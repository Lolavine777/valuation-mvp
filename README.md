# valuation-mvp

Công cụ định giá DCF tối giản để lập **luận điểm đầu tư có kỷ luật** cho một doanh nghiệp.
Nhập giả định → nhận memo một trang: khoảng giá trị, độ nhạy, thị trường đang kỳ vọng gì, cảnh báo.

Không dự đoán giá, không khuyến nghị mua bán, không giao dịch tự động.
Đây là thông tin phục vụ phân tích của bạn, không phải tư vấn tài chính.

## Chạy thử (30 giây)

Cần Python 3.10 trở lên. Không cần cài gì thêm.

```bash
python3 -m valuation inputs/demo.json            # in memo ra màn hình
python3 -m valuation inputs/demo.json --save     # lưu vào journal/<ngày>_<mã>.md (demo không ghi nhật ký)
python3 -m valuation.journal report              # nhật ký kiểm chứng: so với VN-Index, các mốc cần điền
python3 -m unittest discover -s tests            # chạy toàn bộ test
```

`inputs/demo.json` là **công ty giả định**, số liệu minh họa, chỉ để xem công cụ chạy.

## Dùng cho một công ty thật (khoảng 10 phút)

1. Lấy **số liệu** từ báo cáo tài chính gốc vào `inputs/<MA>.json`: doanh thu 12 tháng gần nhất, nợ ròng,
   lợi ích cổ đông không kiểm soát, đầu tư vào công ty liên kết, số cổ phiếu, giá.
   - Trong Claude Code: gõ `/bctc <MA>`. Skill tìm BCTC trên trang công ty, đọc số kèm số trang, rồi chạy script tính toán.
   - Không có Claude Code: đưa `prompts/extract_bctc.md` cùng file PDF cho bất kỳ AI nào đọc được PDF, lưu JSON trả về
     thành `sources/<MA>/extraction.json`, rồi chạy `python3 -m tools.draft_input sources/<MA>/extraction.json`.
   - Hoặc tự sao chép `inputs/TEMPLATE.json` và điền tay.
2. Mở vài trang được trích dẫn trong `_nguon` để kiểm tra số. AI có thể đọc nhầm chữ số trên bản scan.
3. Điền **giả định phán đoán**: tăng trưởng, biên EBIT, ROIC, beta, ERP, lãi suất phi rủi ro.
   Chỗ này là nơi giá trị được quyết định, và là việc của người, không phải của công cụ.
4. Chạy, đọc memo, điền phần 7 (luận điểm, điều gì sẽ làm mình sai, căn cứ từng giả định).
5. Lưu bằng `--save`. Memo vào `journal/<ngày>_<mã>.md`, một dòng vào nhật ký kiểm chứng `journal/log.csv`.
6. Sau 6 và 12 tháng, điền giá và VN-Index lúc đó (xem mục dưới) và xem lại giả định nào đúng, giả định nào sai.

Chạy lại `/bctc` hoặc `tools.draft_input` khi có BCTC mới: chỉ số liệu được cập nhật, giả định bạn đã điền được giữ nguyên.

## Nhật ký kiểm chứng: công cụ có giúp ích không?

Mục đích là trả lời bằng dữ liệu của chính bạn: các mã bạn định giá có làm tốt hơn việc chỉ giữ VN-Index không.

- Mỗi lần `--save` một công ty thật, `journal/log.csv` có thêm một dòng: mã, ngày, giá, giá trị bear/base/bull, biên an toàn, VN-Index.
  VN-Index lấy từ trường `vnindex` trong file đầu vào (`/bctc` điền sẵn) hoặc từ `--vnindex`.
- `python3 -m valuation.journal report` in bảng so sánh, tổng hợp theo nhóm giá dưới hay trên base lúc ghi, và các mốc đã đến hạn kèm lệnh để điền.
- Điền một mốc: `python3 -m valuation.journal update FPT 2026-10-27 --at 6 --price 61000 --vnindex 1812.5`.
  Nếu giữa chừng có thưởng cổ phiếu hoặc chia tách, thêm `--share-factor` (thưởng 10:1 là 1.1) để giá trước và sau so được với nhau.
- Trong Claude Code: gõ `/nhatky`. Skill tìm giá, VN-Index và các sự kiện quyền rồi điền giúp.

So sánh theo giá, không gồm cổ tức tiền mặt ở cả hai bên (VN-Index cũng là chỉ số giá).
Dưới 10 mục ở mỗi mốc thì chưa kết luận được gì.

## Triết lý thiết kế (20/80)

| Việc | Ai làm | Vì sao |
|---|---|---|
| Công thức DCF, WACC, độ nhạy, reverse DCF | Code xác định (`valuation/dcf.py`) | Phép tính phải lặp lại được và kiểm thử được |
| Chép số liệu từ BCTC gốc (thường là PDF scan) | LLM đọc, kèm số trang (`prompts/extract_bctc.md`) | Không có nguồn dữ liệu miễn phí, chính thức nào khác; số trang giúp kiểm chứng nhanh |
| Tính TTM, nợ ròng, đổi đơn vị từ số đã chép | Code xác định (`tools/draft_input.py`) | LLM không làm phép tính |
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
- Số liệu do AI chép từ BCTC gốc. AI có thể đọc nhầm số trên bản scan; script bắt lỗi cấu trúc và vài mâu thuẫn,
  nhưng không bắt được một con số sai mà vẫn trông hợp lý. Luôn kiểm tra vài số với trang được trích dẫn.
- Khi phạm vi hợp nhất thay đổi (ví dụ một công ty con chuyển thành công ty liên kết), doanh thu TTM là ước tính:
  phần còn lại của năm trước được quy đổi theo tỷ lệ của số cùng kỳ đã trình bày lại.
- Đầu tư vào công ty liên kết được cộng vào vốn chủ theo **giá sổ sách**, có thể thấp hơn nhiều so với giá trị thật
  (ví dụ khi công ty liên kết đã niêm yết).
- Một công ty chạy tốt không chứng minh phương pháp. Cần so sánh trên nhiều mã qua 6-12 tháng.

## Cấu trúc

```
valuation/dcf.py     engine tính toán (không I/O)
valuation/memo.py    dựng memo Markdown
valuation/cli.py     dòng lệnh
valuation/journal.py nhật ký kiểm chứng (journal/log.csv): ghi, điền mốc 6/12 tháng, báo cáo
inputs/              file JSON đầu vào (demo.json, TEMPLATE.json, <MA>.json)
prompts/redflags.md  prompt cho LLM đọc báo cáo, đánh dấu bất thường
prompts/extract_bctc.md  prompt cho LLM chép số liệu từ BCTC, kèm số trang
tools/draft_input.py từ số liệu đã chép tạo inputs/<MA>.json (TTM, nợ ròng, đơn vị)
sources/<MA>/        BCTC đã tải (PDF không commit) và extraction.json
.claude/skills/bctc  lệnh /bctc trong Claude Code
.claude/skills/nhatky  lệnh /nhatky trong Claude Code
tests/               unittest
journal/             memo đã lưu và log.csv, để xem lại sau 6-12 tháng
CLAUDE.md            bàn giao cho phiên Claude Code tiếp theo
START_HERE.md        cách cài Claude Code và câu lệnh đầu tiên
```
