# CLAUDE.md: bàn giao cho phiên Claude Code

## Bối cảnh

Người dùng là một kỹ sư (nghiêng về AI/tech), mới bắt đầu học đầu tư, muốn có một công cụ **dùng cá nhân**
để đầu tư có phương hướng theo trường phái định giá doanh nghiệp (DCF, value investing).
Họ đang làm cùng một người bạn (Minh) đang học tài chính và đã có mô hình pro forma trên Excel.
Người dùng nói tiếng Việt: giao tiếp, tài liệu và thông báo lỗi cho người dùng viết bằng tiếng Việt.

Pain point đã chốt: đầu tư theo cảm tính, không có quy trình/luận điểm, không biết giá trị hợp lý,
đọc báo cáo tốn thời gian, không có nhật ký để học từ quyết định của mình.
**Không** phải mục tiêu: tìm edge, dự đoán giá, tự giao dịch, phân tích kỹ thuật.

## Trạng thái hiện tại

MVP chạy được: `python3 -m valuation inputs/demo.json`. Toàn bộ test qua.
Engine DCF đã được đối chiếu độc lập bằng tay (EV và giá trị/cp của demo khớp).
Dữ liệu `demo.json` là **công ty giả định**.

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

1. **`tools/fetch_vnstock.py`**: lấy doanh thu TTM, nợ ròng, số cổ phiếu, giá từ thư viện `vnstock`
   và điền một file JSON nháp theo `inputs/TEMPLATE.json`. Chỉ điền **số liệu**; để trống các giả định phán đoán.
   - Kiểm tra API và giấy phép hiện hành của vnstock trước khi viết (https://vnstocks.com và
     https://github.com/thinh-vu/vnstock). Phiên bản mới có thư viện mở rộng theo gói tài trợ; dùng phần miễn phí.
   - Dữ liệu lấy từ nguồn bên thứ ba và có thể thay đổi/gãy. In rõ nguồn và ngày lấy; nhắc người dùng đối chiếu
     với báo cáo tài chính gốc ít nhất cho lần đầu.
   - Làm sạch đơn vị (tỷ VND, triệu cp, VND/cp) và có test với dữ liệu giả.
2. **Nhật ký kiểm chứng**: một file CSV nhỏ (`journal/log.csv`) ghi mã, ngày, giá, giá trị base/bear/bull,
   VN-Index lúc đó; một lệnh để điền giá và VN-Index tại mốc 6/12 tháng và in so sánh. Mục đích: biết công cụ
   có giúp ích hay không, so với việc chỉ giữ chỉ số.
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
```
