# Memo định giá: DEMO Co (công ty giả định) (DEMO)

> **DỮ LIỆU MINH HỌA.** Công ty và số liệu đều giả định, chỉ để xem công cụ chạy. Không dùng để ra quyết định.

Ngày: 2026-10-27 · Giá thị trường: 22,000 VND/cp · Đơn vị tiền: tỷ VND

## 1. Kết luận một dòng

Giá trị ước tính (base): **18,625 VND/cp**, khoảng bear-bull: 12,802 đến 25,719.
Biên an toàn so với giá hiện tại (base): **-18%** (âm nghĩa là giá cao hơn giá trị ước tính).
Giá thị trường nằm **trong** khoảng bear-bull.

Đây là thông tin phục vụ phân tích của bạn, không phải khuyến nghị mua bán.

## 2. Giả định chính

| Giả định | Giá trị |
|---|---|
| Doanh thu gốc (TTM) | 10,000 tỷ |
| Tăng trưởng 5 năm đầu | 10.0% |
| Giảm dần về g dài hạn trong 5 năm; g dài hạn | 3.5% |
| Biên EBIT: hiện tại → mục tiêu (sau 5 năm) | 10.0% → 12.0% |
| Thuế suất | 20% |
| ROIC giai đoạn tăng trưởng / dài hạn | 14.0% / 11.0% |
| Chi phí vốn chủ Ke | 11.50% |
| Chi phí nợ sau thuế | 6.80% |
| Tỷ trọng vốn chủ / nợ | 85% / 15% |
| **WACC** | **10.78%** |
| Nợ ròng | 1,500 tỷ |
| Số cổ phiếu | 500 triệu |

Phân rã: giá trị 10 năm dự phóng 3,574 tỷ + giá trị cuối kỳ 7,239 tỷ (67% tổng) = giá trị doanh nghiệp 10,813 tỷ.

## 3. Khoảng giá trị theo kịch bản

| Kịch bản | Giá trị/cp (VND) | Biên an toàn |
|---|---|---|
| Bear | 12,802 | -72% |
| Base | 18,625 | -18% |
| Bull | 25,719 | 14% |

## 4. Độ nhạy: giá trị/cp theo WACC (hàng) và g dài hạn (cột)

| WACC \ g | 2.5% | 3.0% | 3.5% | 4.0% | 4.5% |
|---|---|---|---|---|---|
| 8.78% | 27,328 | 28,103 | 28,999 | 30,053 | 31,321 |
| 9.78% | 22,163 | 22,539 | 22,956 | 23,422 | 23,951 |
| 10.78% | 18,304 | 18,462 | 18,625 | 18,795 | 18,974 |
| 11.78% | 15,324 | 15,358 | 15,384 | 15,398 | 15,400 |
| 12.78% | 12,965 | 12,928 | 12,876 | 12,807 | 12,718 |

Đọc bảng này trước khi tin con số base: nếu giá trị đổi nhiều khi lệch 1 điểm %, kết luận còn mong manh.

## 5. Reverse DCF: thị trường đang kỳ vọng gì?

Với giá 22,000 VND, thị trường đang ngầm định giá như thể doanh thu tăng khoảng **18.0%/năm** trong 5 năm đầu (giữ nguyên các giả định khác). Giả định của bạn là 10.0%.
Câu hỏi để trả lời bằng luận điểm: mức kỳ vọng đó hợp lý hơn, hay giả định của bạn hợp lý hơn, và vì sao?

## 6. Cảnh báo tự động

- Không có cảnh báo từ các kiểm tra tự động. Điều này không có nghĩa là giả định đúng.

## 7. Phần bạn điền (không để trống khi quyết định)

**Luận điểm (3 dòng):** doanh nghiệp làm gì, vì sao giá trị cao hơn hoặc thấp hơn giá, điều gì khiến thị trường sai.

- 

**Điều gì sẽ khiến mình sai (và dấu hiệu để thoát):**

- 

**Red flags từ báo cáo** (dán kết quả đã kiểm chứng từ `prompts/redflags.md`, kèm trang trích dẫn):

- 

**Căn cứ cho từng giả định** (nguồn, trang):

- Tăng trưởng: 
- Biên EBIT: 
- ROIC / tái đầu tư: 
- Beta / ERP / lãi suất: 

**Xem lại vào:** 2027-04-27 (6 tháng) và 2027-10-27 (12 tháng). Ghi lại giả định nào đúng, giả định nào sai. Giá và VN-Index lúc đó điền vào nhật ký: `python3 -m valuation.journal report` liệt kê các mốc đến hạn.

