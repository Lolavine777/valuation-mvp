# Threat model: bước lấy số liệu từ tài liệu bên ngoài

Tài liệu này mô tả rủi ro khi để LLM đọc báo cáo tài chính tải từ internet (lệnh `/bctc` và `prompts/extract_bctc.md`), và các lớp phòng thủ đang có.
Nguyên tắc chung: mọi thứ LLM trả về sau khi đọc tài liệu bên ngoài đều là dữ liệu không tin cậy, cho tới khi code xác định và con người kiểm tra xong.

## Luồng dữ liệu và ranh giới tin cậy

1. PDF và trang web từ nguồn công khai, **không tin cậy**: có thể chứa câu chữ cố ý nhắm vào LLM (prompt injection gián tiếp), hoặc đơn giản là bản scan khó đọc.
2. LLM chép số vào `sources/<MA>/extraction.json`, **không tin cậy**: có thể đọc nhầm chữ số, hoặc bị nội dung tài liệu dẫn dắt.
3. `tools/draft_input.py` kiểm tra schema rồi tính toán, **ranh giới tin cậy**: chỉ những gì qua được bước này mới vào `inputs/<MA>.json`.
4. Người dùng điền giả định phán đoán và đọc memo, **tin cậy**: giả định là việc của người, không bao giờ đến từ tài liệu.

## Mục tiêu của kẻ tấn công và biện pháp hiện có

| Mục tiêu | Biện pháp | Kiểm thử |
|---|---|---|
| Đổi giả định phán đoán (tăng trưởng, ROIC, WACC) để đẩy giá trị lên | `compute()` chỉ dựng các trường số liệu cố định; giả định giữ nguyên từ file cũ hoặc để trống từ TEMPLATE | `test_extraction_cannot_set_judgment_assumptions` |
| Chèn trường lạ hoặc số không có nguồn | Danh sách trường cho phép; mỗi số phải là số không âm và có `doc` cùng `page` | `test_rejects_bad_extractions` |
| Chèn nội dung vào memo, ví dụ thêm một mục "Khuyến nghị: MUA" | `company` và `sector` phải là một dòng ngắn, không có cú pháp markdown | `test_markdown_or_multiline_text_is_rejected` |
| Tắt cảnh báo "mô hình không hợp với ngân hàng" bằng cách để trống `sector` | Cảnh báo xét cả tên công ty | `test_financial_flag_uses_company_name_when_sector_is_blank` |
| Ghi file ra ngoài thư mục `inputs/` qua mã cổ phiếu | `ticker` chỉ gồm chữ và số | `test_rejects_bad_extractions` |
| Bắt LLM tự tính toán hoặc đưa giá mục tiêu | Mọi phép tính nằm trong code có test; prompt cấm tính toán và dặn coi nội dung tài liệu là dữ liệu | Prompt và quy tắc 2 trong `CLAUDE.md` |

## Rủi ro còn lại

- LLM vẫn có thể chép sai một con số mà vẫn đúng schema. Biện pháp: mỗi số có số trang để mở ra đối chiếu, và skill `/bctc` kiểm tra chéo EPS cùng vốn hóa trước khi báo xong.
- Skill `/bctc` chạy trong Claude Code, có quyền dùng công cụ trong lúc đọc tài liệu bên ngoài. Biện pháp: chạy với chế độ hỏi xác nhận, không dùng chế độ bỏ qua mọi xác nhận trên thư mục có thứ khác ngoài dự án này (xem `docs/claude-code-setup.md`).
- `notes` được in ra terminal và lưu trong `_canh_bao`, các dòng trích dẫn (`line`) lưu trong `_nguon`; cả hai không được in vào memo. Nếu sau này đưa chúng vào memo, cần áp cùng quy tắc chữ thường như `company`.
