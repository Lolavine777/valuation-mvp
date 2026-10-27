# Bắt đầu làm tiếp trong Claude Code

Gói này đã chạy được. Việc còn lại là mở nó trong Claude Code để làm các bước tiếp theo.
Cần khoảng 10 phút. Python 3.10 trở lên (kiểm tra bằng `python3 --version`; trên Windows có thể là `python --version`).

## 1. Cài Claude Code

Cách khuyến nghị theo tài liệu chính thức (https://code.claude.com/docs/en/setup):

| Máy | Lệnh |
|---|---|
| macOS, Linux, WSL | `curl -fsSL https://claude.ai/install.sh \| bash` |
| Windows PowerShell | `irm https://claude.ai/install.ps1 \| iex` |
| Windows CMD | `curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd` |
| Homebrew | `brew install --cask claude-code` |
| WinGet | `winget install Anthropic.ClaudeCode` |

Cài xong, **mở cửa sổ terminal mới** và chạy `claude --version`. In ra số phiên bản là được.
Nếu báo không tìm thấy lệnh `claude`, xem mục "command not found" tại https://code.claude.com/docs/en/troubleshoot-install.md

Cần tài khoản Pro, Max, Team, Enterprise hoặc Console. Gói miễn phí của claude.ai không có Claude Code.
Nếu bạn thích giao diện đồ họa, ứng dụng Claude Desktop cũng chạy được Claude Code.

## 2. Giải nén và kiểm tra

```bash
unzip valuation-mvp.zip
cd valuation-mvp
python3 -m unittest discover -s tests     # phải thấy: Ran 19 tests ... OK
python3 -m valuation inputs/demo.json     # in memo của công ty giả định
```

Nếu hai lệnh trên chạy được thì máy bạn đã sẵn sàng. Làm bước này **trước** khi mở Claude Code
để có mốc so sánh: nếu sau này có gì hỏng, bạn biết nó hỏng ở đâu.

## 3. (Khuyến nghị) Bật git để hoàn tác được

```bash
git init && git add -A && git commit -m "MVP ban đầu"
```

Nhờ đó mỗi thay đổi của Claude Code đều xem lại và hoàn tác được bằng `git diff` và `git restore`.

## 4. Mở Claude Code trong thư mục dự án

```bash
claude
```

Lần đầu sẽ mở trình duyệt để đăng nhập. Claude Code tự đọc `CLAUDE.md` trong thư mục hiện tại,
trong đó đã có bối cảnh, quy tắc bắt buộc và danh sách việc cần làm.

## 5. Câu lệnh đầu tiên (dán nguyên văn)

```
Đọc CLAUDE.md và README.md, rồi chạy bộ test và lệnh demo để xác nhận mọi thứ đang chạy.
Sau đó đọc valuation/dcf.py và tóm tắt cho tôi trong 10 dòng: mô hình làm gì, giả định nào
được ngầm đặt vào, và chỗ nào bạn thấy rủi ro. Chưa sửa gì cả.
```

Lý do bắt đầu như vậy: bạn có một người đọc độc lập kiểm tra code trước khi cho nó thay đổi gì.
Nếu tóm tắt của nó khác với README, đó là tín hiệu cần xem lại.

## 6. Rồi mới giao việc, mỗi lần một việc

Theo thứ tự trong `CLAUDE.md`. Ví dụ việc số 1:

```
Làm việc 1 trong CLAUDE.md: tools/fetch_vnstock.py.
Trước khi viết code, đọc tài liệu và giấy phép hiện hành của vnstock và cho tôi biết:
(a) dùng được phần miễn phí cho mục đích cá nhân không, (b) hàm nào lấy được doanh thu TTM,
nợ ròng, số cổ phiếu, giá. Chưa viết code cho đến khi tôi đồng ý.
```

Các quy tắc trong `CLAUDE.md` (tối giản, không bịa số liệu, không biến đầu ra thành khuyến nghị,
test phải qua) sẽ được áp dụng cho mọi việc.

## Mẹo làm việc

- Mỗi việc kết thúc bằng `python3 -m unittest discover -s tests` và một commit.
- Khi dữ liệu thật vào, **đối chiếu với báo cáo tài chính gốc** ít nhất lần đầu. Dữ liệu từ thư viện bên thứ ba có thể sai hoặc đổi định dạng.
- Đừng để công cụ chạy ở chế độ bỏ qua mọi xác nhận trên thư mục chứa thứ khác ngoài dự án này.
- Kết quả của công cụ là thông tin để bạn phân tích, không phải khuyến nghị đầu tư.
