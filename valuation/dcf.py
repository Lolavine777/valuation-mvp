"""Engine định giá DCF tối giản: FCFF, giai đoạn tăng trưởng cao rồi giảm dần về g dài hạn.

Thiết kế 20/80:
- Chỉ dùng thư viện chuẩn của Python, không phụ thuộc gì khác.
- Mọi phép tính là công thức xác định. Không có AI trong file này.
- Đầu ra không phải một con số mà là: kịch bản, bảng độ nhạy, reverse DCF, cảnh báo.

Đơn vị quy ước: tiền tính bằng tỷ VND, số cổ phiếu tính bằng triệu cp,
giá trị mỗi cổ phiếu tính bằng VND. Đổi đơn vị chỉ cần sửa hằng số PER_SHARE_FACTOR.
"""

from __future__ import annotations

import copy
from typing import Any, Optional

PER_SHARE_FACTOR = 1000.0  # (tỷ VND * 1e9) / (triệu cp * 1e6) = tỷ * 1000 / triệu cp

REQUIRED = [
    "company",
    "ticker",
    "revenue",
    "growth_start",
    "growth_terminal",
    "margin_start",
    "margin_target",
    "tax_rate",
    "roic",
    "roic_terminal",
    "net_debt",
    "shares_mn",
    "wacc",
]

SCENARIO_KEYS = (
    "growth_start",
    "growth_terminal",
    "margin_start",
    "margin_target",
    "roic",
    "roic_terminal",
    "high_growth_years",
    "years",
)

FINANCIAL_KEYWORDS = (
    "ngân hàng",
    "bảo hiểm",
    "chứng khoán",
    "bất động sản",
    "bank",
    "insurance",
    "securities",
    "real estate",
)


class InputError(ValueError):
    """Dữ liệu đầu vào sai hoặc thiếu."""


def _years(inp: dict) -> tuple[int, int]:
    return int(inp.get("years", 10)), int(inp.get("high_growth_years", 5))


def validate(inp: dict) -> list[str]:
    """Trả về danh sách lỗi (rỗng nếu hợp lệ), viết bằng tiếng Việt để sửa nhanh."""
    errors: list[str] = []
    for key in REQUIRED:
        if key not in inp or inp[key] is None:
            errors.append(f"thiếu trường '{key}'")
    if errors:
        return errors

    n, h = _years(inp)
    if h < 1:
        errors.append("high_growth_years phải >= 1")
    if n <= h:
        errors.append("years phải lớn hơn high_growth_years")
    if inp["revenue"] <= 0:
        errors.append("revenue phải > 0")
    if inp["shares_mn"] <= 0:
        errors.append("shares_mn phải > 0")
    if not 0 <= inp["tax_rate"] < 1:
        errors.append("tax_rate phải nằm trong [0, 1), ví dụ 0.20")
    if inp["roic"] <= 0 or inp["roic_terminal"] <= 0:
        errors.append("roic và roic_terminal phải > 0")

    w = inp["wacc"]
    if not isinstance(w, dict):
        errors.append("wacc phải là object")
    elif "override" not in w:
        for key in ("rf", "erp", "beta", "cost_of_debt"):
            if key not in w:
                errors.append(f"thiếu wacc.{key} (hoặc dùng wacc.override)")
        if "equity_weight" not in w and not inp.get("price"):
            errors.append("cần 'price' hoặc wacc.equity_weight hoặc wacc.override để tính tỷ trọng vốn")
    return errors


def compute_wacc(inp: dict) -> dict[str, Any]:
    """WACC = we*Ke + wd*Kd*(1-t). Ke = rf + beta*ERP. Tỷ trọng theo giá thị trường."""
    w = inp["wacc"]
    if "override" in w:
        return {"wacc": float(w["override"]), "ke": None, "kd_after_tax": None, "we": None, "wd": None, "overridden": True}

    ke = w["rf"] + w["beta"] * w["erp"]
    kd_after = w["cost_of_debt"] * (1 - inp["tax_rate"])
    debt = w.get("debt", max(inp["net_debt"], 0.0))
    if "equity_weight" in w:
        we = float(w["equity_weight"])
    else:
        equity_mkt = inp["price"] * inp["shares_mn"] / PER_SHARE_FACTOR
        we = equity_mkt / (equity_mkt + debt)
    wd = 1 - we
    return {
        "wacc": we * ke + wd * kd_after,
        "ke": ke,
        "kd_after_tax": kd_after,
        "we": we,
        "wd": wd,
        "overridden": False,
    }


