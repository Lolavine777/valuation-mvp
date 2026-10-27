"""Dòng lệnh: python -m valuation inputs/demo.json [--save]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import dcf
from .memo import build_memo


def _clean(obj):
    """Bỏ các khóa ghi chú bắt đầu bằng dấu gạch dưới (dùng trong TEMPLATE.json)."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if not k.startswith("_")}
    return obj


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="valuation", description="Định giá DCF tối giản, xuất memo Markdown.")
    parser.add_argument("input", help="file JSON đầu vào, ví dụ inputs/demo.json")
    parser.add_argument("--save", action="store_true", help="lưu memo vào journal/<ngày>_<mã>.md")
    parser.add_argument("--journal", default="journal", help="thư mục nhật ký (mặc định: journal)")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    path = Path(args.input)
    try:
        inp = _clean(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        print(f"Không tìm thấy file: {path}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"File JSON sai cú pháp ({path}): {e}", file=sys.stderr)
        return 2

    try:
        analysis = dcf.analyze(inp)
    except dcf.InputError as e:
        print(f"Đầu vào chưa hợp lệ: {e}", file=sys.stderr)
        return 1

    memo = build_memo(analysis)
    print(memo)

    if args.save:
        d = inp.get("as_of") or __import__("datetime").date.today().isoformat()
        out_dir = Path(args.journal)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{d}_{inp['ticker']}.md"
        out.write_text(memo, encoding="utf-8")
        print(f"\n[Đã lưu: {out}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
