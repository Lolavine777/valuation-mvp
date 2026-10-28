"""Bất biến kinh tế của mô hình DCF, kiểm trên nhiều bộ giả định ngẫu nhiên.

Seed cố định nên kết quả lặp lại được; chỉ dùng thư viện chuẩn.
Các bộ giả định giữ tăng trưởng thấp hơn ROIC để FCFF luôn dương, vùng mà các bất biến dưới đây phải đúng.
"""

import copy
import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from valuation import dcf  # noqa: E402

CASES = 200
SEED = 20261028


def random_inputs(rng: random.Random) -> dict:
    roic = rng.uniform(0.08, 0.30)
    wacc = rng.uniform(0.08, 0.14)
    g_term = rng.uniform(0.0, min(0.05, wacc - 0.02))
    return {
        "company": "Random Co",
        "ticker": "RND",
        "revenue": rng.uniform(100.0, 100_000.0),
        "growth_start": rng.uniform(-0.05, 0.8 * roic),
        "growth_terminal": g_term,
        "margin_start": rng.uniform(0.03, 0.30),
        "margin_target": rng.uniform(0.03, 0.30),
        "tax_rate": rng.uniform(0.15, 0.25),
        "roic": roic,
        "roic_terminal": rng.uniform(max(0.06, g_term + 0.02), 0.25),
        "net_debt": rng.uniform(-1_000.0, 5_000.0),
        "minorities": rng.uniform(0.0, 500.0),
        "associates": rng.uniform(0.0, 500.0),
        "shares_mn": rng.uniform(10.0, 5_000.0),
        "price": rng.uniform(5_000.0, 200_000.0),
        "years": 10,
        "high_growth_years": rng.randint(1, 9),
        "wacc": {"override": wacc},
    }


def cases():
    rng = random.Random(SEED)
    for i in range(CASES):
        yield i, random_inputs(rng)


def with_changes(inp: dict, **changes) -> dict:
    out = copy.deepcopy(inp)
    out.update(changes)
    return out


class TestDcfProperties(unittest.TestCase):
    def test_generator_produces_valid_inputs(self):
        for i, inp in cases():
            with self.subTest(case=i):
                self.assertEqual(dcf.validate(inp), [])

    def test_value_falls_as_wacc_rises(self):
        for i, inp in cases():
            with self.subTest(case=i):
                w = inp["wacc"]["override"]
                higher = with_changes(inp, wacc={"override": w + 0.01})
                self.assertGreater(dcf.value(inp)["ev"], dcf.value(higher)["ev"])

    def test_enterprise_value_scales_with_revenue(self):
        for i, inp in cases():
            with self.subTest(case=i):
                doubled = with_changes(inp, revenue=inp["revenue"] * 2)
                self.assertTrue(math.isclose(dcf.value(doubled)["ev"], 2 * dcf.value(inp)["ev"], rel_tol=1e-9))

    def test_higher_target_margin_never_lowers_value(self):
        for i, inp in cases():
            with self.subTest(case=i):
                richer = with_changes(inp, margin_target=inp["margin_target"] + 0.02)
                self.assertGreater(dcf.value(richer)["ev"], dcf.value(inp)["ev"])

    def test_equity_bridge_is_exact(self):
        for i, inp in cases():
            with self.subTest(case=i):
                res = dcf.value(inp)
                bridge = res["ev"] - inp["net_debt"] - inp["minorities"] + inp["associates"]
                self.assertTrue(math.isclose(res["equity"], bridge, rel_tol=1e-12, abs_tol=1e-9))
                more_debt = dcf.value(with_changes(inp, net_debt=inp["net_debt"] + 100.0))
                drop = res["per_share"] - more_debt["per_share"]
                self.assertTrue(math.isclose(drop, 100.0 * dcf.PER_SHARE_FACTOR / inp["shares_mn"], rel_tol=1e-9))

    def test_reverse_dcf_reprices_to_the_market_price(self):
        for i, inp in cases():
            with self.subTest(case=i):
                price = dcf.value(inp)["per_share"]
                if price <= 0:
                    continue
                probe = with_changes(inp, price=price, growth_start=0.0)
                rv = dcf.reverse_dcf(probe)
                self.assertEqual(rv["status"], "ok")
                repriced = dcf.value(with_changes(probe, growth_start=rv["growth"]))["per_share"]
                self.assertTrue(math.isclose(repriced, price, rel_tol=1e-5))


if __name__ == "__main__":
    unittest.main()