def project(inp: dict) -> list[dict]:
    """Dự phóng doanh thu, biên EBIT, NOPAT, tái đầu tư và FCFF theo từng năm."""
    n, h = _years(inp)
    g0, g_term = inp["growth_start"], inp["growth_terminal"]
    m0, m_target = inp["margin_start"], inp["margin_target"]
    tax, roic = inp["tax_rate"], inp["roic"]

    rows = []
    revenue = inp["revenue"]
    for t in range(1, n + 1):
        growth = g0 if t <= h else g0 + (g_term - g0) * (t - h) / (n - h)
        margin = m0 + (m_target - m0) * min(t, h) / h
        revenue *= 1 + growth
        ebit = revenue * margin
        nopat = ebit * (1 - tax)
        reinvest_rate = growth / roic  # tái đầu tư = tăng trưởng / ROIC
        fcff = nopat * (1 - reinvest_rate)
        rows.append(
            {
                "year": t,
                "growth": growth,
                "revenue": revenue,
                "margin": margin,
                "ebit": ebit,
                "nopat": nopat,
                "reinvest_rate": reinvest_rate,
                "fcff": fcff,
            }
        )
    return rows


def value(inp: dict) -> dict[str, Any]:
    """Định giá một bộ giả định. Ném InputError nếu WACC <= g dài hạn."""
    n, _ = _years(inp)
    wacc_info = compute_wacc(inp)
    wacc = wacc_info["wacc"]
    g_term = inp["growth_terminal"]
    if wacc <= g_term:
        raise InputError(f"WACC ({wacc:.2%}) phải lớn hơn tăng trưởng dài hạn ({g_term:.2%})")

    rows = project(inp)
    pv_explicit = 0.0
    for r in rows:
        r["discount"] = 1 / (1 + wacc) ** r["year"]
        r["pv"] = r["fcff"] * r["discount"]
        pv_explicit += r["pv"]

    nopat_next = rows[-1]["nopat"] * (1 + g_term)
    fcff_next = nopat_next * (1 - g_term / inp["roic_terminal"])
    terminal_value = fcff_next / (wacc - g_term)
    pv_terminal = terminal_value / (1 + wacc) ** n

    ev = pv_explicit + pv_terminal
    equity = ev - inp["net_debt"] - inp.get("minorities", 0.0)
    per_share = equity * PER_SHARE_FACTOR / inp["shares_mn"]

    return {
        "wacc": wacc_info,
        "rows": rows,
        "pv_explicit": pv_explicit,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "tv_share": pv_terminal / ev if ev else float("nan"),
        "ev": ev,
        "equity": equity,
        "per_share": per_share,
    }


def margin_of_safety(per_share: float, price: Optional[float]) -> Optional[float]:
    """Biên an toàn = 1 - giá / giá trị. Âm nghĩa là giá cao hơn giá trị ước tính."""
    if not price or per_share <= 0:
        return None
    return 1 - price / per_share


def scenarios(inp: dict) -> dict[str, Optional[dict]]:
    """Chạy bear/base/bull. Mỗi kịch bản chỉ ghi đè các giả định có trong whitelist."""
    out: dict[str, Optional[dict]] = {}
    overrides = inp.get("scenarios", {})
    for name in ("bear", "base", "bull"):
        x = copy.deepcopy(inp)
        if name != "base":
            for key, val in overrides.get(name, {}).items():
                if key in SCENARIO_KEYS:
                    x[key] = val
                elif key == "wacc_override":
                    x["wacc"] = {"override": val}
        if name != "base" and name not in overrides:
            out[name] = None
            continue
        try:
            out[name] = value(x)
        except InputError:
            out[name] = None
    return out


def sensitivity(
    inp: dict,
    wacc_deltas: tuple[float, ...] = (-0.02, -0.01, 0.0, 0.01, 0.02),
    g_deltas: tuple[float, ...] = (-0.01, -0.005, 0.0, 0.005, 0.01),
) -> dict[str, Any]:
    """Bảng giá trị mỗi cổ phiếu theo WACC (hàng) và tăng trưởng dài hạn (cột)."""
    base_wacc = compute_wacc(inp)["wacc"]
    base_g = inp["growth_terminal"]
    waccs = [base_wacc + d for d in wacc_deltas]
    gs = [base_g + d for d in g_deltas]
    grid: list[list[Optional[float]]] = []
    for w in waccs:
        row = []
        for g in gs:
            x = copy.deepcopy(inp)
            x["wacc"] = {"override": w}
            x["growth_terminal"] = g
            try:
                row.append(value(x)["per_share"])
            except InputError:
                row.append(None)
        grid.append(row)
    return {"waccs": waccs, "gs": gs, "grid": grid}


