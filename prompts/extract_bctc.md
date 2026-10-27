# Prompt: trích số liệu từ báo cáo tài chính gốc

Mục đích: lấy các **số liệu** cần cho `inputs/<MA>.json` thẳng từ báo cáo tài chính (BCTC) gốc, mỗi số kèm trang để kiểm chứng.
LLM chỉ đọc và chép số. Mọi phép tính (TTM, nợ ròng, đổi đơn vị) do `tools/draft_input.py` làm, có test.

## Cách dùng

- **Trong Claude Code:** gõ `/bctc <MA>`. Skill `.claude/skills/bctc` làm toàn bộ các bước dưới đây.
- **Không có Claude Code:** đưa prompt bên dưới cùng các file PDF cho bất kỳ AI nào đọc được PDF, kể cả PDF dạng ảnh scan.
  Lưu JSON trả về thành `sources/<MA>/extraction.json`, rồi chạy:

```bash
python3 -m tools.draft_input sources/<MA>/extraction.json
```

Script kiểm tra JSON, tính toán và ghi `inputs/<MA>.json`.
Nếu file đã có, script chỉ cập nhật số liệu và giữ nguyên các giả định bạn đã điền.

## Tài liệu cần có

1. BCTC **hợp nhất** của kỳ gần nhất (quý, bán niên hoặc năm), từ trang quan hệ cổ đông của công ty hoặc trang công bố thông tin của HOSE/HNX.
2. Nếu kỳ gần nhất không phải cả năm: BCTC hợp nhất năm gần nhất trước đó (đã kiểm toán).
3. Nếu sau ngày kết thúc kỳ có phát hành thêm hoặc mua lại cổ phiếu (cổ phiếu thưởng, cổ tức bằng cổ phiếu, ESOP, chào bán): công bố thông tin chính thức ghi số cổ phiếu mới.
4. Giá đóng cửa gần nhất từ một trang công khai, ưu tiên trang nhà đầu tư của chính công ty, có ghi ngày.

## Prompt

```
Bạn trích số liệu từ báo cáo tài chính cho một công cụ định giá. Chỉ chép số in trên tài liệu được cung cấp.
Không tính toán, không ước lượng, không dùng kiến thức bên ngoài về công ty. Không tìm thấy thì bỏ trống trường đó và ghi vào "notes".

Quy tắc đọc số:
- Tìm chỉ tiêu theo TÊN, không theo mã số. Mã số khác nhau giữa các chế độ kế toán
  (ví dụ Thông tư 200 và Thông tư 99 áp dụng từ 2026).
- Chép số như in nhưng bỏ dấu phân cách hàng nghìn. Số trong ngoặc là số âm.
- "page" là số trang PDF (trang thứ mấy trong file, như trình xem PDF hiển thị), không phải số trang in ở chân trang.
- Ghi đơn vị tiền in trên báo cáo vào documents.<khóa>.unit: "VND", "nghìn VND", "triệu VND" hoặc "tỷ VND".
- Dùng BCTC hợp nhất. Chỉ dùng BCTC riêng khi công ty không có công ty con, và ghi rõ trong notes.

Các trường trong "values" (mỗi trường: value, doc, page, line = tên chỉ tiêu như in):
- revenue_ytd: Doanh thu thuần về bán hàng và cung cấp dịch vụ, lũy kế từ đầu năm tài chính đến ngày kết thúc kỳ.
- revenue_ytd_prior: cùng chỉ tiêu, cùng kỳ năm trước, lấy ở cột so sánh của chính báo cáo kỳ này.
- revenue_fy_prior: cùng chỉ tiêu, cả năm tài chính trước, từ BCTC năm. Bỏ qua cả hai trường này nếu kỳ gần nhất là cả năm.
- revenue_ytd_prior_comparable: CHỈ điền khi báo cáo nêu thay đổi phạm vi hợp nhất hoặc phương pháp kế toán
  và có trình bày lại số cùng kỳ năm trước theo cơ sở mới (thường ở thuyết minh "Thông tin khái quát" hoặc "Số liệu so sánh").
- cash: Tiền và các khoản tương đương tiền, cuối kỳ.
- short_term_investments: Các khoản đầu tư tài chính ngắn hạn (dòng tổng), cuối kỳ.
- short_term_debt: Vay và nợ thuê tài chính ngắn hạn, cuối kỳ.
- long_term_debt: Vay và nợ thuê tài chính dài hạn, cuối kỳ.
- minorities: Lợi ích cổ đông không kiểm soát (thuộc vốn chủ sở hữu), cuối kỳ.
- associates: Đầu tư vào công ty liên doanh, liên kết (thuộc đầu tư tài chính dài hạn), cuối kỳ. Không có dòng này thì value = 0, trích trang bảng cân đối.
- shares_outstanding: Số cổ phiếu đang lưu hành tại ngày kết thúc kỳ, đơn vị cổ phiếu, từ thuyết minh vốn chủ sở hữu.
- shares_outstanding_current: CHỈ điền khi có tài liệu số 3. Tổng số cổ phiếu sau thay đổi, trừ cổ phiếu quỹ nếu có.

"price": giá đóng cửa, đơn vị VND/cổ phiếu, kèm "date" (YYYY-MM-DD) và "source" (URL).

"notes": liệt kê ngắn mọi điều làm số liệu khó so sánh hoặc cần người xem lại: thay đổi phạm vi hợp nhất, trình bày lại số liệu,
ý kiến kiểm toán/soát xét không phải chấp nhận toàn phần, sự kiện sau ngày kết thúc kỳ ảnh hưởng tới số cổ phiếu hoặc nợ.

Trả về DUY NHẤT một JSON theo mẫu sau, không kèm giải thích:

{
  "ticker": "MA",
  "company": "Tên công ty như in trên báo cáo",
  "sector": "Ngành chính",
  "period_end": "YYYY-MM-DD",
  "months": 6,
  "documents": {
    "A": {"title": "BCTC hợp nhất bán niên 2026 đã soát xét", "source": "URL", "unit": "VND"},
    "B": {"title": "BCTC hợp nhất năm 2025 đã kiểm toán", "source": "URL", "unit": "VND"}
  },
  "values": {
    "revenue_ytd": {"value": 0, "doc": "A", "page": 0, "line": "Doanh thu thuần về bán hàng và cung cấp dịch vụ"}
  },
  "price": {"value": 0, "date": "YYYY-MM-DD", "source": "URL"},
  "notes": []
}
```

## Sau khi có JSON

Kiểm tra ít nhất vài số bằng cách mở đúng trang được trích dẫn.
LLM có thể đọc nhầm chữ số trên bản scan, nhầm cột kỳ này với kỳ trước, hoặc nhầm đơn vị.
Script bắt được lỗi cấu trúc và một số mâu thuẫn, nhưng không bắt được một con số đọc sai mà vẫn hợp lý.
