from decimal import Decimal, InvalidOperation
from django.utils import timezone
from .models import Voucher
from .models import Voucher, ChiTietKhuyenMai

def kiem_tra_va_tinh_voucher(ma_voucher, tong_tien_hang, hang_thanh_vien=None):
    """
    Kiểm tra điều kiện voucher và tính số tiền được giảm.

    Trả về:
        {
            "hop_le": True/False,
            "thong_bao": "...",
            "voucher": voucher hoặc None,
            "so_tien_giam": Decimal
        }
    """

    ket_qua = {
        "hop_le": False,
        "thong_bao": "",
        "voucher": None,
        "so_tien_giam": Decimal("0"),
    }

    ma_voucher = (ma_voucher or "").strip().upper()

    try:
        tong_tien_hang = Decimal(str(tong_tien_hang))
    except (InvalidOperation, ValueError, TypeError):
        ket_qua["thong_bao"] = "Giá trị đơn hàng không hợp lệ."
        return ket_qua

    if not tong_tien_hang.is_finite() or tong_tien_hang < 0:
        ket_qua["thong_bao"] = "Giá trị đơn hàng không hợp lệ."
        return ket_qua

    if not ma_voucher:
        ket_qua["thong_bao"] = "Vui lòng nhập mã voucher."
        return ket_qua

    try:
        voucher = Voucher.objects.get(MaVoucher=ma_voucher)
    except Voucher.DoesNotExist:
        ket_qua["thong_bao"] = "Voucher không tồn tại."
        return ket_qua

    ket_qua["voucher"] = voucher

    if not voucher.TrangThai:
        ket_qua["thong_bao"] = "Voucher hiện không còn hoạt động."
        return ket_qua

    thoi_gian_hien_tai = timezone.now()

    if thoi_gian_hien_tai < voucher.NgayBatDau:
        ket_qua["thong_bao"] = "Voucher chưa đến thời gian sử dụng."
        return ket_qua

    if thoi_gian_hien_tai > voucher.NgayKetThuc:
        ket_qua["thong_bao"] = "Voucher đã hết hạn."
        return ket_qua

    if voucher.DieuKienGiam and tong_tien_hang < voucher.DieuKienGiam:
        ket_qua["thong_bao"] = (
            f"Đơn hàng cần đạt tối thiểu "
            f"{voucher.DieuKienGiam:,.0f}đ để sử dụng voucher."
        )
        return ket_qua

    if voucher.DoiTuongApDung != "TatCaThanhVien":
        if hang_thanh_vien != voucher.DoiTuongApDung:
            ket_qua["thong_bao"] = (
                "Voucher không áp dụng cho hạng thành viên của bạn."
            )
            return ket_qua

    if voucher.LoaiGiamGia == "PhanTram":
        so_tien_giam = (
            tong_tien_hang * voucher.GiaTriGiam / Decimal("100")
        )
    else:
        so_tien_giam = voucher.GiaTriGiam

    # Không cho số tiền giảm vượt quá tổng tiền hàng.
    so_tien_giam = min(so_tien_giam, tong_tien_hang)

    ket_qua["hop_le"] = True
    ket_qua["thong_bao"] = "Áp dụng voucher thành công."
    ket_qua["so_tien_giam"] = so_tien_giam.quantize(Decimal("1"))

    return ket_qua

def tinh_gia_khuyen_mai(ma_san_pham, gia_goc):
    gia_goc = Decimal(str(gia_goc))
    thoi_gian_hien_tai = timezone.now()

    chi_tiet = ChiTietKhuyenMai.objects.filter(
        MaSanPham=ma_san_pham,
        TrangThai=True,
        MaKhuyenMai__NgayBatDau__lte=thoi_gian_hien_tai,
        MaKhuyenMai__NgayKetThuc__gte=thoi_gian_hien_tai,
    ).order_by(
        "-MaKhuyenMai__NgayBatDau"
    ).first()

    if not chi_tiet:
        return gia_goc

    gia_sau_giam = gia_goc * (
        Decimal("1") -
        chi_tiet.PhanTramGiam / Decimal("100")
    )

    return max(
        Decimal("0"),
        gia_sau_giam
    ).quantize(Decimal("1"))