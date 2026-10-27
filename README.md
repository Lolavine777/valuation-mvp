# valuation-mvp

Công cụ định giá DCF tối giản để lập **luận điểm đầu tư có kỷ luật** cho một doanh nghiệp.
Nhập giả định → nhận memo một trang: khoảng giá trị, độ nhạy, thị trường đang kỳ vọng gì, cảnh báo.

Không dự đoán giá, không khuyến nghị mua bán, không giao dịch tự động.
Đây là thông tin phục vụ phân tích của bạn, không phải tư vấn tài chính.

## Chạy thử (30 giây)

Cần Python 3.10 trở lên. Không cần cài gì thêm.

```bash
python3 -m valuation inputs/demo.json            # in memo ra màn hình
python3 -m valuation inputs/demo.json --save     # lưu vào journal/<ngày>_<mã>.md
python3 -m unittest discover -s tests            # chạy toàn bộ test
```

`inputs/demo.json` là **công ty giả định**, số liệu minh họa, chỉ để xem công cụ chạy.

## Dùng cho một công ty thật (khoảng 10 phút)

1. Sao chép `inputs/TEMPLATE.json` thành `inputs/<MA>.json`.
2. Điền **số liệu** từ báo cáo tài chính: doanh thu 12 tháng gần nhất, nợ ròng, số cổ phiếu, giá.
3. Điền **giả định phán đoán**: tăng trưởng, biên EBIT, ROIC, beta, ERP, lãi suất phi rủi ro.
   Chỗ này là nơi giá trị được quyết định, và là việc của người, không phải của công cụ.
4. Chạy, đọc memo, điền phần 7 (luận điểm, điều gì sẽ làm mình sai, căn cứ từng giả định).
5. Lưu bằng `--save`, xem lại sau 6 và 12 tháng.

## Triết lý thiết kế (20/80)

| Việc | Ai làm | Vì sao |
|---|---|---|
| Công thức DCF, WACC, độ nhạy, reverse DCF | Code xác định (`valuation/dcf.py`) | Phép tính phải lặp lại được và kiểm thử được |
| Đọc thuyết minh, báo cáo thường niên, đánh dấu bất thường | LLM hỗ trợ (`prompts/redflags.md`) | Đây là chỗ AI thực sự tiết kiệm thời gian, nhưng mọi trích dẫn phải được kiểm chứng |
| Giả định về tương lai (tăng trưởng, biên, ROIC, rủi ro) | Con người | Giá trị nằm ở các giả định này, AI không có thông tin nội bộ |
| Kiểm chứng | Nhật ký + so với VN-Index sau 6-12 tháng | Chỉ tin sau khi có dữ liệu |

Nguyên tắc: mỗi thành phần phải trả lời được "giải quyết pain point nào?". Không trả lời được thì bỏ.
Vì vậy: chỉ dùng thư viện chuẩn, không database, không giao diện, không agent framework.

## Cách đọc memo

- **Khoảng giá trị (bear / base / bull)** quan trọng hơn con số base. Giá nằm ở đâu trong khoảng này?
- **Bảng độ nhạy**: nếu lệch 1 điểm % WACC làm giá trị đổi rất nhiều, kết luận còn mong manh.
  Khi ROIC dài hạn ≈ WACC, tăng trưởng dài hạn gần như không thêm giá trị. Đó là kinh tế học, không phải lỗi.
- **Reverse DCF**: giữ giả định khác, thị trường đang ngầm kỳ vọng tăng trưởng bao nhiêu? Hãy trả lời bằng luận điểm.
- **Giá trị cuối kỳ** thường chiếm 60-80% tổng. Nếu trên 75% công cụ sẽ cảnh báo.
- **Biên an toàn** = 1 − giá / giá trị. Âm nghĩa là giá cao hơn giá trị ước tính.

## Mô hình làm gì

FCFF 10 năm: tăng trưởng giữ cao `high_growth_years` năm đầu rồi giảm tuyến tính về g dài hạn;
biên EBIT dịch tuyến tính tới mục tiêu; tái đầu tư = tăng trưởng / ROIC; giá trị cuối kỳ theo công thức Gordon
với ROIC dài hạn riêng; WACC từ CAPM và chi phí nợ, tỷ trọng theo giá thị trường (hoặc nhập tay).
Kiểm tra tính đúng đắn: mô hình khớp công thức đóng (perpetuity) khi không tăng trưởng, và cho thấy
tăng trưởng không tạo giá trị khi ROIC = WACC (xem `tests/test_dcf.py`).

## Hạn chế cần biết

- **Không dùng cho ngân hàng, bảo hiểm, chứng khoán, bất động sản.** Với các ngành này nợ là nguyên liệu kinh doanh;
  dùng P/B và ROE, mô hình thu nhập thặng dư hoặc NAV. Công cụ sẽ cảnh báo nếu trường `sector` thuộc nhóm này.
- DCF nhạy với giả định. Kết quả là một khoảng, không phải sự thật.
- Chiết khấu cuối năm (không giữa năm); tỷ trọng WACC theo giá thị trường (không theo giá trị nội tại);
  beta, ERP và lãi suất phi rủi ro nhập tay, chưa lấy tự động.
- Tái đầu tư năm t tính theo tăng trưởng của chính năm t (g_t / ROIC), không theo tăng trưởng năm sau.
  Khi tăng trưởng không đổi, hai cách cho cùng kết quả; trong giai đoạn tăng trưởng giảm dần, cách này cho FCFF hơi thấp hơn (thận trọng).
- Chưa nối dữ liệu thật. Số liệu phải nhập tay từ báo cáo tài chính.
- Một công ty chạy tốt không chứng minh phương pháp. Cần so sánh trên nhiều mã qua 6-12 tháng.

## Cấu trúc

```
valuation/dcf.py     engine tính toán (không I/O)
valuation/memo.py    dựng memo Markdown
valuation/cli.py     dòng lệnh
inputs/              file JSON đầu vào (demo.json, TEMPLATE.json)
prompts/redflags.md  prompt cho LLM đọc báo cáo
tests/               unittest
journal/             memo đã lưu, để xem lại sau 6-12 tháng
CLAUDE.md            bàn giao cho phiên Claude Code tiếp theo
START_HERE.md        cách cài Claude Code và câu lệnh đầu tiên
```
