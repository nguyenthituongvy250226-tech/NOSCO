
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum

from KHACHHANG.models import HoSoKhachHang, LichSuTichDiem
from THANHTOAN.models import ThanhToan


# =====================================================
# 1. CẤU HÌNH CHƯƠNG TRÌNH KHÁCH HÀNG THÂN THIẾT
# =====================================================

GIA_TRI_QUY_DOI = Decimal("10000")

CAC_HANG_THANH_VIEN = [
    (0, "Thành viên"),
    (100, "Đồng"),
    (300, "Bạc"),
    (600, "Vàng"),
    (1000, "Kim cương"),
]


# =====================================================
# 2. TÍNH ĐIỂM THEO GIÁ TRỊ ĐƠN HÀNG
# =====================================================

def tinh_diem_don_hang(don):
    """
    10.000 đồng = 1 điểm.

    Chỉ tính trên giá trị hàng sau giảm giá.
    Không tính phí vận chuyển.
    """

    tong_tien_hang = Decimal(str(don.tong_tien_hang or 0))
    so_tien_giam = Decimal(str(don.so_tien_giam or 0))

    gia_tri_tinh_diem = max(
        tong_tien_hang - so_tien_giam,
        Decimal("0")
    )

    diem = (
        gia_tri_tinh_diem / GIA_TRI_QUY_DOI
    ).to_integral_value(rounding=ROUND_FLOOR)

    return int(diem)


# =====================================================
# 3. XÁC ĐỊNH HẠNG THÀNH VIÊN
# =====================================================

def xac_dinh_hang_thanh_vien(tong_diem):
    """
    Xác định hạng dựa trên số dư điểm hiện tại.
    """

    hang = "Thành viên"

    for moc_diem, ten_hang in CAC_HANG_THANH_VIEN:
        if tong_diem >= moc_diem:
            hang = ten_hang

    return hang


# =====================================================
# 4. CẬP NHẬT ĐIỂM VÀ HẠNG THÀNH VIÊN
# =====================================================

def cap_nhat_diem_va_hang(ho_so, so_diem_thay_doi):
    """
    Cộng hoặc trừ điểm.
    Sau đó tự động xác định lại hạng thành viên.
    """

    diem_hien_tai = ho_so.DiemTichLuy or 0

    diem_moi = max(
        diem_hien_tai + so_diem_thay_doi,
        0
    )

    ho_so.DiemTichLuy = diem_moi

    ho_so.HangThanhVien = xac_dinh_hang_thanh_vien(
        diem_moi
    )

    ho_so.save(
        update_fields=[
            "DiemTichLuy",
            "HangThanhVien",
        ]
    )

    return diem_moi, ho_so.HangThanhVien


# =====================================================
# 5. GHI NHẬN LỊCH SỬ ĐIỂM
# =====================================================

def ghi_lich_su_diem(
    ho_so,
    don,
    loai_giao_dich,
    so_diem,
    noi_dung,
):
    """
    Ghi nhận lịch sử cộng/trừ điểm.
    """

    return LichSuTichDiem.objects.create(
        MaKhachHang=ho_so,
        MaDonHang=don.ma_don_hang,
        LoaiGiaoDich=loai_giao_dich,
        SoDiem=so_diem,
        NoiDung=noi_dung,
        SoDuDiem=ho_so.DiemTichLuy,
    )


# =====================================================
# 6. CỘNG ĐIỂM SAU KHI THANH TOÁN THÀNH CÔNG
# =====================================================

def cong_diem_sau_thanh_toan(thanh_toan, don, ho_so):
    """
    Chỉ cộng điểm khi:
    - Giao dịch thuộc loại ThanhToan.
    - Trạng thái là DaThanhToan.
    - Đơn hàng chưa được cộng điểm trước đó.
    """

    da_cong = LichSuTichDiem.objects.filter(
        MaDonHang=don.ma_don_hang,
        LoaiGiaoDich="CONG",
    ).exists()

    if da_cong:
        return {
            "thanh_cong": False,
            "thong_bao": "Đơn hàng đã được cộng điểm trước đó."
        }

    so_diem = tinh_diem_don_hang(don)

    if so_diem <= 0:
        return {
            "thanh_cong": False,
            "thong_bao": "Đơn hàng chưa đủ điều kiện tích điểm."
        }

    diem_moi, hang_moi = cap_nhat_diem_va_hang(
        ho_so,
        so_diem,
    )

    ghi_lich_su_diem(
        ho_so=ho_so,
        don=don,
        loai_giao_dich="CONG",
        so_diem=so_diem,
        noi_dung=(
            f"Cộng {so_diem} điểm từ đơn hàng "
            f"{don.ma_don_hang}."
        ),
    )

    return {
        "thanh_cong": True,
        "so_diem": so_diem,
        "diem_moi": diem_moi,
        "hang_moi": hang_moi,
    }


# =====================================================
# 7. TÍNH SỐ ĐIỂM CẦN THU HỒI KHI HOÀN TIỀN
# =====================================================

