"""Dựng memo Markdown một trang từ kết quả phân tích. Chỉ định dạng, không tính toán."""

from __future__ import annotations

import calendar
import datetime as dt
from typing import Any, Optional


def _n(x: Optional[float], digits: int = 0) -> str:
    return "-" if x is None else f"{x:,.{digits}f}"


def _p(x: Optional[float], digits: int = 1) -> str:
    return "-" if x is None else f"{x * 100:.{digits}f}%"


def add_months(d: dt.date, months: int) -> dt.date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def _as_of(inp: dict) -> dt.date:
    raw = inp.get("as_of")
    if raw:
        return dt.date.fromisoformat(raw)
    return dt.date.today()


def _position(price: Optional[float], bear: Optional[float], bull: Optional[float]) -> str:
    if not price or bear is None or bull is None:
        return ""
    if price < bear:
        return "Giá thị trường nằm **dưới** khoảng bear-bull."
    if price > bull:
        return "Giá thị trường nằm **trên** khoảng bear-bull."
    return "Giá thị trường nằm **trong** khoảng bear-bull."


def build_memo(a: dict[str, Any]) -> str:
    inp = a["inp"]
    base = a["base"]
    sc = a["scenarios"]
    sens = a["sensitivity"]
    price = inp.get("price")
    d = _as_of(inp)
    h = int(inp.get("high_growth_years", 5))
    n = int(inp.get("years", 10))
    w = base["wacc"]

    L: list[str] = []
    L.append(f"# Memo định giá: {inp['company']} ({inp['ticker']})")
    L.append("")
    if inp.get("demo"):
        L.append("> **DỮ LIỆU MINH HỌA.** Công ty và số liệu đều giả định, chỉ để xem công cụ chạy. Không dùng để ra quyết định.")
        L.append("")
    L.append(f"Ngày: {d.isoformat()} · Giá thị trường: {_n(price)} VND/cp · Đơn vị tiền: tỷ VND")
    L.append("")

    # 1. Kết luận
    L.append("## 1. Kết luận một dòng")
    L.append("")
    bear = sc["bear"]["per_share"] if sc.get("bear") else None
    bull = sc["bull"]["per_share"] if sc.get("bull") else None
    line = f"Giá trị ước tính (base): **{_n(base['per_share'])} VND/cp**"
    if bear is not None and bull is not None:
        line += f", khoảng bear-bull: {_n(bear)} đến {_n(bull)}."
    else:
        line += "."
    L.append(line)
    if price and a["mos"] is not None:
        L.append(f"Biên an toàn so với giá hiện tại (base): **{_p(a['mos'], 0)}** (âm nghĩa là giá cao hơn giá trị ước tính).")
    pos = _position(price, bear, bull)
    if pos:
        L.append(pos)
    L.append("")
    L.append("Đây là thông tin phục vụ phân tích của bạn, không phải khuyến nghị mua bán.")
    L.append("")

    # 2. Giả định
    L.append("## 2. Giả định chính")
    L.append("")
    L.append("| Giả định | Giá trị |")
    L.append("|---|---|")
    L.append(f"| Doanh thu gốc (TTM) | {_n(inp['revenue'])} tỷ |")
    L.append(f"| Tăng trưởng {h} năm đầu | {_p(inp['growth_start'])} |")
    L.append(f"| Giảm dần về g dài hạn trong {n - h} năm; g dài hạn | {_p(inp['growth_terminal'])} |")
    L.append(f"| Biên EBIT: hiện tại → mục tiêu (sau {h} năm) | {_p(inp['margin_start'])} → {_p(inp['margin_target'])} |")
    L.append(f"| Thuế suất | {_p(inp['tax_rate'], 0)} |")
    L.append(f"| ROIC giai đoạn tăng trưởng / dài hạn | {_p(inp['roic'])} / {_p(inp['roic_terminal'])} |")
    if w["overridden"]:
        L.append(f"| WACC (nhập tay) | {_p(w['wacc'], 2)} |")
    else:
        L.append(f"| Chi phí vốn chủ Ke | {_p(w['ke'], 2)} |")
        L.append(f"| Chi phí nợ sau thuế | {_p(w['kd_after_tax'], 2)} |")
        L.append(f"| Tỷ trọng vốn chủ / nợ | {_p(w['we'], 0)} / {_p(w['wd'], 0)} |")
        L.append(f"| **WACC** | **{_p(w['wacc'], 2)}** |")
    L.append(f"| Nợ ròng | {_n(inp['net_debt'])} tỷ |")
    if inp.get("minorities"):
        L.append(f"| Lợi ích cổ đông không kiểm soát (trừ ra) | {_n(inp['minorities'])} tỷ |")
    if inp.get("associates"):
        L.append(f"| Đầu tư vào công ty liên kết, giá sổ sách (cộng vào) | {_n(inp['associates'])} tỷ |")
    L.append(f"| Số cổ phiếu | {_n(inp['shares_mn'])} triệu |")
    L.append("")
    L.append(
        f"Phân rã: giá trị {n} năm dự phóng {_n(base['pv_explicit'])} tỷ + giá trị cuối kỳ {_n(base['pv_terminal'])} tỷ "
        f"({_p(base['tv_share'], 0)} tổng) = giá trị doanh nghiệp {_n(base['ev'])} tỷ."
    )
    L.append("")

    # 3. Kịch bản
    L.append("## 3. Khoảng giá trị theo kịch bản")
    L.append("")
    L.append("| Kịch bản | Giá trị/cp (VND) | Biên an toàn |")
    L.append("|---|---|---|")
    for name, label in (("bear", "Bear"), ("base", "Base"), ("bull", "Bull")):
        r = sc.get(name)
        if r is None:
            L.append(f"| {label} | chưa định nghĩa | - |")
            continue
        L.append(f"| {label} | {_n(r['per_share'])} | {_p(r['mos'], 0)} |")
    L.append("")

    # 4. Độ nhạy
    L.append("## 4. Độ nhạy: giá trị/cp theo WACC (hàng) và g dài hạn (cột)")
    L.append("")
    head = "| WACC \\ g | " + " | ".join(_p(g, 1) for g in sens["gs"]) + " |"
    L.append(head)
    L.append("|---|" + "---|" * len(sens["gs"]))
    for wv, row in zip(sens["waccs"], sens["grid"]):
        cells = " | ".join(_n(v) if v is not None else "n/a" for v in row)
        L.append(f"| {_p(wv, 2)} | {cells} |")
    L.append("")
    L.append("Đọc bảng này trước khi tin con số base: nếu giá trị đổi nhiều khi lệch 1 điểm %, kết luận còn mong manh.")
    L.append("")

    # 5. Reverse DCF
    L.append("## 5. Reverse DCF: thị trường đang kỳ vọng gì?")
    L.append("")
    rv = a["reverse"]
    implied = rv["growth"]
    if rv["status"] == "no_price":
        L.append("Không tính được vì chưa có giá thị trường.")
    elif rv["status"] == "above_range":
        L.append(
            f"Giá {_n(price)} VND cao đến mức ngay cả khi doanh thu tăng {_p(rv['hi'], 0)}/năm trong {h} năm đầu, "
            "với ROIC, biên và WACC hiện tại, giá trị ước tính vẫn thấp hơn giá. "
            "Hoặc thị trường đang kỳ vọng một điều không nằm trong các giả định này, hoặc giá đang cao hơn giá trị."
        )
    elif rv["status"] == "below_range":
        L.append(
            f"Giá {_n(price)} VND thấp đến mức ngay cả khi doanh thu giảm {_p(abs(rv['lo']), 0)}/năm trong {h} năm đầu, "
            "giá trị ước tính vẫn cao hơn giá. Nên kiểm tra lại dữ liệu đầu vào trước khi tin kết quả này."
        )
    elif implied is None:
        L.append("Không tìm được nghiệm ổn định với các giả định hiện tại.")
    else:
        L.append(
            f"Với giá {_n(price)} VND, thị trường đang ngầm định giá như thể doanh thu tăng khoảng **{_p(implied)}/năm** "
            f"trong {h} năm đầu (giữ nguyên các giả định khác). Giả định của bạn là {_p(inp['growth_start'])}."
        )
        L.append("Câu hỏi để trả lời bằng luận điểm: mức kỳ vọng đó hợp lý hơn, hay giả định của bạn hợp lý hơn, và vì sao?")
    L.append("")

    # 6. Cảnh báo
    L.append("## 6. Cảnh báo tự động")
    L.append("")
    if a["flags"]:
        for f in a["flags"]:
            L.append(f"- {f}")
    else:
        L.append("- Không có cảnh báo từ các kiểm tra tự động. Điều này không có nghĩa là giả định đúng.")
    L.append("")

    # 7. Phần người điền
    L.append("## 7. Phần bạn điền (không để trống khi quyết định)")
    L.append("")
    L.append("**Luận điểm (3 dòng):** doanh nghiệp làm gì, vì sao giá trị cao hơn hoặc thấp hơn giá, điều gì khiến thị trường sai.")
    L.append("")
    L.append("- ")
    L.append("")
    L.append("**Điều gì sẽ khiến mình sai (và dấu hiệu để thoát):**")
    L.append("")
    L.append("- ")
    L.append("")
    L.append("**Red flags từ báo cáo** (dán kết quả đã kiểm chứng từ `prompts/redflags.md`, kèm trang trích dẫn):")
    L.append("")
    L.append("- ")
    L.append("")
    L.append("**Căn cứ cho từng giả định** (nguồn, trang):")
    L.append("")
    L.append("- Tăng trưởng: ")
    L.append("- Biên EBIT: ")
    L.append("- ROIC / tái đầu tư: ")
    L.append("- Beta / ERP / lãi suất: ")
    L.append("")
    L.append(
        f"**Xem lại vào:** {add_months(d, 6).isoformat()} (6 tháng) và {add_months(d, 12).isoformat()} (12 tháng). "
        "Ghi lại: giá lúc đó, VN-Index lúc đó, giả định nào đúng, giả định nào sai."
    )
    L.append("")
    return "\n".join(L)
