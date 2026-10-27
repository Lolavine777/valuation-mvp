"""Nhật ký kiểm chứng: công cụ có giúp ích không, so với việc chỉ giữ VN-Index?

Mỗi lần lưu memo bằng `--save`, một dòng được ghi vào journal/log.csv: mã, ngày, giá, giá trị bear/base/bull,
biên an toàn, VN-Index. Sau 6 và 12 tháng, điền giá và VN-Index lúc đó; báo cáo so sánh hai bên.

Dùng:
  python3 -m valuation.journal report
  python3 -m valuation.journal update FPT 2026-10-27 --at 6 --price 61000 --vnindex 1812.5 [--share-factor 1.1]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path
from typing import Any, Optional

from .memo import add_months

HORIZONS = (6, 12)
ENTRY_FIELDS = ["ticker", "as_of", "price", "bear", "base", "bull", "mos", "vnindex", "memo"]
CHECK_FIELDS = [f"{name}_{h}m" for h in HORIZONS for name in ("date", "price", "vnindex", "share_factor")]
FIELDS = ENTRY_FIELDS + CHECK_FIELDS
DEFAULT_FILE = Path("journal") / "log.csv"
MIN_SAMPLE = 10


class JournalError(ValueError):
    """Lỗi khi đọc hoặc cập nhật nhật ký."""


def load(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save(path: Path, rows: list[dict[str, str]]) -> None:
    # Giữ lại các cột người dùng tự thêm (ví dụ ghi chú thêm trong Excel), không âm thầm xóa.
    extra = [k for r in rows for k in r if k not in FIELDS and k is not None]
    fields = FIELDS + list(dict.fromkeys(extra))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows({k: r.get(k) or "" for k in fields} for r in rows)
    tmp.replace(path)  # ghi file tạm rồi đổi tên: bị ngắt giữa chừng cũng không hỏng nhật ký cũ


def _num(s: Optional[str]) -> Optional[float]:
    return float(s) if s not in (None, "") else None


def _fmt(x: Optional[float], digits: int = 0) -> str:
    return "" if x is None else f"{x:.{digits}f}"


def entry(analysis: dict[str, Any], as_of: str, vnindex: Optional[float], memo_path: Path) -> dict[str, str]:
    """Dòng nhật ký từ kết quả dcf.analyze."""
    sc = analysis["scenarios"]

    def per_share(name: str) -> Optional[float]:
        return sc[name]["per_share"] if sc.get(name) else None

    return {
        "ticker": analysis["inp"]["ticker"],
        "as_of": as_of,
        "price": _fmt(analysis["inp"].get("price") or None),
        "bear": _fmt(per_share("bear")),
        "base": _fmt(analysis["base"]["per_share"]),
        "bull": _fmt(per_share("bull")),
        "mos": _fmt(analysis["mos"], 4),
        "vnindex": _fmt(vnindex, 2),
        "memo": str(memo_path),
    }


def record(path: Path, row: dict[str, str]) -> bool:
    """Thêm một dòng. Cùng mã và ngày thì ghi đè phần định giá, giữ các cột kiểm tra đã điền. Trả về True nếu thêm mới."""
    rows = load(path)
    for r in rows:
        if (r["ticker"], r["as_of"]) == (row["ticker"], row["as_of"]):
            r.update(row)
            save(path, rows)
            return False
    rows.append(row)
    save(path, rows)
    return True


def update(
    path: Path,
    ticker: str,
    as_of: str,
    at: int,
    price: Optional[float] = None,
    vnindex: Optional[float] = None,
    share_factor: Optional[float] = None,
    date: Optional[str] = None,
) -> dict[str, str]:
    """Điền giá và VN-Index tại mốc `at` tháng (6 hoặc 12). `at=0` chỉ để bổ sung VN-Index lúc ghi."""
    if at not in (0,) + HORIZONS:
        raise JournalError("--at phải là 0, 6 hoặc 12")
    for name, v in (("price", price), ("vnindex", vnindex), ("share_factor", share_factor)):
        if v is not None and v <= 0:
            raise JournalError(f"{name} phải > 0")
    rows = load(path)
    match = [r for r in rows if (r["ticker"], r["as_of"]) == (ticker, as_of)]
    if not match:
        have = ", ".join(r["as_of"] for r in rows if r["ticker"] == ticker) or "không có"
        raise JournalError(f"không có mục {ticker} ngày {as_of} trong {path} (các ngày đã ghi của {ticker}: {have})")
    r = match[0]

    if at == 0:
        if vnindex is None or price is not None or share_factor is not None:
            raise JournalError("--at 0 chỉ dùng để bổ sung --vnindex lúc ghi")
        r["vnindex"] = _fmt(vnindex, 2)
    else:
        if price is None or vnindex is None:
            raise JournalError("cần cả --price và --vnindex")
        start = dt.date.fromisoformat(as_of)
        d = dt.date.fromisoformat(date) if date else add_months(start, at)
        if d <= start:
            raise JournalError(f"--date phải sau ngày ghi {as_of}")
        r[f"date_{at}m"] = d.isoformat()
        r[f"price_{at}m"] = _fmt(price)
        r[f"vnindex_{at}m"] = _fmt(vnindex, 2)
        r[f"share_factor_{at}m"] = _fmt(share_factor if share_factor is not None else 1.0, 4)
    save(path, rows)
    return r


def returns(r: dict[str, str], h: int) -> Optional[tuple[float, float]]:
    """(lợi nhuận cổ phiếu, lợi nhuận VN-Index) tại mốc h tháng, theo giá, không gồm cổ tức tiền mặt.

    share_factor là số cổ phiếu nhận được cho mỗi cổ phiếu ban đầu (thưởng 10:1 → 1.1), để giá sau chia tách
    so được với giá trước.
    """
    p0, i0 = _num(r.get("price")), _num(r.get("vnindex"))
    p, i = _num(r.get(f"price_{h}m")), _num(r.get(f"vnindex_{h}m"))
    if None in (p0, i0, p, i):
        return None
    k = _num(r.get(f"share_factor_{h}m")) or 1.0
    return p * k / p0 - 1, i / i0 - 1


def due(rows: list[dict[str, str]], today: dt.date) -> list[tuple[dict[str, str], int, dt.date]]:
    """Các mốc đã đến hạn mà chưa điền."""
    out = []
    for r in rows:
        for h in HORIZONS:
            d = add_months(dt.date.fromisoformat(r["as_of"]), h)
            if d <= today and not r.get(f"price_{h}m"):
                out.append((r, h, d))
    return out


def _pct(x: Optional[float]) -> str:
    return "-" if x is None else f"{x * 100:+.1f}%"


def _pts(x: float) -> str:
    return f"{x * 100:+.1f}"


def _vnd(s: str) -> str:
    return f"{float(s):,.0f}" if s else "-"


def report(rows: list[dict[str, str]], today: dt.date) -> str:
    L = ["# Nhật ký kiểm chứng", ""]
    if not rows:
        L.append("Chưa có mục nào. Lưu memo của một công ty thật bằng `python3 -m valuation inputs/<MA>.json --save`.")
        return "\n".join(L) + "\n"

    checked: dict[int, list[tuple[Optional[float], float]]] = {h: [] for h in HORIZONS}
    table = []
    for r in rows:
        mos = _num(r.get("mos"))
        for h in HORIZONS:
            ret = returns(r, h)
            if ret is None:
                continue
            excess = ret[0] - ret[1]
            checked[h].append((mos, excess))
            table.append(
                f"| {r['ticker']} | {r['as_of']} | {_vnd(r['price'])} | {_vnd(r['base'])} | {_pct(mos)} | {h} tháng | "
                f"{_pct(ret[0])} | {_pct(ret[1])} | {_pts(excess)} |"
            )

    L.append(f"Đang theo dõi {len(rows)} mục.")
    L.append("")
    if table:
        L.append("Lợi nhuận theo giá, cổ phiếu đã điều chỉnh thưởng/chia tách. Cả hai bên không gồm cổ tức tiền mặt.")
        L.append("")
        L.append("| Mã | Ngày ghi | Giá | Base | Biên an toàn | Mốc | Cổ phiếu | VN-Index | Hơn VN-Index (điểm %) |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        L += table
    else:
        L.append("Chưa có mốc 6 hoặc 12 tháng nào được điền.")
    L.append("")

    L.append("## Tổng hợp")
    L.append("")
    for h in HORIZONS:
        items = checked[h]
        if not items:
            L.append(f"- {h} tháng: chưa có dữ liệu.")
            continue
        L.append(f"- {h} tháng: {_summary(items)}")
        for label, group in (
            ("giá dưới base lúc ghi (biên an toàn > 0)", [x for x in items if x[0] is not None and x[0] > 0]),
            ("giá trên base lúc ghi", [x for x in items if x[0] is not None and x[0] <= 0]),
        ):
            if group:
                L.append(f"  - {label}: {_summary(group)}")
        if len(items) < MIN_SAMPLE:
            L.append(f"  - Mới có {len(items)} mục: chưa đủ để kết luận gì (cần ít nhất {MIN_SAMPLE}).")
    L.append("")
    L.append("Đây là tự đánh giá, không phải bằng chứng thống kê, và không phải khuyến nghị mua bán.")

    pending = due(rows, today)
    missing_index = [r for r in rows if not r.get("vnindex")]
    if pending or missing_index:
        L.append("")
        L.append("## Cần điền")
        L.append("")
        for r, h, d in pending:
            L.append(
                f"- {r['ticker']} ghi ngày {r['as_of']}, mốc {h} tháng (đến hạn {d.isoformat()}): "
                f"`python3 -m valuation.journal update {r['ticker']} {r['as_of']} --at {h} --price <giá> --vnindex <điểm>`"
            )
        for r in missing_index:
            L.append(
                f"- {r['ticker']} ghi ngày {r['as_of']} thiếu VN-Index lúc ghi: "
                f"`python3 -m valuation.journal update {r['ticker']} {r['as_of']} --at 0 --vnindex <điểm>`"
            )
    return "\n".join(L) + "\n"


def _summary(items: list[tuple[Optional[float], float]]) -> str:
    excess = [e for _, e in items]
    wins = sum(e > 0 for e in excess)
    avg = sum(excess) / len(excess)
    return f"{len(excess)} mục, hơn VN-Index trung bình {_pts(avg)} điểm %, thắng VN-Index {wins}/{len(excess)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="valuation.journal", description="Nhật ký kiểm chứng so với VN-Index.")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help=f"file nhật ký (mặc định: {DEFAULT_FILE})")
    sub = parser.add_subparsers(dest="cmd", required=True)
    rep = sub.add_parser("report", help="in bảng so sánh và các mốc cần điền")
    rep.add_argument("--today", help="ngày tham chiếu YYYY-MM-DD (mặc định: hôm nay)")
    up = sub.add_parser("update", help="điền giá và VN-Index tại mốc 6 hoặc 12 tháng")
    up.add_argument("ticker")
    up.add_argument("as_of", help="ngày ghi, YYYY-MM-DD")
    up.add_argument("--at", type=int, required=True, help="mốc: 6 hoặc 12 (0 để bổ sung VN-Index lúc ghi)")
    up.add_argument("--price", type=float, help="giá đóng cửa tại mốc, VND/cp")
    up.add_argument("--vnindex", type=float, help="VN-Index đóng cửa cùng ngày")
    up.add_argument("--share-factor", type=float, help="số cổ phiếu nhận được cho mỗi cổ phiếu ban đầu (mặc định 1)")
    up.add_argument("--date", help="ngày của giá, YYYY-MM-DD (mặc định: ngày đến hạn)")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    path = Path(args.file)
    try:
        if args.cmd == "report":
            today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
            print(report(load(path), today), end="")
        else:
            r = update(path, args.ticker, args.as_of, args.at, args.price, args.vnindex, args.share_factor, args.date)
            print(f"Đã cập nhật {r['ticker']} {r['as_of']} trong {path}")
    except (JournalError, ValueError) as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
