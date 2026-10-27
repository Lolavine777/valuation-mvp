import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import draft_input as di  # noqa: E402
from valuation import dcf  # noqa: E402
from valuation.cli import _clean  # noqa: E402


def cite(value, doc="A", page=5):
    return {"value": value, "doc": doc, "page": page, "line": "chỉ tiêu"}


def make_extraction(**over):
    # Số liệu giả, đơn vị VND như phần lớn BCTC: 600 tỷ = 600e9
    ex = {
        "ticker": "TEST",
        "company": "Test Co",
        "sector": "Công nghệ",
        "period_end": "2026-06-30",
        "months": 6,
        "documents": {
            "A": {"title": "BCTC bán niên 2026", "source": "https://example.com/a.pdf", "unit": "VND"},
            "B": {"title": "BCTC năm 2025", "source": "https://example.com/b.pdf", "unit": "VND"},
        },
        "values": {
            "revenue_ytd": cite(600e9),
            "revenue_ytd_prior": cite(500e9),
            "revenue_fy_prior": cite(1100e9, doc="B", page=9),
            "cash": cite(100e9),
            "short_term_investments": cite(50e9),
            "short_term_debt": cite(200e9),
            "long_term_debt": cite(30e9),
            "minorities": cite(40e9),
            "associates": cite(25e9),
            "shares_outstanding": cite(100_000_000, page=47),
        },
        "price": {"value": 30000, "date": "2026-10-27", "source": "https://example.com/gia"},
        "vnindex": {"value": 1700.5, "date": "2026-10-27", "source": "https://example.com/vni"},
        "notes": [],
    }
    ex.update(over)
    return ex