def reverse_dcf(inp: dict, lo: float = -0.10, hi: float = 0.40) -> dict[str, Any]:
    """Tìm tăng trưởng doanh thu giai đoạn đầu mà thị trường đang ngầm định giá.

    Giữ nguyên mọi giả định khác, chỉ thay growth_start sao cho giá trị = giá hiện tại.
    Trả về {"growth": số hoặc None, "status": ...} với status là một trong:
    ok, no_price, above_range (giá cao hơn cả khi tăng trưởng = hi),
    below_range (giá thấp hơn cả khi tăng trưởng = lo), no_root.
    """
    price = inp.get("price")
    if not price:
        return {"growth": None, "status": "no_price", "lo": lo, "hi": hi}

    def f(g: float) -> Optional[float]:
        x = copy.deepcopy(inp)
        x["growth_start"] = g
        try:
            return value(x)["per_share"] - price
        except InputError:
            return None

    f_lo, f_hi = f(lo), f(hi)
    out = {"growth": None, "status": "no_root", "lo": lo, "hi": hi}
    if f_lo is None or f_hi is None:
        return out
    if f_lo * f_hi > 0:
        if f_lo < 0 and f_hi < 0:
            out["status"] = "above_range"
        elif f_lo > 0 and f_hi > 0:
            out["status"] = "below_range"
        return out
    for _ in range(100):
        mid = (lo + hi) / 2
        f_mid = f(mid)
        if f_mid is None:
            return out
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
        if hi - lo < 1e-7:
            break
    out["growth"] = (lo + hi) / 2
    out["status"] = "ok"
    return out


def flags(inp: dict, res: dict) -> list[str]:
    """Cảnh báo tự động về các giả định dễ làm méo kết quả."""
    out: list[str] = []
    wacc = res["wacc"]["wacc"]
    g_term = inp["growth_terminal"]
    sector = str(inp.get("sector", "")).lower()

    if any(k in sector for k in FINANCIAL_KEYWORDS):
        out.append(
            "Ngành tài chính hoặc bất động sản: FCFF này không phù hợp (nợ là nguyên liệu kinh doanh). "
            "Nên dùng P/B và ROE, mô hình thu nhập thặng dư hoặc NAV. Coi kết quả chỉ để tham khảo."
        )
    rf = inp["wacc"].get("rf")
    if rf is not None and g_term >= rf:
        out.append(f"Tăng trưởng dài hạn ({g_term:.1%}) >= lãi suất phi rủi ro ({rf:.1%}): thường là quá lạc quan.")
    if g_term > 0.05:
        out.append(f"Tăng trưởng dài hạn {g_term:.1%} cao hơn mức thường coi là tối đa cho nền kinh tế danh nghĩa.")
    if res["tv_share"] > 0.75:
        out.append(
            f"Giá trị cuối kỳ chiếm {res['tv_share']:.0%} tổng giá trị: kết quả phụ thuộc chủ yếu vào giả định dài hạn."
        )
    if inp["roic"] <= wacc:
        out.append("ROIC giai đoạn tăng trưởng <= WACC: tăng trưởng không tạo ra giá trị, có thể hủy giá trị.")
    if inp["roic_terminal"] > wacc + 0.03:
        out.append(
            f"ROIC dài hạn ({inp['roic_terminal']:.1%}) cao hơn WACC hơn 3 điểm %: ngầm giả định lợi thế cạnh tranh tồn tại mãi mãi."
        )
    if inp["margin_target"] - inp["margin_start"] > 0.03:
        out.append("Biên EBIT mục tiêu cao hơn biên hiện tại hơn 3 điểm %: cần một luận điểm cụ thể cho việc này.")
    if inp["growth_start"] > 0.15:
        out.append(
            f"Tăng trưởng {inp['growth_start']:.0%}/năm kéo dài {_years(inp)[1]} năm: rất ít doanh nghiệp giữ được."
        )
    if res["equity"] <= 0:
        out.append("Giá trị vốn chủ sở hữu <= 0 theo các giả định này.")
    if not inp.get("price"):
        out.append("Chưa có giá thị trường: không tính được biên an toàn và reverse DCF.")
    return out


def analyze(inp: dict) -> dict[str, Any]:
    """Chạy toàn bộ phân tích. Ném InputError với danh sách lỗi nếu đầu vào không hợp lệ."""
    errors = validate(inp)
    if errors:
        raise InputError("; ".join(errors))
    base = value(inp)
    return {
        "inp": inp,
        "base": base,
        "scenarios": scenarios(inp),
        "sensitivity": sensitivity(inp),
        "reverse": reverse_dcf(inp),
        "mos": margin_of_safety(base["per_share"], inp.get("price")),
        "flags": flags(inp, base),
    }
