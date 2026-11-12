from decimal import Decimal, InvalidOperation
from django.utils import timezone

from .models import Voucher, ChiTietKhuyenMai, VoucherKhachHang
def chuan_hoa_hang_thanh_vien(hang_thanh_vien):
   """
   Chuẩn hóa hạng thành viên về mã lưu trong database.


   Chấp nhận cả tên hiển thị và mã hạng.
   """


   mapping_hang = {
       "Thành viên": "TatCaThanhVien",
       "TatCaThanhVien": "TatCaThanhVien",


       "Đồng": "Dong",
       "Dong": "Dong",


       "Bạc": "Bac",
       "Bac": "Bac",


       "Vàng": "Vang",
       "Vang": "Vang",


       "Kim cương": "KimCuong",
       "KimCuong": "KimCuong",
   }


   if not hang_thanh_vien:
       return None


   hang_thanh_vien = str(hang_thanh_vien).strip()


   return mapping_hang.get(hang_thanh_vien)


def kiem_tra_va_tinh_voucher(
   ma_voucher,
   tong_tien_hang,
   hang_thanh_vien=None,
   ma_khach_hang=None
):
   """
   Kiểm tra điều kiện voucher và tính số tiền được giảm.


   Hỗ trợ chuẩn hóa hạng thành viên trước khi so sánh.
   Giữ nguyên cấu trúc kết quả để không ảnh hưởng
   đến các chức năng checkout hiện tại.
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


   # Kiểm tra voucher đã sử dụng
   if ma_khach_hang:
       da_su_dung = VoucherKhachHang.objects.filter(
           MaVoucher=voucher,
           MaKhachHang_id=ma_khach_hang,
           TrangThai="DaSuDung"
       ).exists()


       if da_su_dung:
           ket_qua["thong_bao"] = (
               "Bạn đã sử dụng voucher này rồi."
           )
           return ket_qua


   # Kiểm tra trạng thái voucher
   if not voucher.TrangThai:
       ket_qua["thong_bao"] = (
           "Voucher hiện không còn hoạt động."
       )
       return ket_qua


   # Kiểm tra thời hạn voucher
   thoi_gian_hien_tai = timezone.now()


   if thoi_gian_hien_tai < voucher.NgayBatDau:
       ket_qua["thong_bao"] = (
           "Voucher chưa đến thời gian sử dụng."
       )
       return ket_qua


   if thoi_gian_hien_tai > voucher.NgayKetThuc:
       ket_qua["thong_bao"] = "Voucher đã hết hạn."
       return ket_qua


   # ==========================================
   # KIỂM TRA HẠNG THÀNH VIÊN
   # ==========================================


   if voucher.DoiTuongApDung != "TatCaThanhVien":


       hang_chuan_hoa = chuan_hoa_hang_thanh_vien(
           hang_thanh_vien
       )


       if hang_chuan_hoa != voucher.DoiTuongApDung:
           ket_qua["thong_bao"] = (
               "Voucher không áp dụng cho hạng thành viên của bạn."
           )
           return ket_qua


   # ==========================================
   # TÍNH GIÁ TRỊ GIẢM
   # ==========================================


   if voucher.LoaiGiamGia == "PhanTram":
       so_tien_giam = (
           tong_tien_hang
           * voucher.GiaTriGiam
           / Decimal("100")
       )


   else:
       so_tien_giam = voucher.GiaTriGiam


   # Không cho giảm vượt quá tổng tiền hàng
   so_tien_giam = min(
       so_tien_giam,
       tong_tien_hang
   )


   ket_qua["hop_le"] = True


   ket_qua["thong_bao"] = (
       "Áp dụng voucher thành công."
   )


   ket_qua["so_tien_giam"] = (
       so_tien_giam.quantize(Decimal("1"))
   )


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
def tra_lai_voucher_cho_don(don):
   """
   Trả lại lượt sử dụng voucher khi đơn hàng bị hủy
   theo trường hợp được phép.
   """
   if not don.ma_voucher or not don.ma_khach_hang:
       return


   VoucherKhachHang.objects.filter(
       MaVoucher_id=don.ma_voucher,
       MaKhachHang_id=don.ma_khach_hang,
       MaDonHang_id=don.pk,
       TrangThai="DaSuDung",
   ).update(
       MaDonHang=None,
       TrangThai="ChuaSuDung",
   )






# =====================================================
# CẤP VOUCHER TỰ ĐỘNG THEO HẠNG THÀNH VIÊN
# =====================================================


def cap_voucher_theo_hang(khach_hang, hang_thanh_vien):
   """
   Tự động cấp các voucher đang hoạt động
   phù hợp với hạng thành viên của khách hàng.


   Không cấp trùng voucher cho cùng khách hàng.
   """


   mapping_hang_voucher = {
       "Thành viên": "TatCaThanhVien",
       "Đồng": "Dong",
       "Bạc": "Bac",
       "Vàng": "Vang",
       "Kim cương": "KimCuong",
   }


   doi_tuong_ap_dung = mapping_hang_voucher.get(
       hang_thanh_vien
   )


   if not doi_tuong_ap_dung:
       return 0


   thoi_gian_hien_tai = timezone.now()


   danh_sach_voucher = Voucher.objects.filter(
       DoiTuongApDung=doi_tuong_ap_dung,
       TrangThai=True,
       NgayBatDau__lte=thoi_gian_hien_tai,
       NgayKetThuc__gte=thoi_gian_hien_tai,
   )


   so_voucher_moi = 0


   for voucher in danh_sach_voucher:


       voucher_khach_hang, da_tao = (
           VoucherKhachHang.objects.get_or_create(
               MaVoucher=voucher,
               MaKhachHang=khach_hang,
               defaults={
                   "TrangThai": "ChuaSuDung",
               },
           )
       )


       if da_tao:
           so_voucher_moi += 1


   return so_voucher_moi