class TestCompute(unittest.TestCase):
    def test_ttm_net_debt_and_units(self):
        data, warnings = di.compute(make_extraction())
        self.assertAlmostEqual(data["revenue"], 600 + (1100 - 500))  # H1 năm nay + H2 năm trước
        self.assertAlmostEqual(data["net_debt"], 200 + 30 - 100 - 50)
        self.assertAlmostEqual(data["minorities"], 40)
        self.assertAlmostEqual(data["associates"], 25)
        self.assertAlmostEqual(data["shares_mn"], 100)
        self.assertEqual((data["price"], data["as_of"]), (30000, "2026-10-27"))
        self.assertEqual(warnings, [])

    def test_full_year_report_needs_no_prior(self):
        ex = make_extraction(months=12)
        for key in ("revenue_ytd_prior", "revenue_fy_prior"):
            ex["values"].pop(key)
        self.assertAlmostEqual(di.compute(ex)[0]["revenue"], 600)

    def test_unit_per_document(self):
        ex = make_extraction()
        ex["documents"]["B"]["unit"] = "triệu VND"
        ex["values"]["revenue_fy_prior"] = cite(1_100_000, doc="B")  # 1.100 tỷ viết theo triệu đồng
        self.assertAlmostEqual(di.compute(ex)[0]["revenue"], 1200)

    def test_scope_change_scales_rest_of_prior_year(self):
        # Năm trước hợp nhất một công ty con chiếm 30% doanh thu, năm nay không còn
        ex = make_extraction()
        ex["values"]["revenue_ytd_prior_comparable"] = cite(350e9)
        data, warnings = di.compute(ex)
        self.assertAlmostEqual(data["revenue"], 600 + (1100 - 500) * 0.7)
        self.assertTrue(any("Phạm vi hợp nhất thay đổi" in w for w in warnings))

    def test_current_share_count_wins_and_is_flagged(self):
        ex = make_extraction()
        ex["values"]["shares_outstanding_current"] = cite(110_000_000, doc="A", page=2)
        data, warnings = di.compute(ex)
        self.assertAlmostEqual(data["shares_mn"], 110)
        self.assertTrue(any("Số cổ phiếu thay đổi" in w for w in warnings))

    def test_rejects_bad_extractions(self):
        cases = {
            "thiếu trích dẫn": lambda ex: ex["values"]["cash"].pop("page"),
            "trích dẫn sai tài liệu": lambda ex: ex["values"]["cash"].update(doc="Z"),
            "khóa gõ nhầm": lambda ex: ex["values"].update(revenue=cite(1)),
            "số âm": lambda ex: ex["values"]["cash"].update(value=-1),
            "đơn vị lạ": lambda ex: ex["documents"]["A"].update(unit="USD"),
            "thiếu số năm trước": lambda ex: ex["values"].pop("revenue_fy_prior"),
            "giá không có nguồn": lambda ex: ex["price"].pop("source"),
            "months lạ": lambda ex: ex.update(months=7),
            "VN-Index khác ngày với giá": lambda ex: ex["vnindex"].update(date="2026-10-26"),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                ex = make_extraction()
                mutate(ex)
                with self.assertRaises(di.ExtractionError):
                    di.compute(ex)

    def test_prior_ytd_larger_than_full_year_is_rejected(self):
        ex = make_extraction()
        ex["values"]["revenue_ytd_prior"] = cite(1200e9)  # thường do nhầm cột hoặc đơn vị
        with self.assertRaisesRegex(di.ExtractionError, "revenue_ytd_prior"):
            di.compute(ex)

    def test_vnindex_optional_but_flagged(self):
        self.assertEqual(di.compute(make_extraction())[0]["vnindex"], 1700.5)
        ex = make_extraction()
        ex.pop("vnindex")
        data, warnings = di.compute(ex)
        self.assertIsNone(data["vnindex"])
        self.assertTrue(any("VN-Index" in w for w in warnings))

    def test_negative_minorities_allowed(self):
        ex = make_extraction()
        ex["values"]["minorities"] = cite(-5e9)
        self.assertAlmostEqual(di.compute(ex)[0]["minorities"], -5)


class TestDraft(unittest.TestCase):
    def test_new_file_from_template_keeps_judgments_empty(self):
        with tempfile.TemporaryDirectory() as d:
            out, data, _ = di.draft(make_extraction(), Path(d))
            doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(out.name, "TEST.json")
        self.assertEqual(doc["revenue"], data["revenue"])
        self.assertEqual(doc["growth_start"], 0.0)  # giả định phán đoán để người điền
        self.assertEqual(doc["sector"], "Công nghệ")
        self.assertIn("revenue_ytd", doc["_nguon"]["so_lieu"])
        self.assertTrue(dcf.validate(_clean(doc)))  # chưa chạy được định giá khi chưa điền giả định
        self.assertIn("growth_start", di.unfilled(doc))
        self.assertIn("wacc.rf", di.unfilled(doc))

    def test_unfilled_skips_wacc_parts_when_overridden(self):
        doc = {k: 0.1 for k in di.JUDGMENTS} | {"wacc": {"override": 0.11}}
        self.assertEqual(di.unfilled(doc), [])

    def test_template_sector_hint_is_not_kept(self):
        # Câu hướng dẫn trong TEMPLATE có chữ "ngân hàng" và sẽ bật cảnh báo ngành tài chính nếu bị giữ lại
        ex = make_extraction()
        ex.pop("sector")
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = di.draft(ex, Path(d))
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["sector"], "")

    def test_rerun_updates_numbers_and_keeps_judgments(self):
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = di.draft(make_extraction(), Path(d))
            doc = json.loads(out.read_text(encoding="utf-8"))
            doc["growth_start"] = 0.12
            doc["wacc"]["beta"] = 1.3
            out.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

            ex = make_extraction()
            ex["values"]["cash"] = cite(150e9)
            di.draft(ex, Path(d))
            doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["growth_start"], 0.12)
        self.assertEqual(doc["wacc"]["beta"], 1.3)
        self.assertAlmostEqual(doc["net_debt"], 200 + 30 - 150 - 50)

    def test_rerun_without_vnindex_clears_stale_value(self):
        # VN-Index cũ đứng cạnh giá mới sẽ làm sai nhật ký kiểm chứng
        with tempfile.TemporaryDirectory() as d:
            di.draft(make_extraction(), Path(d))
            ex = make_extraction(price={"value": 31000, "date": "2026-11-27", "source": "https://example.com/gia"})
            ex.pop("vnindex")
            out, _, _ = di.draft(ex, Path(d))
            self.assertIsNone(json.loads(out.read_text(encoding="utf-8"))["vnindex"])

    def test_cli_reports_error_without_traceback(self):
        ex = make_extraction()
        ex["values"]["cash"].pop("doc")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "extraction.json"
            p.write_text(json.dumps(ex), encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(di.main([str(p), "--out-dir", d]), 1)
            self.assertFalse((Path(d) / "TEST.json").exists())
        self.assertIn("values.cash cần trích dẫn", err.getvalue())


if __name__ == "__main__":
    unittest.main()
