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

from valuation import cli, compare, dcf  # noqa: E402

DEMO = cli._clean(json.loads((ROOT / "inputs" / "demo.json").read_text(encoding="utf-8")))


def run(module, *argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = module.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def write_snapshot(folder, as_of, **changes):
    inp = copy.deepcopy(DEMO)
    inp.update(as_of=as_of, **changes)
    (Path(folder) / f"{as_of}_{inp['ticker']}.json").write_text(json.dumps(inp), encoding="utf-8")
    return inp


class TestSnapshot(unittest.TestCase):
    def test_save_writes_input_snapshot_next_to_memo(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, _ = run(cli, str(ROOT / "inputs" / "demo.json"), "--save", "--journal", d)
            snapshot = json.loads((Path(d) / "2026-10-27_DEMO.json").read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(snapshot, DEMO)


class TestCompare(unittest.TestCase):
    def test_lists_changes_and_splits_data_from_judgment(self):
        new = copy.deepcopy(DEMO)
        new.update(growth_start=0.12, margin_target=0.13, revenue=11000)
        res = compare.compare(DEMO, new)
        self.assertEqual([k for k, _, _ in res["changed"]], ["growth_start", "margin_target", "revenue"])
        text = compare.report(DEMO, new)
        data, judgment = text.split("## Giả định phán đoán đã đổi")
        self.assertIn("Doanh thu gốc (TTM), tỷ", data)
        self.assertIn("Biên EBIT mục tiêu", judgment)
        self.assertIn("không phải khuyến nghị mua bán", text)

    def test_effects_and_interaction_add_up_to_the_total_change(self):
        new = copy.deepcopy(DEMO)
        new.update(growth_start=0.12, margin_target=0.13)
        res = compare.compare(DEMO, new)
        total = res["new_value"] - res["old_value"]
        effects = dict(res["effects"])
        self.assertGreater(effects["growth_start"], 0)
        self.assertGreater(effects["margin_target"], 0)
        self.assertNotAlmostEqual(sum(effects.values()), total)  # the two changes compound
        self.assertIn(f"{total - sum(effects.values()):+,.0f} VND/cp", compare.report(DEMO, new))

    def test_largest_effect_listed_first(self):
        new = copy.deepcopy(DEMO)
        new.update(growth_start=0.101, margin_target=0.16)
        self.assertEqual(compare.compare(DEMO, new)["effects"][0][0], "margin_target")

    def test_price_change_moves_value_only_through_market_weights(self):
        fixed = copy.deepcopy(DEMO)
        fixed["wacc"] = {"override": 0.11}
        res = compare.compare(fixed, {**fixed, "price": 30000})
        self.assertEqual(dict(res["effects"])["price"], 0)
        # Without an override, WACC weights come from market cap, so price changes the value.
        self.assertNotEqual(dict(compare.compare(DEMO, {**DEMO, "price": 30000})["effects"])["price"], 0)

    def test_scenario_changes_do_not_move_base_value(self):
        new = copy.deepcopy(DEMO)
        new["scenarios"]["bear"]["growth_start"] = 0.02
        res = compare.compare(DEMO, new)
        self.assertEqual(res["changed"][0][0], "scenarios.bear.growth_start")
        self.assertEqual(dict(res["effects"])["scenarios.bear.growth_start"], 0)
        self.assertIn("Kịch bản bear: Tăng trưởng giai đoạn đầu", compare.report(DEMO, new))

    def test_switching_wacc_method_is_handled(self):
        new = copy.deepcopy(DEMO)
        new["wacc"] = {"override": 0.11}
        res = compare.compare(DEMO, new)
        self.assertAlmostEqual(res["new_value"], dcf.value(new)["per_share"])
        self.assertIn("(không có)", compare.report(DEMO, new))


class TestCli(unittest.TestCase):
    def test_ticker_uses_the_two_latest_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            write_snapshot(d, "2026-01-01", growth_start=0.08)
            write_snapshot(d, "2026-04-01", growth_start=0.09)
            write_snapshot(d, "2026-07-01", growth_start=0.10)
            code, out, _ = run(compare, "DEMO", "--journal", d)
        self.assertEqual(code, 0)
        self.assertIn("# So sánh: DEMO, 2026-04-01 → 2026-07-01", out)

    def test_needs_two_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            write_snapshot(d, "2026-01-01")
            code, out, err = run(compare, "DEMO", "--journal", d)
        self.assertEqual((code, out), (1, ""))
        self.assertIn("Cần ít nhất hai bản lưu", err)

    def test_refuses_different_tickers(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.json"
            b = Path(d) / "b.json"
            a.write_text(json.dumps(DEMO), encoding="utf-8")
            b.write_text(json.dumps({**DEMO, "ticker": "OTHER"}), encoding="utf-8")
            code, _, err = run(compare, str(a), str(b))
        self.assertEqual(code, 1)
        self.assertIn("khác mã", err)


if __name__ == "__main__":
    unittest.main()
