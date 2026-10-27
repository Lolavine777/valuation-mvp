---
name: bctc
description: Lấy số liệu định giá cho một mã cổ phiếu (doanh thu TTM, nợ ròng, lợi ích CĐKKS, đầu tư liên kết, số cổ phiếu, giá) từ báo cáo tài chính gốc, rồi tạo hoặc cập nhật inputs/<MA>.json. Dùng khi người dùng gõ /bctc <MA> hoặc muốn lấy, cập nhật số liệu cho một mã.
---

# /bctc <MA>

Skill này chỉ là cách chạy `prompts/extract_bctc.md` trong Claude Code.
Định nghĩa từng trường, quy tắc đọc số và mẫu JSON nằm trong file prompt đó: đọc nó trước, và coi nó là chuẩn duy nhất.
Mọi phép tính do `tools/draft_input.py` làm. Không tự tính TTM, nợ ròng hay đổi đơn vị.

## Các bước

1. **Công cụ đọc PDF.** BCTC Việt Nam thường là PDF scan, đọc bằng Read với tham số `pages` (tối đa 20 trang mỗi lần).
   Read cần `pdftoppm`. Nếu thiếu, chạy `brew install poppler`.

2. **Tìm tài liệu từ nguồn chính thức:** mục công bố thông tin trên trang quan hệ cổ đông của công ty, hoặc trang công bố thông tin của HOSE/HNX.
   Báo chí và trang tổng hợp chỉ dùng để biết tài liệu nào đã có, không dùng làm nguồn cho con số.
   Tải về `sources/<MA>/` (file PDF không được commit). Cần:
   - BCTC hợp nhất kỳ gần nhất. Nếu không phải cả năm, thêm BCTC hợp nhất năm trước đã kiểm toán.
   - Công bố thông tin sau ngày kết thúc kỳ về thay đổi số cổ phiếu: cổ phiếu thưởng, cổ tức bằng cổ phiếu, ESOP, chào bán, mua cổ phiếu quỹ.
     Có thì tải văn bản ghi tổng số cổ phiếu mới, thường là nghị quyết HĐQT về tăng vốn điều lệ.
   - Giá đóng cửa gần nhất có ghi ngày, ưu tiên trang thông tin cổ phiếu của chính công ty.

3. **Đọc số.** Bảng cân đối và kết quả kinh doanh thường ở khoảng trang PDF 5-15.
   Thuyết minh vốn chủ sở hữu (số cổ phiếu đang lưu hành) nằm ở nửa sau báo cáo.
   Đọc cả chú thích dưới các bảng: thay đổi phạm vi hợp nhất và số liệu trình bày lại thường chỉ được nêu ở đó.

4. **Ghi `sources/<MA>/extraction.json`** đúng mẫu trong prompt, mỗi số có `doc` và `page` là số trang PDF.

5. **Chạy** `python3 -m tools.draft_input sources/<MA>/extraction.json`.
   Nếu báo lỗi, mở lại trang để sửa extraction. Không sửa script để cho qua.

6. **Kiểm tra chéo trước khi báo xong**, nêu kết quả cho người dùng:
   - Lợi nhuận sau thuế của cổ đông công ty mẹ chia số cổ phiếu tại ngày kết thúc kỳ phải xấp xỉ EPS in trên báo cáo.
   - Giá nhân số cổ phiếu dùng để định giá phải xấp xỉ vốn hóa trên một trang công khai cùng ngày.
     Lệch hơn vài phần trăm thường là do có phát hành cổ phiếu sau ngày kết thúc kỳ mà bạn chưa tìm thấy.

7. **Báo lại cho người dùng:** bảng số liệu kèm trang, các cảnh báo script in ra, và các giả định còn phải điền.
   Không tự điền giả định phán đoán (tăng trưởng, biên EBIT, ROIC, beta, ERP, lãi suất): đó là việc của người dùng (quy tắc 2 trong CLAUDE.md).

## Không làm

- Không bịa hay ước lượng số. Không tìm thấy thì để trống trường đó, ghi vào `notes`, và nói rõ với người dùng.
- Không gọi API nội bộ của các công ty chứng khoán hay trang dữ liệu để lấy số. Chỉ đọc tài liệu công bố công khai.
- Ngân hàng, bảo hiểm, chứng khoán, bất động sản: mô hình này không phù hợp (quy tắc 6 trong CLAUDE.md). Báo người dùng trước khi làm tiếp.
