from uuid import uuid4

from .models import ThanhToan


def tao_thanh_toan_cho_don(don_hang, phuong_thuc):
    phuong_thuc_hop_le = dict(
        ThanhToan._meta.get_field("PhuongThucThanhToan").choices
    )
    if phuong_thuc not in phuong_thuc_hop_le:
        raise ValueError("Phương thức thanh toán không hợp lệ.")

    return ThanhToan.objects.create(
        MaThanhToan=f"TT{uuid4().hex[:8].upper()}",
        DonHang=don_hang,
        PhuongThucThanhToan=phuong_thuc,
        SoTienThanhToan=don_hang.tong_tien,
        TrangThaiThanhToan="ChoThanhToan",
        LoaiGiaoDich="ThanhToan",
        MaGiaoDich=None if phuong_thuc == "COD" else uuid4().hex.upper(),
    )
