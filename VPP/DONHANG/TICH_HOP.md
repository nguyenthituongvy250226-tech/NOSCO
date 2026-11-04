# Tích hợp đơn hàng và giao hàng

Chạy `python manage.py migrate` trong thư mục `VPP` để tạo schema trước khi dùng các luồng mới.

Các module Django trong dự án gọi nghiệp vụ qua `DONHANG.services`; dữ liệu mã khách hàng, địa chỉ, voucher và biến thể hiện là mã tham chiếu do module tương ứng quản lý.

Module tài khoản cần đặt `request.session["ma_khach_hang"]` sau đăng nhập. Trang khách hàng chỉ truy vấn các đơn mang mã đó; nhân viên đã đăng nhập qua Django Admin được phép xem toàn bộ đơn.

## Tích hợp thông báo khách hàng

`DonHang.ma_khach_hang` là mã tham chiếu tới hồ sơ do module quản lý khách hàng sở hữu. Module thông báo dùng mã này để tìm đúng tài khoản và kênh liên hệ. `ten_nguoi_nhan` và `sdt_nguoi_nhan` là bản chụp thông tin giao hàng của đơn; không dùng thay cho hồ sơ khách hàng.

Các signal được phát sau khi transaction lưu thành công:

- `don_hang_da_tao(sender=DonHang, don_hang=don)`: đơn mới được tạo.
- `don_hang_trang_thai_thay_doi(sender=DonHang, don_hang=don, trang_thai_cu=..., trang_thai_moi=...)`: trạng thái đơn đổi.
- `yeu_cau_tra_hang_da_tao(sender=YeuCauTraHang, yeu_cau=yeu_cau, don_hang=don)`: khách gửi yêu cầu trả hàng.
- `yeu_cau_tra_hang_da_xu_ly(sender=YeuCauTraHang, yeu_cau=yeu_cau, don_hang=don, ket_qua=...)`: nhân viên duyệt, từ chối hoặc hoàn tất yêu cầu. `ket_qua` lần lượt là `da_duyet`, `tu_choi`, `hoan_tat`.

Receiver ví dụ:

```python
from django.dispatch import receiver
from DONHANG.signals import don_hang_da_tao


@receiver(don_hang_da_tao)
def thong_bao_don_moi(sender, *, don_hang, **kwargs):
    ma_khach_hang = don_hang.ma_khach_hang
    # Tra hồ sơ khách trong module quản lý khách hàng rồi tạo thông báo.
```

Không gửi trùng thông báo cho cùng sự kiện nếu receiver cùng nghe signal trạng thái tổng và signal chuyên biệt về trả hàng. Các receiver hiện dùng `send_robust`; lỗi receiver không hủy giao dịch đơn hàng và cần được ghi log/xử lý lại nếu thông báo cần bảo đảm giao nhận.

## Tạo đơn từ giỏ hàng/thanh toán

```python
from DONHANG.services import tao_don_hang

don = tao_don_hang({
    "ma_khach_hang": "KH0001",
    "ma_dia_chi": "DC0001",
    "ma_voucher": "VC0001",  # tùy chọn
    "ten_nguoi_nhan": "Nguyen Van A",
    "sdt_nguoi_nhan": "0900000000",
    "dia_chi_nhan_hang": "So 1, Da Nang",
    "ghi_chu": "Giao giờ hành chính",
    "so_tien_giam": "5000",
    "phi_van_chuyen": "20000",
    "items": [
        {"ma_bien_the": "SP001", "so_luong": 2, "don_gia": "45000"}
    ],
})
```

Hàm tạo đơn trong một transaction, tạo mã đơn/chi tiết/giao hàng và tính tổng tiền hàng cùng tổng thanh toán. `ma_bien_the` và giá phải được lấy, xác minh từ module sản phẩm/giỏ hàng trước khi gọi; đơn hàng giữ lại giá đã chốt tại thời điểm đặt.

## Cập nhật từ module giao hàng

