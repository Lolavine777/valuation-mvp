"""So sánh hai bản lưu của cùng một mã: số liệu và giả định nào đã đổi, và mỗi thay đổi làm giá trị đổi bao nhiêu.

Mỗi lần `--save`, cạnh memo có bản chụp giả định journal/<ngày>_<mã>.json.

Dùng:
  python3 -m valuation.compare FPT                                  # hai bản lưu gần nhất trong journal/
  python3 -m valuation.compare journal/2026-10-27_FPT.json journal/2027-04-27_FPT.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Optional

from . import dcf
from .cli import _clean
from .memo import _n, _p

# Số liệu lấy từ báo cáo tài chính hoặc thị trường; mọi khóa số còn lại là giả định phán đoán.
DATA_KEYS = {"revenue", "net_debt", "minorities", "associates", "shares_mn", "price", "vnindex"}
SKIP_KEYS = {"company", "ticker", "sector", "as_of", "demo"}
RATE_KEYS = {
    "growth_start",
    "growth_terminal",
    "margin_start",
    "margin_target",
    "tax_rate",
    "roic",
    "roic_terminal",
    "rf",
    "erp",
    "cost_of_debt",
    "equity_weight",
    "override",
}
LABELS = {
    "revenue": "Doanh thu gốc (TTM), tỷ",
    "net_debt": "Nợ ròng, tỷ",
    "minorities": "Lợi ích CĐKKS, tỷ",
    "associates": "Đầu tư liên kết, tỷ",
    "shares_mn": "Số cổ phiếu, triệu",
    "price": "Giá thị trường, VND/cp",
    "vnindex": "VN-Index",
    "growth_start": "Tăng trưởng giai đoạn đầu",
    "growth_terminal": "Tăng trưởng dài hạn",
    "margin_start": "Biên EBIT hiện tại",
    "margin_target": "Biên EBIT mục tiêu",
    "tax_rate": "Thuế suất",
    "roic": "ROIC giai đoạn tăng trưởng",
    "roic_terminal": "ROIC dài hạn",
    "years": "Số năm dự phóng",
    "high_growth_years": "Số năm tăng trưởng cao",
    "wacc.rf": "Lãi suất phi rủi ro",
    "wacc.erp": "ERP",
    "wacc.beta": "Beta",
    "wacc.cost_of_debt": "Chi phí nợ",
    "wacc.debt": "Nợ dùng tính WACC, tỷ",
    "wacc.equity_weight": "Tỷ trọng vốn chủ",
    "wacc.override": "WACC nhập tay",
}


def flatten(inp: dict, prefix: str = "") -> dict[str, float]:
    """Các giá trị số, khóa lồng nhau nối bằng dấu chấm (wacc.rf, scenarios.bear.growth_start)."""
    out: dict[str, float] = {}
    for k, v in inp.items():
        if not prefix and k in SKIP_KEYS:
            continue
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, f"{key}."))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[key] = float(v)
    return out


def _set(inp: dict, key: str, value: Optional[float]) -> None:
    *parents, leaf = key.split(".")
    node = inp
    for p in parents:
        node = node.setdefault(p, {})
    if value is None:
        node.pop(leaf, None)
    else:
        node[leaf] = value


def _per_share(inp: dict) -> Optional[float]:
    """Giá trị base mỗi cổ phiếu, hoặc None nếu bộ giả định không hợp lệ."""
    if dcf.validate(inp):
        return None
    try:
        return dcf.value(inp)["per_share"]
    except dcf.InputError:
        return None


def compare(old: dict, new: dict) -> dict[str, Any]:
    """Liệt kê khóa đã đổi và ảnh hưởng riêng của từng thay đổi lên giá trị base của bản cũ."""
    a, b = flatten(old), flatten(new)
    changed = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
    old_value, new_value = _per_share(old), _per_share(new)

    effects = []
    for key in changed:
        trial = copy.deepcopy(old)
        _set(trial, key, b.get(key))
        value = _per_share(trial)
        effects.append((key, None if value is None or old_value is None else value - old_value))
    effects.sort(key=lambda e: (e[1] is None, -abs(e[1] or 0.0)))

    return {
        "changed": [(k, a.get(k), b.get(k)) for k in changed],
        "old_value": old_value,
        "new_value": new_value,
        "effects": effects,
    }


def _label(key: str) -> str:
    if key.startswith("scenarios."):
        _, name, leaf = key.split(".", 2)
        return f"Kịch bản {name}: {LABELS.get(leaf, leaf)}"
    return LABELS.get(key, key)


def _fmt(key: str, v: Optional[float]) -> str:
    leaf = key.rsplit(".", 1)[-1]
    if v is None:
        return "(không có)"
    if leaf in RATE_KEYS:
        return _p(v, 2)
    if leaf in ("years", "high_growth_years"):
        return str(int(v))
    if leaf == "beta":
        return f"{v:.2f}"
    return _n(v, 0 if leaf in ("price", "vnindex") else 1)


def _mos(per_share: Optional[float], price: Optional[float]) -> str:
    if per_share is None:
        return "-"
    mos = dcf.margin_of_safety(per_share, price)
    return "-" if mos is None else f"{mos:.0%}"


def report(old: dict, new: dict) -> str:
    res = compare(old, new)
    ov, nv = res["old_value"], res["new_value"]
    L = [f"# So sánh: {new['ticker']}, {old.get('as_of', '?')} → {new.get('as_of', '?')}", ""]

    L += ["## Giá trị", "", "| | Bản cũ | Bản mới |", "|---|---:|---:|"]
    L.append(f"| Giá trị ước tính (base), VND/cp | {_n(ov)} | {_n(nv)} |")
    L.append(f"| Giá thị trường, VND/cp | {_n(old.get('price'))} | {_n(new.get('price'))} |")
    L.append(f"| Biên an toàn (base) | {_mos(ov, old.get('price'))} | {_mos(nv, new.get('price'))} |")
    L.append("")
    if ov is None or nv is None:
        L += ["Một trong hai bản lưu chưa đủ giả định hợp lệ nên không tính được giá trị.", ""]
    elif ov:
        L += [f"Giá trị base thay đổi {nv - ov:+,.0f} VND/cp ({(nv - ov) / ov:+.1%}).", ""]

    for title, keys in (
        ("Số liệu đã đổi", [c for c in res["changed"] if c[0] in DATA_KEYS]),
        ("Giả định phán đoán đã đổi", [c for c in res["changed"] if c[0] not in DATA_KEYS]),
    ):
        L += [f"## {title}", ""]
        if not keys:
            L += ["Không có.", ""]
            continue
        L += ["| Mục | Bản cũ | Bản mới |", "|---|---:|---:|"]
        L += [f"| {_label(k)} | {_fmt(k, a)} | {_fmt(k, b)} |" for k, a, b in keys]
        L.append("")

    if res["effects"] and ov is not None and nv is not None:
        L += ["## Mỗi thay đổi làm giá trị base đổi bao nhiêu", ""]
        L += ["Áp riêng từng thay đổi lên bản cũ, giữ nguyên mọi thứ khác.", ""]
        L += ["| Thay đổi | Ảnh hưởng, VND/cp |", "|---|---:|"]
        for key, effect in res["effects"]:
            L.append(f"| {_label(key)} | {'không tính riêng được' if effect is None else f'{effect:+,.0f}'} |")
        known = sum(e for _, e in res["effects"] if e is not None)
        L += ["", f"Phần còn lại do các thay đổi tác động lẫn nhau: {nv - ov - known:+,.0f} VND/cp.", ""]
        if any(key.startswith("scenarios.") for key, _ in res["effects"]):
            L += ["Thay đổi trong kịch bản bear/bull không ảnh hưởng giá trị base.", ""]

    L += ["## Ghi lại trước khi đóng file", ""]
    L += ["- Vì sao từng giả định phán đoán thay đổi, và bằng chứng mới là gì?"]
    L += ["- Thay đổi nào đến từ dữ liệu mới, thay đổi nào chỉ là đổi ý?", ""]
    L.append("Đây là thông tin phục vụ phân tích của bạn, không phải khuyến nghị mua bán.")
    return "\n".join(L)


def _load(path: Path) -> dict:
    return _clean(json.loads(path.read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="valuation.compare", description="So sánh hai bản lưu của cùng một mã.")
    parser.add_argument("targets", nargs="+", help="một mã (dùng hai bản lưu gần nhất) hoặc hai file JSON")
    parser.add_argument("--journal", default="journal", help="thư mục nhật ký (mặc định: journal)")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(args.targets) == 1:
        ticker = args.targets[0]
        paths = sorted(Path(args.journal).glob(f"*_{ticker}.json"))[-2:]
        if len(paths) < 2:
            print(f"Cần ít nhất hai bản lưu của {ticker} trong {args.journal} (lưu bằng --save).", file=sys.stderr)
            return 1
    elif len(args.targets) == 2:
        paths = [Path(t) for t in args.targets]
    else:
        print("Truyền một mã hoặc đúng hai file JSON.", file=sys.stderr)
        return 2

    try:
        old, new = (_load(p) for p in paths)
    except FileNotFoundError as e:
        print(f"Không tìm thấy file: {e.filename}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"File JSON sai cú pháp: {e}", file=sys.stderr)
        return 2
    if old.get("ticker") != new.get("ticker"):
        print(f"Hai bản lưu khác mã: {old.get('ticker')} và {new.get('ticker')}.", file=sys.stderr)
        return 1

    print(report(old, new))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
