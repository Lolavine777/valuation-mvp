import csv
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from valuation import cli, journal  # noqa: E402


def row(ticker="AAA", as_of="2026-01-15", price=100, base=125, mos=0.2, vnindex=1000):
    return {
        "ticker": ticker,
        "as_of": as_of,
        "price": str(price),
        "bear": "90",
        "base": str(base),
        "bull": "160",
        "mos": str(mos),
        "vnindex": "" if vnindex is None else str(vnindex),
        "memo": f"journal/{as_of}_{ticker}.md",
    }


class JournalTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "log.csv"

    def tearDown(self):
        self._tmp.cleanup()


class TestRecordAndUpdate(JournalTestCase):
    def test_record_appends_and_same_key_replaces_but_keeps_checks(self):
        self.assertTrue(journal.record(self.path, row()))
        self.assertTrue(journal.record(self.path, row(ticker="BBB")))
        journal.update(self.path, "AAA", "2026-01-15", 6, price=110, vnindex=1050)

        self.assertFalse(journal.record(self.path, row(base=130)))  # định giá lại cùng ngày
        rows = journal.load(self.path)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["base"], "130")
        self.assertEqual(rows[0]["price_6m"], "110")  # cột kiểm tra không bị xóa

    def test_update_defaults_date_and_share_factor(self):
        journal.record(self.path, row(as_of="2026-08-31"))
        r = journal.update(self.path, "AAA", "2026-08-31", 6, price=110, vnindex=1050)
        self.assertEqual(r["date_6m"], "2027-02-28")  # cuối tháng: không vượt sang tháng sau
        self.assertEqual(r["share_factor_6m"], "1.0000")

    def test_update_fills_missing_entry_vnindex(self):
        journal.record(self.path, row(vnindex=None))
        journal.update(self.path, "AAA", "2026-01-15", 0, vnindex=1001.5)
        self.assertEqual(journal.load(self.path)[0]["vnindex"], "1001.50")

    def test_update_rejects_bad_requests(self):
        journal.record(self.path, row())
        cases = {
            "không có mục": dict(ticker="ZZZ", at=6, price=1, vnindex=1),
            "mốc lạ": dict(at=3, price=1, vnindex=1),
            "thiếu VN-Index": dict(at=6, price=1),
            "giá âm": dict(at=6, price=-1, vnindex=1),
            "ngày trước ngày ghi": dict(at=6, price=1, vnindex=1, date="2025-12-31"),
            "mốc 0 kèm giá": dict(at=0, price=1, vnindex=1),
        }
        for name, kw in cases.items():
            with self.subTest(name):
                with self.assertRaises(journal.JournalError):
                    journal.update(self.path, kw.pop("ticker", "AAA"), "2026-01-15", **kw)

    def test_user_added_columns_survive(self):
        journal.record(self.path, row())
        with self.path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        rows[0]["ghi_chu"] = "mua thử 100 cp"
        with self.path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=journal.FIELDS + ["ghi_chu"])
            w.writeheader()
            w.writerows(rows)
        journal.update(self.path, "AAA", "2026-01-15", 6, price=110, vnindex=1050)
        self.assertEqual(journal.load(self.path)[0]["ghi_chu"], "mua thử 100 cp")


