from django.dispatch import receiver
from DONHANG.signals import don_hang_da_tao
from .models import HoSoKhachHang, ThongBao


@receiver(don_hang_da_tao)
def tao_thong_bao_khi_dat_hang(sender, don_hang, **kwargs):
    # Tìm hồ sơ khách hàng tương ứng với đơn hàng
    ho_so = HoSoKhachHang.objects.select_related(
        "MaNguoiDung"
    ).filter(
        MaHoSo=don_hang.ma_khach_hang
    ).first()

    if not ho_so:
        return

    # Tạo thông báo cho tài khoản khách hàng
    ThongBao.objects.create(
        MaNguoiNhan=ho_so.MaNguoiDung,
        TieuDe="Đặt hàng thành công",
        NoiDung=(
            f"Đơn hàng {don_hang.ma_don_hang} của bạn đã được tạo "
            "thành công và đang chờ xác nhận."
        ),
        LoaiThongBao="DON_HANG",
        DaDoc=False,
    )