def tinh_diem_thu_hoi(thanh_toan, don):
    """
    Thu hồi điểm theo tỷ lệ:

    Tiền hoàn / Giá trị hàng sau giảm giá.

    Nếu hoàn toàn bộ đơn hàng:
    Không thu hồi vượt quá tổng số điểm đã nhận.
    """

    lich_su_cong = LichSuTichDiem.objects.filter(
        MaDonHang=don.ma_don_hang,
        LoaiGiaoDich="CONG",
    )

    tong_diem_da_nhan = (
        lich_su_cong.aggregate(
            tong=Sum("SoDiem")
        )["tong"] or 0
    )

    if tong_diem_da_nhan <= 0:
        return 0

    tong_tien_hang = Decimal(
        str(don.tong_tien_hang or 0)
    )

    so_tien_giam = Decimal(
        str(don.so_tien_giam or 0)
    )

    gia_tri_duoc_tich_diem = max(
        tong_tien_hang - so_tien_giam,
        Decimal("0")
    )

    if gia_tri_duoc_tich_diem <= 0:
        return 0

    tien_hoan = Decimal(
        str(thanh_toan.SoTienThanhToan or 0)
    )

    if tien_hoan <= 0:
        return 0

    # Không thu hồi quá 100% số điểm ban đầu.
    ty_le_hoan = min(
        tien_hoan / gia_tri_duoc_tich_diem,
        Decimal("1")
    )

    diem_thu_hoi = (
        Decimal(str(tong_diem_da_nhan)) * ty_le_hoan
    ).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )

    return min(
        int(diem_thu_hoi),
        tong_diem_da_nhan,
    )


# =====================================================
# 8. TRỪ ĐIỂM KHI HOÀN TIỀN THÀNH CÔNG
# =====================================================

def tru_diem_sau_hoan_tien(thanh_toan, don, ho_so):
    """
    Chỉ trừ điểm khi giao dịch hoàn tiền đã hoàn tất.
    Không trừ trùng cho cùng một đơn hàng.
    """

    da_tru = LichSuTichDiem.objects.filter(
        MaDonHang=don.ma_don_hang,
        LoaiGiaoDich="TRU",
    ).exists()

    if da_tru:
        return {
            "thanh_cong": False,
            "thong_bao": "Đơn hàng đã được thu hồi điểm."
        }

    so_diem_thu_hoi = tinh_diem_thu_hoi(
        thanh_toan,
        don,
    )

    if so_diem_thu_hoi <= 0:
        return {
            "thanh_cong": False,
            "thong_bao": "Không có điểm cần thu hồi."
        }

    # Không để số dư điểm bị âm.
    so_diem_thuc_te = min(
        so_diem_thu_hoi,
        ho_so.DiemTichLuy or 0,
    )

    if so_diem_thuc_te <= 0:
        return {
            "thanh_cong": False,
            "thong_bao": "Khách hàng không còn điểm để thu hồi."
        }

    diem_moi, hang_moi = cap_nhat_diem_va_hang(
        ho_so,
        -so_diem_thuc_te,
    )

    ghi_lich_su_diem(
        ho_so=ho_so,
        don=don,
        loai_giao_dich="TRU",
        so_diem=so_diem_thuc_te,
        noi_dung=(
            f"Thu hồi {so_diem_thuc_te} điểm do hoàn tiền "
            f"đơn hàng {don.ma_don_hang}."
        ),
    )

    return {
        "thanh_cong": True,
        "so_diem_thu_hoi": so_diem_thuc_te,
        "diem_moi": diem_moi,
        "hang_moi": hang_moi,
    }


# =====================================================
# 9. SERVICE ĐIỀU PHỐI TOÀN BỘ NGHIỆP VỤ
# =====================================================

@transaction.atomic
def xu_ly_diem_theo_thanh_toan(thanh_toan):
    """
    Hàm trung tâm kết nối THANHTOAN với KHACHHANG
    và KHUYENMAI.

    DaThanhToan:
        Cộng điểm.

    DaHoanTien:
        Thu hồi điểm.

    Các trạng thái khác:
        Không xử lý.
    """

    giao_dich = ThanhToan.objects.select_for_update().get(
        pk=thanh_toan.pk
    )

    if not giao_dich.DonHang_id:
        return {
            "thanh_cong": False,
            "thong_bao": "Giao dịch không có đơn hàng."
        }

    if giao_dich.TrangThaiThanhToan not in (
        "DaThanhToan",
        "DaHoanTien",
    ):
        return {
            "thanh_cong": False,
            "thong_bao": "Giao dịch chưa đủ điều kiện."
        }

    if giao_dich.LoaiGiaoDich == "ThanhToan":
        if giao_dich.TrangThaiThanhToan != "DaThanhToan":
            return {
                "thanh_cong": False,
                "thong_bao": "Thanh toán chưa hoàn tất."
            }

    elif giao_dich.LoaiGiaoDich == "HoanTien":
        if giao_dich.TrangThaiThanhToan != "DaHoanTien":
            return {
                "thanh_cong": False,
                "thong_bao": "Hoàn tiền chưa hoàn tất."
            }

    else:
        return {
            "thanh_cong": False,
            "thong_bao": "Loại giao dịch không hợp lệ."
        }

    don = giao_dich.DonHang

    # Khóa hồ sơ để tránh hai giao dịch đồng thời
    # cập nhật điểm của cùng một khách hàng.
    ho_so = HoSoKhachHang.objects.select_for_update().filter(
        MaHoSo=don.ma_khach_hang
    ).first()

    if not ho_so:
        return {
            "thanh_cong": False,
            "thong_bao": "Không tìm thấy hồ sơ khách hàng."
        }

    if giao_dich.LoaiGiaoDich == "ThanhToan":

        ket_qua = cong_diem_sau_thanh_toan(
            giao_dich,
            don,
            ho_so,
        )

    else:

        ket_qua = tru_diem_sau_hoan_tien(
            giao_dich,
            don,
            ho_so,
        )

    # Đồng bộ voucher theo hạng hiện tại.
    # get_or_create trong service voucher giúp tránh cấp trùng.
    if ket_qua.get("thanh_cong"):
        from KHUYENMAI.services import cap_voucher_theo_hang

        cap_voucher_theo_hang(
            khach_hang=ho_so,
            hang_thanh_vien=ho_so.HangThanhVien,
        )

    return ket_qua