```python
from DONHANG.models import DonHang
from DONHANG.services import cap_nhat_giao_hang

don = DonHang.objects.get(ma_don_hang=ma_don_hang)
cap_nhat_giao_hang(
    don,
    trang_thai="dang_giao",  # cho_lay_hang, dang_giao, da_giao, giao_that_bai, hoan_hang
    don_vi_van_chuyen="NOSCO Express",
    ma_van_don="NX123456",
)
```

Trạng thái vận chuyển tự đồng bộ sang đơn hàng và từng dòng sản phẩm. Trạng thái cấp đơn là `cho_lay_hang`, `cho_giao_hang`, `da_giao` hoặc `tra_hang`.

## API quản trị

API JSON nằm dưới `/don-hang/api/` và yêu cầu tài khoản nhân viên Django đã đăng nhập (session + CSRF):

- `POST /don-hang/api/tao/` nhận cùng cấu trúc JSON như ví dụ `tao_don_hang`.
- `GET /don-hang/api/<ma_don_hang>/` trả đơn, chi tiết và thông tin vận chuyển.
- `POST /don-hang/api/<ma_don_hang>/giao-hang/` nhận `trang_thai` cùng các trường tùy chọn `don_vi_van_chuyen`, `ma_van_don`, `ly_do_that_bai`.

Các endpoint này phục vụ màn hình quản trị. Module nội bộ nên gọi service Python trực tiếp để không cần vòng HTTP.

## Luồng theo use case

- Khách chỉ sửa thông tin người nhận hoặc hủy đơn ở trạng thái `cho_xac_nhan`.
- Nhân viên xử lý tại `/don-hang/nhan-vien/`: xác nhận để chuyển sang `cho_lay_hang`, hoặc chọn hết hàng để hủy.
- Nhân viên cập nhật đơn vị vận chuyển/mã vận đơn và kết quả giao tại cùng màn hình. Khi hãng vận chuyển báo giao thành công, chi tiết đơn hiển thị “Giao hàng thành công” và mở thời hạn 24 giờ để khách gửi yêu cầu trả hàng.
- Nếu khách không gửi yêu cầu trong 24 giờ, đơn tự chuyển từ `cho_xac_nhan_nhan` sang `da_giao`. Chạy `python manage.py chot_don_cho_xac_nhan_qua_han` định kỳ (ví dụ mỗi 5 phút bằng Windows Task Scheduler hoặc cron trên máy chủ). Trang danh sách/chi tiết cũng chốt đơn quá hạn khi được mở.
- Giao thất bại kết thúc đơn ở `da_huy`.
- Khách có thể gửi trả sản phẩm trong vòng 24 giờ sau khi đơn vị vận chuyển báo giao thành công. Mã thanh toán phải do module thanh toán cung cấp.
- Nhân viên xử lý tại `/don-hang/nhan-vien/tra-hang/`. Khi duyệt, chọn đơn vị vận chuyển; mã vận đơn trả được tạo tự động bằng cách đổi tiền tố mã yêu cầu từ `RT` thành `MVD`. Hệ thống phát signal `yeu_cau_tra_hang_da_duyet` để module thanh toán bắt đầu hoàn tiền. Khi từ chối, nhập lý do để khách xem và đơn trở về `da_giao`.
- Yêu cầu trả hàng có tiến độ `cho_xu_ly` → `da_duyet` → `hoan_tat` (hoặc `tu_choi`). Khách xem tiến độ tại `/don-hang/<ma_don_hang>/tra-hang/theo-doi/`; sau khi duyệt, nhân viên cập nhật hoàn tất ở trang xử lý yêu cầu. Module thanh toán có thể nghe `yeu_cau_tra_hang_da_hoan_tat`.
- Module thông báo có thể nghe `don_hang_da_tao`, `don_hang_trang_thai_thay_doi`, `yeu_cau_tra_hang_da_tao` và `yeu_cau_tra_hang_da_xu_ly` để gửi cập nhật cho khách.

Yêu cầu trả hỗ trợ chọn từng dòng sản phẩm và số lượng; dữ liệu này được lưu ở `ChiTietYeuCauTraHang`.