class TestReturnsAndReport(JournalTestCase):
    def test_returns_adjust_for_bonus_shares(self):
        # Thưởng 10:1: giá giảm từ 100 xuống 99 nhưng mỗi cổ phiếu cũ thành 1,1 cổ phiếu
        r = row() | {"price_6m": "99", "vnindex_6m": "1050", "share_factor_6m": "1.1"}
        stock, index = journal.returns(r, 6)
        self.assertAlmostEqual(stock, 99 * 1.1 / 100 - 1)
        self.assertAlmostEqual(index, 0.05)
        self.assertIsNone(journal.returns(row(), 12))

    def test_report_summarises_and_lists_due(self):
        journal.record(self.path, row("AAA", mos=0.2))
        journal.record(self.path, row("BBB", mos=-0.1))
        journal.record(self.path, row("CCC", as_of="2026-09-01", vnindex=None))
        journal.update(self.path, "AAA", "2026-01-15", 6, price=120, vnindex=1050)  # +20% vs +5%
        journal.update(self.path, "BBB", "2026-01-15", 6, price=95, vnindex=1050)  # -5% vs +5%

        text = journal.report(journal.load(self.path), today=dt.date(2027, 1, 20))
        self.assertIn("Đang theo dõi 3 mục.", text)
        self.assertIn("| AAA | 2026-01-15 | 100 | 125 | +20.0% | 6 tháng | +20.0% | +5.0% | +15.0 |", text)
        self.assertIn("6 tháng: 2 mục, hơn VN-Index trung bình +2.5 điểm %, thắng VN-Index 1/2", text)
        self.assertIn("giá dưới base lúc ghi (biên an toàn > 0): 1 mục, hơn VN-Index trung bình +15.0 điểm %", text)
        self.assertIn("chưa đủ để kết luận", text)
        self.assertIn("update AAA 2026-01-15 --at 12", text)  # mốc 12 tháng đã đến hạn
        self.assertNotIn("update CCC 2026-09-01 --at 6", text)  # chưa đến hạn
        self.assertIn("update CCC 2026-09-01 --at 0 --vnindex", text)  # thiếu VN-Index lúc ghi

    def test_empty_report(self):
        self.assertIn("Chưa có mục nào", journal.report([], today=dt.date(2026, 1, 1)))

    def test_report_before_any_check_has_no_table(self):
        text = journal.report([row(price=22000, base=18625)], today=dt.date(2026, 2, 1))
        self.assertIn("Chưa có mốc 6 hoặc 12 tháng nào được điền.", text)
        self.assertNotIn("| Mã |", text)

    def test_large_numbers_get_thousand_separators(self):
        r = row(price=22000, base=18625) | {"price_6m": "23100", "vnindex_6m": "1000"}
        self.assertIn("| 22,000 | 18,625 |", journal.report([r], today=dt.date(2026, 8, 1)))


class TestCliIntegration(JournalTestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(list(argv))
        return code, err.getvalue()

    def real_company_input(self, **over):
        inp = json.loads((ROOT / "inputs" / "demo.json").read_text(encoding="utf-8"))
        inp.pop("demo")  # coi như công ty thật
        inp.update(over)
        p = Path(self._tmp.name) / "real.json"
        p.write_text(json.dumps(inp, ensure_ascii=False), encoding="utf-8")
        return p

    def test_save_records_entry_with_vnindex_from_input(self):
        code, err = self.run_cli(str(self.real_company_input(vnindex=1761.87)), "--save", "--journal", self._tmp.name)
        self.assertEqual(code, 0)
        r = journal.load(self.path)[0]
        self.assertEqual((r["ticker"], r["as_of"], r["price"], r["base"], r["vnindex"]), ("DEMO", "2026-10-27", "22000", "18625", "1761.87"))
        self.assertIn("Đã thêm vào nhật ký", err)

    def test_save_without_vnindex_records_and_says_how_to_fill(self):
        code, err = self.run_cli(str(self.real_company_input()), "--save", "--journal", self._tmp.name)
        self.assertEqual(code, 0)
        self.assertEqual(journal.load(self.path)[0]["vnindex"], "")
        self.assertIn("--at 0 --vnindex", err)

    def test_demo_is_never_logged(self):
        code, err = self.run_cli(str(ROOT / "inputs" / "demo.json"), "--save", "--journal", self._tmp.name)
        self.assertEqual(code, 0)
        self.assertFalse(self.path.exists())
        self.assertIn("không ghi vào nhật ký", err)

    def test_journal_cli_update_and_report(self):
        journal.record(self.path, row())
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(
                journal.main(["--file", str(self.path), "update", "AAA", "2026-01-15", "--at", "6", "--price", "110", "--vnindex", "1050"]),
                0,
            )
            self.assertEqual(journal.main(["--file", str(self.path), "report", "--today", "2026-08-01"]), 0)
        self.assertIn("+10.0% | +5.0% | +5.0 |", out.getvalue())
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(journal.main(["--file", str(self.path), "update", "AAA", "2026-01-15", "--at", "6", "--price", "1"]), 1)
        self.assertIn("cần cả --price và --vnindex", err.getvalue())


if __name__ == "__main__":
    unittest.main()
