import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from valuation import cli, dcf  # noqa: E402


def make_inputs(**over):
    base = {
        "company": "Test Co",
        "ticker": "TEST",
        "revenue": 1000.0,
        "growth_start": 0.0,
        "growth_terminal": 0.0,
        "margin_start": 0.10,
        "margin_target": 0.10,
        "tax_rate": 0.20,
        "roic": 0.15,
        "roic_terminal": 0.15,
        "net_debt": 0.0,
        "shares_mn": 100.0,
        "price": 10000.0,
        "years": 10,
        "high_growth_years": 5,
        "wacc": {"override": 0.10},
    }
    base.update(over)
    return base


class TestEngine(unittest.TestCase):
    def test_zero_growth_is_perpetuity(self):
        # Không tăng trưởng, không tái đầu tư: EV = NOPAT / WACC
        inp = make_inputs()
        nopat = 1000 * 0.10 * 0.80
        res = dcf.value(inp)
        self.assertAlmostEqual(res["ev"], nopat / 0.10, places=6)

    def test_growth_is_worthless_when_roic_equals_wacc(self):
        # Khi ROIC = WACC, tăng trưởng không tạo giá trị: EV = NOPAT năm 1 / WACC
        g = 0.05
        inp = make_inputs(
            growth_start=g,
            growth_terminal=g,
            roic=0.10,
            roic_terminal=0.10,
        )
        nopat1 = 1000 * (1 + g) * 0.10 * 0.80
        res = dcf.value(inp)
        self.assertAlmostEqual(res["ev"], nopat1 / 0.10, places=6)

    def test_growth_creates_value_when_roic_above_wacc(self):
        low = dcf.value(make_inputs(growth_start=0.0, growth_terminal=0.0))["ev"]
        high = dcf.value(make_inputs(growth_start=0.06, growth_terminal=0.03, roic_terminal=0.15))["ev"]
        self.assertGreater(high, low)

    def test_growth_destroys_value_when_roic_below_wacc(self):
        flat = dcf.value(make_inputs(roic=0.06, roic_terminal=0.06))["ev"]
        grow = dcf.value(make_inputs(growth_start=0.08, growth_terminal=0.03, roic=0.06, roic_terminal=0.06))["ev"]
        self.assertLess(grow, flat)

    def test_wacc_must_exceed_terminal_growth(self):
        inp = make_inputs(growth_terminal=0.10)
        with self.assertRaises(dcf.InputError):
            dcf.value(inp)

    def test_net_debt_and_per_share(self):
        inp = make_inputs(net_debt=200.0)
        res = dcf.value(inp)
        self.assertAlmostEqual(res["equity"], res["ev"] - 200.0)
        self.assertAlmostEqual(res["per_share"], res["equity"] * 1000 / 100.0)

    def test_wacc_components(self):
        inp = make_inputs(
            wacc={"rf": 0.04, "erp": 0.07, "beta": 1.2, "cost_of_debt": 0.09, "equity_weight": 0.8},
        )
        w = dcf.compute_wacc(inp)
        ke = 0.04 + 1.2 * 0.07
        kd = 0.09 * (1 - 0.20)
        self.assertAlmostEqual(w["ke"], ke)
        self.assertAlmostEqual(w["wacc"], 0.8 * ke + 0.2 * kd)

    def test_market_weights_from_price(self):
        inp = make_inputs(
            net_debt=50.0,
            price=5000.0,  # vốn hóa = 5000 * 100 / 1000 = 500
            wacc={"rf": 0.04, "erp": 0.07, "beta": 1.0, "cost_of_debt": 0.08, "debt": 500.0},
        )
        w = dcf.compute_wacc(inp)
        self.assertAlmostEqual(w["we"], 0.5)

    def test_sensitivity_monotonic_in_wacc(self):
        inp = make_inputs(growth_start=0.06, growth_terminal=0.03)
        s = dcf.sensitivity(inp)
        mid = len(s["gs"]) // 2
        col = [row[mid] for row in s["grid"]]
        self.assertEqual(col, sorted(col, reverse=True))

    def test_reverse_dcf_round_trip(self):
        inp = make_inputs(growth_start=0.08, growth_terminal=0.03)
        target = dcf.value(inp)["per_share"]
        probe = copy.deepcopy(inp)
        probe["growth_start"] = 0.0
        probe["price"] = target
        rv = dcf.reverse_dcf(probe)
        self.assertEqual(rv["status"], "ok")
        self.assertAlmostEqual(rv["growth"], 0.08, places=4)

    def test_reverse_dcf_without_price(self):
        inp = make_inputs()
        inp.pop("price")
        rv = dcf.reverse_dcf(inp)
        self.assertIsNone(rv["growth"])
        self.assertEqual(rv["status"], "no_price")

    def test_reverse_dcf_price_above_reachable_range(self):
        # Giá cao gấp nhiều lần mọi giá trị đạt được khi tăng trưởng nằm trong [-10%, 40%]
        inp = make_inputs(growth_start=0.05, growth_terminal=0.03, price=1_000_000.0)
        rv = dcf.reverse_dcf(inp)
        self.assertEqual(rv["status"], "above_range")
        self.assertIsNone(rv["growth"])

    def test_reverse_dcf_price_below_reachable_range(self):
        inp = make_inputs(growth_start=0.05, growth_terminal=0.03, price=1.0)
        rv = dcf.reverse_dcf(inp)
        self.assertEqual(rv["status"], "below_range")

    def test_margin_of_safety(self):
        self.assertAlmostEqual(dcf.margin_of_safety(100.0, 70.0), 0.30)
        self.assertLess(dcf.margin_of_safety(100.0, 130.0), 0)
        self.assertIsNone(dcf.margin_of_safety(-5.0, 10.0))

    def test_validate_reports_missing_fields(self):
        inp = make_inputs()
        inp.pop("revenue")
        self.assertTrue(any("revenue" in e for e in dcf.validate(inp)))

    def test_validate_requires_price_or_weight(self):
        inp = make_inputs(wacc={"rf": 0.04, "erp": 0.07, "beta": 1.0, "cost_of_debt": 0.08})
        inp.pop("price")
        self.assertTrue(any("price" in e for e in dcf.validate(inp)))

    def test_scenarios_only_run_when_defined(self):
        inp = make_inputs(growth_start=0.06, growth_terminal=0.03)
        inp["scenarios"] = {"bear": {"growth_start": 0.02}, "bull": {"growth_start": 0.10}}
        sc = dcf.scenarios(inp)
        self.assertLess(sc["bear"]["per_share"], sc["base"]["per_share"])
        self.assertGreater(sc["bull"]["per_share"], sc["base"]["per_share"])
        sc2 = dcf.scenarios(make_inputs())
        self.assertIsNone(sc2["bear"])
        self.assertIsNotNone(sc2["base"])

    def test_financial_sector_flag(self):
        inp = make_inputs(sector="Ngân hàng")
        res = dcf.value(inp)
        self.assertTrue(any("tài chính" in f for f in dcf.flags(inp, res)))

    def test_terminal_value_share_flag(self):
        inp = make_inputs(growth_terminal=0.045, roic_terminal=0.30, wacc={"override": 0.06})
        res = dcf.value(inp)
        self.assertGreater(res["tv_share"], 0.75)
        self.assertTrue(any("Giá trị cuối kỳ chiếm" in f for f in dcf.flags(inp, res)))

    def test_scenario_mos_matches_headline_mos(self):
        inp = make_inputs(growth_start=0.06, growth_terminal=0.03)
        a = dcf.analyze(inp)
        self.assertAlmostEqual(a["mos"], dcf.margin_of_safety(a["base"]["per_share"], inp["price"]))
        self.assertAlmostEqual(a["scenarios"]["base"]["mos"], a["mos"])

    def test_invalid_scenario_raises_instead_of_hiding(self):
        bad = {
            "wacc_override": 0.02,  # WACC <= g dài hạn
            "roic_terminal": 0,  # sẽ chia cho 0
            "high_growth_years": 10,  # = years
            "growth_start": "0.05",  # sai kiểu
        }
        for key, val in bad.items():
            with self.subTest(key=key):
                inp = make_inputs(growth_terminal=0.03, scenarios={"bear": {key: val}})
                with self.assertRaisesRegex(dcf.InputError, "kịch bản bear"):
                    dcf.analyze(inp)

    def test_validate_rejects_unknown_scenarios(self):
        for sc in ({"bear": {"growth": 0.02}}, {"base": {"growth_start": 0.02}}, {"bear": 0.02}, ["bear"]):
            with self.subTest(sc=sc):
                self.assertTrue(any("scenarios" in e for e in dcf.validate(make_inputs(scenarios=sc))))

    def test_validate_rejects_wrong_types_instead_of_crashing(self):
        cases = [
            (make_inputs(revenue="1000"), "revenue"),
            (make_inputs(price=True), "price"),
            (make_inputs(wacc={"override": "0.10"}), "wacc.override"),
            (make_inputs(as_of="27/10/2026"), "as_of"),
            (make_inputs(ticker="../x"), "ticker"),
        ]
        for inp, field in cases:
            with self.subTest(field=field):
                self.assertTrue(any(field in e for e in dcf.validate(inp)))


class TestCli(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_demo_end_to_end_and_save(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, _ = self.run_cli(str(ROOT / "inputs" / "demo.json"), "--save", "--journal", d)
            saved = Path(d) / "2026-10-27_DEMO.md"
            self.assertEqual(code, 0)
            self.assertEqual(out, saved.read_text(encoding="utf-8") + "\n")
        # Số base của demo đã được đối chiếu bằng tay; biên an toàn ở mục 1 và mục 3 phải là cùng một số.
        self.assertIn("(base): **-18%**", out)
        self.assertIn("| Base | 18,625 | -18% |", out)
        self.assertIn("không phải khuyến nghị mua bán", out)

    def test_bad_input_prints_message_not_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_text(json.dumps(make_inputs(revenue="1000")), encoding="utf-8")
            code, _, err = self.run_cli(str(p))
        self.assertEqual(code, 1)
        self.assertIn("'revenue' phải là số", err)


if __name__ == "__main__":
    unittest.main()
