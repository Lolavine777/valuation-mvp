"""Tạo inputs/<MA>.json từ số liệu đã trích từ BCTC (JSON theo prompts/extract_bctc.md).

Chỉ điền số liệu: doanh thu TTM, nợ ròng, lợi ích CĐKKS, đầu tư liên kết, số cổ phiếu, giá.
Các giả định phán đoán (tăng trưởng, biên, ROIC, WACC...) giữ nguyên nếu file đã có,
hoặc lấy khung trống từ inputs/TEMPLATE.json nếu là file mới.

Dùng: python3 -m tools.draft_input sources/FPT/extraction.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from valuation import dcf

ROOT = Path(__file__).resolve().parent.parent

UNIT_TO_TY = {"VND": 1e-9, "nghìn VND": 1e-6, "triệu VND": 1e-3, "tỷ VND": 1.0}

REQUIRED = (
    "revenue_ytd",
    "cash",
    "short_term_investments",
    "short_term_debt",
    "long_term_debt",
    "minorities",
    "associates",
    "shares_outstanding",
)
OPTIONAL = ("revenue_ytd_prior", "revenue_fy_prior", "revenue_ytd_prior_comparable", "shares_outstanding_current")
JUDGMENTS = ("growth_start", "growth_terminal", "margin_start", "margin_target", "roic", "roic_terminal")
WACC_JUDGMENTS = ("rf", "erp", "cost_of_debt")


MAX_TEXT = 120
MARKDOWN_CHARS = "#*_`[]<>|!\\"


def _plain_text(v: Any) -> bool:
    return isinstance(v, str) and len(v) <= MAX_TEXT and v.isprintable() and not any(c in MARKDOWN_CHARS for c in v)


class ExtractionError(ValueError):
    """File trích xuất sai hoặc thiếu."""


def _is_date(v: Any) -> bool:
    try:
        dt.date.fromisoformat(v)
        return True
    except (TypeError, ValueError):
        return False


def check(ex: dict) -> list[str]:
    """Trả về danh sách lỗi (rỗng nếu hợp lệ). Mỗi con số bắt buộc phải có trích dẫn tài liệu và trang."""
    errors: list[str] = []
    docs = ex.get("documents")
    if not isinstance(docs, dict) or not docs:
        return ["thiếu 'documents'"]
    for key, d in docs.items():
        if not isinstance(d, dict) or d.get("unit") not in UNIT_TO_TY:
            errors.append(f"documents.{key}.unit phải là một trong: {', '.join(UNIT_TO_TY)}")
    if not str(ex.get("ticker", "")).isalnum():
        errors.append("ticker chỉ gồm chữ và số")
    if not ex.get("company"):
        errors.append("thiếu 'company'")
    # Văn bản do LLM chép từ tài liệu bên ngoài sẽ vào memo: chỉ cho phép một dòng ngắn, không có cú pháp markdown.
    for key in ("company", "sector"):
        text = ex.get(key)
        if text is not None and not _plain_text(text):
            errors.append(f"{key} phải là một dòng chữ thường, tối đa {MAX_TEXT} ký tự, không chứa {MARKDOWN_CHARS}")
    if not _is_date(ex.get("period_end")):
        errors.append("period_end phải có dạng YYYY-MM-DD")
    months = ex.get("months")
    if months not in (3, 6, 9, 12):
        errors.append("months phải là 3, 6, 9 hoặc 12")

    values = ex.get("values")
    if not isinstance(values, dict):
        return errors + ["thiếu 'values'"]
    need = REQUIRED if months == 12 else REQUIRED + ("revenue_ytd_prior", "revenue_fy_prior")
    errors += [f"thiếu values.{key}" for key in need if key not in values]
    for key, v in values.items():
        if key not in REQUIRED + OPTIONAL:
            errors.append(f"values.{key}: trường không được hỗ trợ (chỉ: {', '.join(REQUIRED + OPTIONAL)})")
            continue
        num = v.get("value") if isinstance(v, dict) else None
        # Lợi ích CĐKKS có thể âm khi công ty con lỗ lũy kế; các số còn lại không thể âm.
        if not dcf._is_number(num) or (num < 0 and key != "minorities"):
            errors.append(f"values.{key}.value phải là số" + ("" if key == "minorities" else " >= 0"))
        elif v.get("doc") not in docs or not isinstance(v.get("page"), int) or v["page"] < 1:
            errors.append(f"values.{key} cần trích dẫn: 'doc' (một khóa trong documents) và 'page' (số trang PDF)")

    price = ex.get("price")
    if not isinstance(price, dict):
        errors.append("thiếu 'price'")
    else:
        if not dcf._is_number(price.get("value")) or price["value"] <= 0:
            errors.append("price.value phải là số > 0 (VND/cp)")
        if not _is_date(price.get("date")):
            errors.append("price.date phải có dạng YYYY-MM-DD")
        if not price.get("source"):
            errors.append("price.source: ghi nguồn giá (URL)")
        vni = ex.get("vnindex")
        if vni is not None:
            if not isinstance(vni, dict) or not dcf._is_number(vni.get("value")) or vni["value"] <= 0:
                errors.append("vnindex.value phải là số > 0 (điểm)")
            elif vni.get("date") != price.get("date"):
                errors.append("vnindex.date phải trùng price.date: nhật ký so sánh giá và VN-Index cùng một phiên")
            elif not vni.get("source"):
                errors.append("vnindex.source: ghi nguồn (URL)")
    return errors


def _ty(ex: dict, key: str) -> float:
    v = ex["values"][key]
    return v["value"] * UNIT_TO_TY[ex["documents"][v["doc"]]["unit"]]


def compute(ex: dict) -> tuple[dict[str, Any], list[str]]:
    """Tính các trường số liệu của inputs/<MA>.json (tỷ VND, triệu cp, VND/cp) và danh sách cảnh báo."""
    errors = check(ex)
    if errors:
        raise ExtractionError("; ".join(errors))
    vals = ex["values"]
    warnings = [str(n) for n in ex.get("notes", [])]

    revenue = _ty(ex, "revenue_ytd")
    if ex["months"] != 12:
        prior, fy_prior = _ty(ex, "revenue_ytd_prior"), _ty(ex, "revenue_fy_prior")
        if prior >= fy_prior:
            raise ExtractionError(
                "revenue_ytd_prior phải nhỏ hơn revenue_fy_prior: lũy kế cùng kỳ không thể lớn hơn cả năm. "
                "Kiểm tra lại cột và đơn vị."
            )
        rest = fy_prior - prior  # phần còn lại của năm trước, để ghép thành 12 tháng gần nhất
        if "revenue_ytd_prior_comparable" in vals:
            ratio = _ty(ex, "revenue_ytd_prior_comparable") / prior
            rest *= ratio
            warnings.append(
                f"Phạm vi hợp nhất thay đổi: phần {12 - ex['months']} tháng còn lại của năm trước được quy đổi "
                f"theo tỷ lệ cùng kỳ trình bày lại ({ratio:.1%}). Doanh thu TTM là ước tính."
            )
        revenue += rest

    net_debt = (
        _ty(ex, "short_term_debt")
        + _ty(ex, "long_term_debt")
        - _ty(ex, "cash")
        - _ty(ex, "short_term_investments")
    )
    shares_key = "shares_outstanding_current" if "shares_outstanding_current" in vals else "shares_outstanding"
    if shares_key == "shares_outstanding_current":
        before, after = vals["shares_outstanding"]["value"], vals[shares_key]["value"]
        warnings.append(
            f"Số cổ phiếu thay đổi sau ngày {ex['period_end']}: {before:,} → {after:,} cp. "
            "Dùng số mới nhất để khớp với giá hiện tại."
        )
    data = {
        "company": ex["company"],
        "ticker": ex["ticker"],
        "as_of": ex["price"]["date"],
        "price": ex["price"]["value"],
        "shares_mn": round(vals[shares_key]["value"] / 1e6, 3),
        "revenue": round(revenue, 1),
        "net_debt": round(net_debt, 1),
        "minorities": round(_ty(ex, "minorities"), 1),
        "associates": round(_ty(ex, "associates"), 1),
        # Luôn ghi, kể cả None: giữ VN-Index cũ bên cạnh giá mới sẽ làm sai nhật ký kiểm chứng.
        "vnindex": ex["vnindex"]["value"] if ex.get("vnindex") else None,
    }
    if data["vnindex"] is None:
        warnings.append("Chưa có VN-Index cùng ngày với giá: nhật ký kiểm chứng sẽ thiếu mốc so sánh.")
    return data, warnings


def _sources(ex: dict) -> dict[str, Any]:
    """Ghi lại nguồn của từng con số để kiểm chứng sau này."""
    vni = ex.get("vnindex")
    return {
        "vnindex": f"{vni['value']:,} điểm ngày {vni['date']} ({vni['source']})" if vni else "",
        "lay_ngay": dt.date.today().isoformat(),
        "ky_bao_cao": f"{ex['months']} tháng kết thúc {ex['period_end']}",
        "tai_lieu": {k: f"{d.get('title', '')} ({d.get('source', '')})" for k, d in ex["documents"].items()},
        "so_lieu": {
            k: f"{v['value']:,} · tài liệu {v['doc']}, trang PDF {v['page']}: {v.get('line', '')}"
            for k, v in ex["values"].items()
        },
        "gia": f"{ex['price']['value']:,} VND/cp ngày {ex['price']['date']} ({ex['price']['source']})",
    }


def unfilled(doc: dict) -> list[str]:
    """Các giả định phán đoán còn để 0 như trong TEMPLATE (dcf.validate coi 0 là hợp lệ nên không báo)."""
    todo = [k for k in JUDGMENTS if not doc.get(k)]
    w = doc.get("wacc", {})
    if "override" not in w:
        todo += [f"wacc.{k}" for k in WACC_JUDGMENTS if not w.get(k)]
    return todo


def draft(ex: dict, out_dir: Path) -> tuple[Path, dict[str, Any], list[str]]:
    """Ghi inputs/<MA>.json. File đã có thì chỉ thay số liệu, giữ nguyên giả định phán đoán."""
    data, warnings = compute(ex)
    out = out_dir / f"{data['ticker']}.json"
    existed = out.exists()
    src = out if existed else ROOT / "inputs" / "TEMPLATE.json"
    doc = json.loads(src.read_text(encoding="utf-8"))
    doc.update(data)
    # Ô "sector" của TEMPLATE là câu hướng dẫn có chữ "ngân hàng": không được giữ lại, kẻo bị cảnh báo nhầm.
    if ex.get("sector") or not existed:
        doc["sector"] = ex.get("sector", "")
    if not existed:
        doc["_ghi_chu"] = (
            "Tạo bởi tools/draft_input.py. Tiền: tỷ VND. Số cổ phiếu: triệu cp. Giá: VND/cp. Tỷ lệ: 0.10 = 10%. "
            "Số liệu có nguồn trong _nguon; các giả định phán đoán do bạn điền. Chạy lại script chỉ cập nhật số liệu."
        )
    doc["_nguon"] = _sources(ex)
    doc["_canh_bao"] = warnings
    out_dir.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out, data, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="draft_input", description="Tạo inputs/<MA>.json từ số liệu trích từ BCTC.")
    parser.add_argument("extraction", help="file JSON trích xuất, ví dụ sources/FPT/extraction.json")
    parser.add_argument("--out-dir", default=str(ROOT / "inputs"), help="thư mục ghi (mặc định: inputs)")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    path = Path(args.extraction)
    try:
        ex = json.loads(path.read_text(encoding="utf-8"))
        out, data, warnings = draft(ex, Path(args.out_dir))
    except FileNotFoundError:
        print(f"Không tìm thấy file: {path}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"File JSON sai cú pháp ({path}): {e}", file=sys.stderr)
        return 2
    except ExtractionError as e:
        print(f"Số liệu trích xuất chưa hợp lệ: {e}", file=sys.stderr)
        return 1

    print(f"Đã ghi {out}")
    print(f"  Doanh thu TTM:          {data['revenue']:>12,.1f} tỷ")
    print(f"  Nợ ròng:                {data['net_debt']:>12,.1f} tỷ (âm là dư tiền)")
    print(f"  Lợi ích CĐKKS:          {data['minorities']:>12,.1f} tỷ")
    print(f"  Đầu tư liên kết:        {data['associates']:>12,.1f} tỷ")
    print(f"  Số cổ phiếu:            {data['shares_mn']:>12,.3f} triệu")
    print(f"  Giá ({data['as_of']}): {data['price']:>12,.0f} VND/cp")
    if data["vnindex"] is not None:
        print(f"  VN-Index cùng ngày:     {data['vnindex']:>12,.2f} điểm")
    if warnings:
        print("\nCảnh báo:")
        for w in warnings:
            print(f"  - {w}")
    todo = unfilled(json.loads(out.read_text(encoding="utf-8")))
    if todo:
        print(f"\nGiả định còn để 0, cần bạn điền trước khi chạy định giá: {', '.join(todo)}")
    print("\nMở đúng trang được trích dẫn trong _nguon để kiểm tra lại ít nhất vài con số.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
