---
name: nhatky
description: Cập nhật nhật ký kiểm chứng journal/log.csv. Điền giá và VN-Index cho các mục đã đến hạn 6 hoặc 12 tháng, rồi in báo cáo so sánh với việc chỉ giữ VN-Index. Dùng khi người dùng gõ /nhatky, muốn cập nhật nhật ký, hoặc hỏi công cụ định giá có giúp ích không.
---

# /nhatky

Mọi phép tính do `valuation/journal.py` làm. Skill này chỉ tìm số liệu và gọi lệnh.

## Các bước

1. Chạy `python3 -m valuation.journal report` và đọc mục "Cần điền".
   Không có gì cần điền thì gửi báo cáo cho người dùng là xong.

2. Với mỗi mốc đến hạn, tìm từ nguồn công khai:
   - Giá đóng cửa của mã tại ngày đến hạn. Nếu hôm đó không giao dịch, dùng phiên gần nhất trước đó và ghi ngày đó vào `--date`.
     Ưu tiên trang thông tin cổ phiếu của chính công ty.
   - VN-Index đóng cửa **cùng phiên** đó, đối chiếu ít nhất hai nguồn.

3. Tìm sự kiện quyền **giữa ngày ghi và ngày kiểm tra** làm thay đổi số cổ phiếu mỗi cổ đông đang nắm:
   cổ phiếu thưởng, cổ tức bằng cổ phiếu, chia tách.
   `--share-factor` là số cổ phiếu nhận được cho mỗi cổ phiếu ban đầu, nhân dồn nếu có nhiều sự kiện.
   Ví dụ: thưởng 10:1 thì 1.1; thưởng 10:1 rồi chia tách 1:2 thì 2.2.
   Phát hành cho người khác (ESOP, chào bán riêng lẻ) và cổ tức tiền mặt không tính.
   Phát hành quyền mua cho cổ đông hiện hữu: hỏi người dùng trước, vì cách điều chỉnh phụ thuộc giá chào bán.
   Ghi nguồn của từng sự kiện khi báo lại.

4. Chạy cho từng mốc:
   `python3 -m valuation.journal update <MA> <ngày ghi> --at <6|12> --price <giá> --vnindex <điểm> [--share-factor <hệ số>] [--date <ngày>]`

5. Chạy lại `report` và gửi bảng cho người dùng, kèm nguồn của giá, VN-Index và các sự kiện quyền.
   Không diễn giải thành khuyến nghị mua bán. Nhắc rằng ít hơn 10 mục ở mỗi mốc thì chưa kết luận được gì.

## Không làm

- Không bịa hay ước lượng giá. Không tìm được nguồn thì để trống mốc đó và nói rõ với người dùng.
- Không gọi API nội bộ của các công ty chứng khoán hay trang dữ liệu (xem CLAUDE.md).
- Không sửa tay journal/log.csv. Chỉ cập nhật qua lệnh `update`.
