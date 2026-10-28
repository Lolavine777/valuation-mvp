# CLAUDE.md: bàn giao cho phiên Claude Code

## Bối cảnh

Người dùng là một kỹ sư (nghiêng về AI/tech), mới bắt đầu học đầu tư, muốn có một công cụ **dùng cá nhân**
để đầu tư có phương hướng theo trường phái định giá doanh nghiệp (DCF, value investing).
Họ đang làm cùng một người bạn đang học tài chính và đã có mô hình pro forma trên Excel.
Người dùng nói tiếng Việt: giao tiếp, tài liệu và thông báo lỗi cho người dùng viết bằng tiếng Việt.

Pain point đã chốt: đầu tư theo cảm tính, không có quy trình/luận điểm, không biết giá trị hợp lý,
đọc báo cáo tốn thời gian, không có nhật ký để học từ quyết định của mình.
**Không** phải mục tiêu: tìm edge, dự đoán giá, tự giao dịch, phân tích kỹ thuật.

## Trạng thái hiện tại

MVP chạy được: `python3 -m valuation inputs/demo.json`. Toàn bộ test qua.
Engine DCF đã được đối chiếu độc lập bằng tay (EV và giá trị/cp của demo khớp).
Dữ liệu `demo.json` là **công ty giả định**.
`inputs/FPT.json` có số liệu thật lấy từ BCTC gốc của FPT, nguồn và số trang ghi trong `_nguon`.
Các giả định phán đoán của FPT chưa được điền.

## Quy tắc bắt buộc

1. **Tối giản.** Lõi chỉ dùng thư viện chuẩn của Python. Không thêm database, giao diện web, agent framework,
   hay thư viện nặng khi chưa có pain point cụ thể và chưa hỏi người dùng.
2. **Công thức do code, giả định do người, LLM chỉ đọc văn bản.** Không đưa LLM vào `dcf.py`.
   LLM không được tính DCF, không đưa giá mục tiêu, không khuyến nghị mua bán.
3. **Test phải qua trước khi báo xong:** `python3 -m unittest discover -s tests`.
   Thêm test cho mỗi thay đổi hành vi. Không làm yếu các test công thức đóng (perpetuity, ROIC = WACC).
4. **Không bịa số liệu.** Không đưa số liệu công ty thật vào repo trừ khi lấy từ báo cáo tài chính/nguồn đã
   kiểm chứng và ghi nguồn. Không đoán tên hàm hay API của thư viện bên ngoài: đọc tài liệu hoặc chạy thử.
5. **Không biến đầu ra thành khuyến nghị.** Giữ nguyên các câu miễn trừ và cảnh báo trong memo.
6. **Ngân hàng, bảo hiểm, chứng khoán, bất động sản:** mô hình FCFF này không phù hợp. Đừng "vá" cho chạy được;
   nếu người dùng cần, đề xuất mô hình riêng (P/B-ROE, thu nhập thặng dư, NAV) và hỏi trước.

## Việc tiếp theo (theo thứ tự ưu tiên, mỗi lần làm một việc)

1. **Lấy số liệu: đã xong bằng `/bctc <MA>`** (`.claude/skills/bctc`, `prompts/extract_bctc.md`, `tools/draft_input.py`).
   LLM đọc BCTC gốc và chép số kèm trang; script tính TTM, nợ ròng, đổi đơn vị và có test.
   Quyết định ngày 2026-10-27, đừng làm lại:
   - **Không dùng `vnstock`.** PyPI cách ly `vnstock` và `vnai` từ 24/9/2026. Theo CHANGELOG của chính họ, các bản trước
     tự ghi chỉ dẫn vào file cấu hình của trợ lý AI, kể cả file toàn cục của Claude Code, mỗi lần `import`. `vnai` gửi telemetry.
   - **Không gọi API nội bộ của Vietcap hay công ty chứng khoán.** Claude Code chặn vì là lách kiểm soát truy cập, kể cả khi người dùng đồng ý.
   - API chính thức: SSI FastConnect Data miễn phí nhưng chỉ có giá, chỉ số và số cổ phiếu niêm yết, không có BCTC.
     FiinQuant và EODHD có BCTC nhưng trả phí và cần đăng ký. Người dùng chưa muốn đăng ký; có thể xem lại sau.
2. **Nhật ký kiểm chứng: đã xong** (`valuation/journal.py`, `/nhatky`). `--save` ghi một dòng vào `journal/log.csv`
   (demo không ghi); `python3 -m valuation.journal report|update` để xem và điền mốc 6/12 tháng.
   So sánh theo giá, có điều chỉnh thưởng/chia tách qua `--share-factor`, không gồm cổ tức tiền mặt ở cả hai bên.
   Hướng mở rộng khi có đủ mục: tính cả cổ tức tiền mặt (cần VN-Index tổng lợi nhuận, VNINDEX-TR, nếu có nguồn chính thức).
3. **(Tùy chọn) `tools/redflags.py`**: chạy `prompts/redflags.md` trên một thư mục PDF/văn bản bằng LLM API.
   Bắt buộc có trích dẫn và số trang; in cảnh báo rằng đầu ra phải được kiểm chứng. Chỉ làm khi người dùng đã
   thử prompt thủ công và thấy hữu ích.

## Không làm (trừ khi người dùng yêu cầu rõ)

Dự đoán giá, phân tích kỹ thuật, tối ưu danh mục, giao dịch tự động, backtest chiến lược, giao diện web, multi-agent.
Lý do đã thảo luận: bằng chứng ủng hộ yếu, dễ tự lừa mình bằng backtest, và không giải quyết pain point đã chốt.

## Lệnh thường dùng

```bash
python3 -m unittest discover -s tests
python3 -m valuation inputs/demo.json
python3 -m valuation inputs/demo.json --save
python3 -m tools.draft_input sources/<MA>/extraction.json
python3 -m valuation.journal report
python3 -m valuation.compare <MA>
```
