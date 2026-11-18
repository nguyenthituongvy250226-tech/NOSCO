

"""Các hàm nghiệp vụ dùng chung cho module đơn hàng."""

from SANPHAM.models import BienTheSanPham
import re
import unicodedata


from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4


from django.db import transaction
from django.dispatch import Signal
from django.utils import timezone


from .models import (
   DonHang,
   ChiTietDonHang,
   YeuCauTraHang,
   ChiTietYeuCauTraHang,
   BangChungYeuCauTraHang,
)


from THANHTOAN.models import ThanhToan










# =========================================================
# NGOẠI LỆ VÀ SIGNAL
# =========================================================


class DuLieuDonHangKhongHopLe(Exception):
   """Lỗi dữ liệu hoặc thao tác đơn hàng không hợp lệ."""




don_hang_trang_thai_thay_doi = Signal()




def _phat_tin_trang_thai(don, trang_thai_cu, trang_thai_moi):
   if trang_thai_cu != trang_thai_moi:
       don_hang_trang_thai_thay_doi.send(
           sender=DonHang,
           don_hang=don,
           trang_thai_cu=trang_thai_cu,
           trang_thai_moi=trang_thai_moi,
       )




# =========================================================
# HÀM HỖ TRỢ
# =========================================================

def _cap_nhat_ton_kho(danh_sach, *, cong=False):
    """
    Cập nhật tồn kho theo mã biến thể.
    cong=False: trừ kho.
    cong=True: cộng kho.
    """

    so_luong_theo_bien_the = {}

    for item in danh_sach:
        ma = str(item["ma_bien_the"])
        so_luong = int(item["so_luong"])

        so_luong_theo_bien_the[ma] = (
            so_luong_theo_bien_the.get(ma, 0) + so_luong
        )

    cac_bien_the = {
        str(bt.pk): bt
        for bt in BienTheSanPham.objects.select_for_update().filter(
            pk__in=so_luong_theo_bien_the.keys()
        )
    }

    # Kiểm tra biến thể có tồn tại.
    if len(cac_bien_the) != len(so_luong_theo_bien_the):
        raise DuLieuDonHangKhongHopLe(
            "Có sản phẩm không tồn tại trong kho."
        )

    # Kiểm tra đủ hàng trước khi trừ.
    if not cong:
        for ma, so_luong in so_luong_theo_bien_the.items():
            if cac_bien_the[ma].so_luong_ton < so_luong:
                raise DuLieuDonHangKhongHopLe(
                    f"Sản phẩm {ma} không đủ số lượng tồn kho."
                )

    # Cập nhật tồn kho.
    for ma, so_luong in so_luong_theo_bien_the.items():
        bien_the = cac_bien_the[ma]

        if cong:
            bien_the.so_luong_ton += so_luong
        else:
            bien_the.so_luong_ton -= so_luong

        bien_the.save(update_fields=["so_luong_ton"])


def _hoan_ton_kho_don_hang(don):
    """Hoàn kho khi đơn hàng bị hủy hoặc giao thất bại."""

    if not don.ton_kho_da_tru:
        return

    danh_sach = list(
        don.chi_tiet.values("ma_bien_the", "so_luong")
    )

    _cap_nhat_ton_kho(danh_sach, cong=True)

    don.ton_kho_da_tru = False
    don.save(update_fields=["ton_kho_da_tru"])
def _ma(prefix):
   """Sinh mã ngắn, không vượt quá 10 ký tự."""
   return f"{prefix}{uuid4().hex[:10 - len(prefix)]}".upper()




def _decimal(value, ten_truong="Giá trị"):
   try:
       if value in (None, ""):
           return Decimal("0")


       ket_qua = Decimal(str(value))


       if not ket_qua.is_finite():
           raise InvalidOperation


       return ket_qua


   except (InvalidOperation, TypeError, ValueError):
       raise DuLieuDonHangKhongHopLe(
           f"{ten_truong} không hợp lệ."
       )




def _so_nguyen_duong(value, ten_truong="Số lượng"):
   try:
       ket_qua = int(value)
   except (TypeError, ValueError):
       raise DuLieuDonHangKhongHopLe(
           f"{ten_truong} phải là số nguyên."
       )


   if str(value).strip() != str(ket_qua) and not isinstance(value, int):
       raise DuLieuDonHangKhongHopLe(
           f"{ten_truong} phải là số nguyên."
       )


   if ket_qua <= 0:
       raise DuLieuDonHangKhongHopLe(
           f"{ten_truong} phải lớn hơn 0."
       )


   return ket_qua




def _chuan_hoa_chuoi(value):
   value = str(value or "").strip().lower()
   value = unicodedata.normalize("NFD", value)


   value = "".join(
       ky_tu
       for ky_tu in value
       if unicodedata.category(ky_tu) != "Mn"
   )


   return value.replace("đ", "d")




# =========================================================
# PHÍ VẬN CHUYỂN
# =========================================================


PHI_VAN_CHUYEN_TIEU_CHUAN = Decimal("30000")
PHI_VAN_CHUYEN_DA_NANG = Decimal("0")




def dia_chi_duoc_mien_phi(dia_chi):
   dia_chi_chuan_hoa = _chuan_hoa_chuoi(dia_chi)


   return bool(
       re.search(r"\bda\s+nang\b", dia_chi_chuan_hoa)
   )




def tinh_phi_van_chuyen(dia_chi):
   if dia_chi_duoc_mien_phi(dia_chi):
       return PHI_VAN_CHUYEN_DA_NANG


   return PHI_VAN_CHUYEN_TIEU_CHUAN




# =========================================================
# KIỂM TRA THANH TOÁN
# =========================================================


def _kiem_tra_thanh_toan_don(don):
   """
   COD được chấp nhận.
   Các phương thức khác phải có giao dịch ThanhToan
   ở trạng thái DaThanhToan.
   """


   cac_giao_dich = ThanhToan.objects.filter(
       DonHang=don,
       LoaiGiaoDich="ThanhToan",
   )


   if not cac_giao_dich.exists():
       raise DuLieuDonHangKhongHopLe(
           "Đơn hàng chưa có thông tin thanh toán."
       )


   for giao_dich in cac_giao_dich:
       phuong_thuc = _chuan_hoa_chuoi(
           getattr(giao_dich, "PhuongThucThanhToan", "")
       )


       if phuong_thuc in ("cod", "thanh toan khi nhan hang"):
           return True


       trang_thai = getattr(
           giao_dich,
           "TrangThaiThanhToan",
           "",
       )


       if trang_thai == "DaThanhToan":
           return True


   raise DuLieuDonHangKhongHopLe(
       "Đơn hàng chưa được thanh toán thành công."
   )




# =========================================================
# TẠO ĐƠN HÀNG
# =========================================================


@transaction.atomic
def tao_don_hang(
   du_lieu=None,
   *,
   ma_khach_hang=None,
   ma_dia_chi=None,
   ten_nguoi_nhan=None,
   sdt_nguoi_nhan=None,
   dia_chi_nhan_hang=None,
   ghi_chu="",
   items=None,
   ma_voucher=None,
   so_tien_giam=0,
):
   """
   Hỗ trợ cả hai cách gọi:


   1. tao_don_hang({...})


   2. tao_don_hang(
       ma_khach_hang=...,
       ten_nguoi_nhan=...,
       ...
   )
   """


   if du_lieu is not None:
       if not isinstance(du_lieu, dict):
           raise DuLieuDonHangKhongHopLe(
               "Dữ liệu tạo đơn hàng không hợp lệ."
           )


       ma_khach_hang = du_lieu.get("ma_khach_hang")
       ma_dia_chi = du_lieu.get("ma_dia_chi")
       ten_nguoi_nhan = du_lieu.get("ten_nguoi_nhan")
       sdt_nguoi_nhan = du_lieu.get("sdt_nguoi_nhan")
       dia_chi_nhan_hang = du_lieu.get("dia_chi_nhan_hang")
       ghi_chu = du_lieu.get("ghi_chu", "")
       items = du_lieu.get("items")
       ma_voucher = du_lieu.get("ma_voucher")
       so_tien_giam = du_lieu.get("so_tien_giam", 0)


   if not ma_khach_hang:
       raise DuLieuDonHangKhongHopLe(
           "Không tìm thấy thông tin khách hàng."
       )


   if not items:
       raise DuLieuDonHangKhongHopLe(
           "Đơn hàng phải có ít nhất một sản phẩm."
       )


   ten_nguoi_nhan = str(ten_nguoi_nhan or "").strip()
   sdt_nguoi_nhan = str(sdt_nguoi_nhan or "").strip()
   dia_chi_nhan_hang = str(
       dia_chi_nhan_hang or ""
   ).strip()


   if not ten_nguoi_nhan:
       raise DuLieuDonHangKhongHopLe(
           "Vui lòng nhập tên người nhận."
       )


   if not sdt_nguoi_nhan:
       raise DuLieuDonHangKhongHopLe(
           "Vui lòng nhập số điện thoại người nhận."
       )


   if not dia_chi_nhan_hang:
       raise DuLieuDonHangKhongHopLe(
           "Vui lòng nhập địa chỉ nhận hàng."
       )


   tong_tien_hang = Decimal("0")
   danh_sach_san_pham = []


   for item in items:
       ma_bien_the = item.get("ma_bien_the")


       if not ma_bien_the:
           raise DuLieuDonHangKhongHopLe(
               "Thiếu mã biến thể sản phẩm."
           )


       so_luong = _so_nguyen_duong(
           item.get("so_luong"),
           "Số lượng sản phẩm",
       )


       don_gia = _decimal(
           item.get("don_gia"),
           "Đơn giá sản phẩm",
       )


       if don_gia < 0:
           raise DuLieuDonHangKhongHopLe(
               "Đơn giá không được âm."
           )


       thanh_tien = don_gia * so_luong
       tong_tien_hang += thanh_tien


       danh_sach_san_pham.append({
           "ma_bien_the": ma_bien_the,
           "so_luong": so_luong,
           "don_gia": don_gia,
           "thanh_tien": thanh_tien,
       })


   so_tien_giam = _decimal(
       so_tien_giam,
       "Số tiền giảm",
   )


   if so_tien_giam < 0:
       raise DuLieuDonHangKhongHopLe(
           "Số tiền giảm không được âm."
       )


   if so_tien_giam > tong_tien_hang:
       so_tien_giam = tong_tien_hang


   # Tự tính phí vận chuyển theo địa chỉ.
   phi_van_chuyen = tinh_phi_van_chuyen(
       dia_chi_nhan_hang
   )


   tong_tien = (
       tong_tien_hang
       - so_tien_giam
       + phi_van_chuyen
   )

   # Kiểm tra và trừ tồn kho khi đặt hàng.
   _cap_nhat_ton_kho(
       danh_sach_san_pham,
       cong=False,
   )
   don = DonHang.objects.create(
       ma_don_hang=_ma("DH"),
       ma_khach_hang=ma_khach_hang,
       ma_dia_chi=ma_dia_chi,
       ten_nguoi_nhan=ten_nguoi_nhan,
       sdt_nguoi_nhan=sdt_nguoi_nhan,
       dia_chi_nhan_hang=dia_chi_nhan_hang,
       ma_voucher=ma_voucher or None,
       ghi_chu=ghi_chu,
       ngay_dat=timezone.now(),
       phi_van_chuyen=phi_van_chuyen,
       tong_tien_hang=tong_tien_hang,
       so_tien_giam=so_tien_giam,
       tong_tien=max(tong_tien, Decimal("0")),
       trang_thai_don="cho_xac_nhan",
       ton_kho_da_tru=True,
   )


   for item in danh_sach_san_pham:
       ChiTietDonHang.objects.create(
           ma_chi_tiet_dh=_ma("CT"),
           ma_don_hang=don,
           ma_bien_the=item["ma_bien_the"],
           so_luong=item["so_luong"],
           don_gia=item["don_gia"],
           thanh_tien=item["thanh_tien"],

       )

       # Phát tín hiệu khi đơn hàng được tạo thành công.
   from .signals import don_hang_da_tao

   don_hang_da_tao.send(
       sender=DonHang,
       don_hang=don,
   )
   return don




# =========================================================
# SUPERUSER XỬ LÝ ĐƠN HÀNG
# =========================================================


@transaction.atomic
def xu_ly_don_hang(don, *, hanh_dong):
   don = DonHang.objects.select_for_update().get(
       pk=don.pk
   )


   trang_thai_cu = don.trang_thai_don


   if hanh_dong == "xac_nhan":
       if trang_thai_cu != "cho_xac_nhan":
           raise DuLieuDonHangKhongHopLe(
               "Chỉ được xác nhận đơn đang Chờ xác nhận."
           )


       _kiem_tra_thanh_toan_don(don)
       don.trang_thai_don = "cho_lay_hang"


   elif hanh_dong == "het_hang":
       if trang_thai_cu != "cho_xac_nhan":
           raise DuLieuDonHangKhongHopLe(
               "Chỉ được hủy đơn đang Chờ xác nhận theo thao tác này."
           )

       _hoan_ton_kho_don_hang(don)
       don.trang_thai_don = "da_huy"
       from KHUYENMAI.services import tra_lai_voucher_cho_don
       tra_lai_voucher_cho_don(don)


   else:
       raise DuLieuDonHangKhongHopLe(
           "Thao tác xử lý đơn hàng không hợp lệ."
       )


   don.save()


   _phat_tin_trang_thai(
       don,
       trang_thai_cu,
       don.trang_thai_don,
   )


   return don




# =========================================================
# SUPERUSER CẬP NHẬT VẬN CHUYỂN
# =========================================================


@transaction.atomic
def cap_nhat_giao_hang(
   don,
   *,
   trang_thai,
   don_vi_van_chuyen=None,
   ma_van_don=None,
   ly_do_that_bai=None,
):
   don = DonHang.objects.select_for_update().get(
       pk=don.pk
   )


   trang_thai_cu = don.trang_thai_don


   if don_vi_van_chuyen:
       don.don_vi_van_chuyen = don_vi_van_chuyen


   if ma_van_don:
       don.ma_van_don = ma_van_don


   if trang_thai == "cho_giao_hang":
       if trang_thai_cu != "cho_lay_hang":
           raise DuLieuDonHangKhongHopLe(
               "Chỉ được chuyển đơn Chờ lấy hàng sang Chờ giao hàng."
           )


       don.trang_thai_don = "cho_giao_hang"


   elif trang_thai == "da_giao":
       if trang_thai_cu != "cho_giao_hang":
           raise DuLieuDonHangKhongHopLe(
               "Chỉ được xác nhận giao thành công cho đơn Chờ giao hàng."
           )


       don.trang_thai_don = "da_giao"
       don.ngay_giao_thanh_cong = timezone.now()


       # =====================================================
       # GHI NHẬN COD ĐÃ THANH TOÁN
       # VÀ TỰ ĐỘNG CỘNG ĐIỂM KHÁCH HÀNG
       # =====================================================


       giao_dich_cod = ThanhToan.objects.filter(
           DonHang=don,
           PhuongThucThanhToan="COD",
           LoaiGiaoDich="ThanhToan",
           TrangThaiThanhToan="ChoThanhToan",
       )


       # Lưu mã giao dịch trước khi cập nhật trạng thái.
       danh_sach_ma_thanh_toan = list(
           giao_dich_cod.values_list(
               "MaThanhToan",
               flat=True,
           )
       )


       # Giữ nguyên cách cập nhật trạng thái COD hiện tại.
       giao_dich_cod.update(
           TrangThaiThanhToan="DaThanhToan",
           NgayThanhToan=timezone.now(),
       )


       # Xử lý điểm cho từng giao dịch vừa được xác nhận.
       from KHACHHANG.loyalty_services import (
           xu_ly_diem_theo_thanh_toan
       )


       for ma_thanh_toan in danh_sach_ma_thanh_toan:
           thanh_toan_cod = ThanhToan.objects.select_for_update().get(
               pk=ma_thanh_toan,
           )


           xu_ly_diem_theo_thanh_toan(thanh_toan_cod)
   elif trang_thai == "giao_that_bai":
       if trang_thai_cu != "cho_giao_hang":
           raise DuLieuDonHangKhongHopLe(
               "Chỉ được xác nhận giao thất bại cho đơn Chờ giao hàng."
           )

       _hoan_ton_kho_don_hang(don)
       don.trang_thai_don = "da_huy"
       from KHUYENMAI.services import tra_lai_voucher_cho_don
       tra_lai_voucher_cho_don(don)


       if hasattr(don, "ly_do_that_bai"):
           don.ly_do_that_bai = (
               str(ly_do_that_bai or "").strip()
               or "Giao hàng không thành công."
           )


   else:
       raise DuLieuDonHangKhongHopLe(
           "Trạng thái cập nhật vận chuyển không hợp lệ."
       )


   if hasattr(don, "cap_nhat_van_chuyen_luc"):
       don.cap_nhat_van_chuyen_luc = timezone.now()


   don.save()


   _phat_tin_trang_thai(
       don,
       trang_thai_cu,
       don.trang_thai_don,
   )


   return don




# =========================================================
# KHÁCH HÀNG HỦY ĐƠN
# =========================================================


@transaction.atomic
def khach_huy_don_hang(don):
   don = DonHang.objects.select_for_update().get(
       pk=don.pk
   )


   if don.trang_thai_don != "cho_xac_nhan":
       raise DuLieuDonHangKhongHopLe(
           "Bạn chỉ được hủy đơn hàng khi đơn đang Chờ xác nhận."
       )


   trang_thai_cu = don.trang_thai_don
   _hoan_ton_kho_don_hang(don)
   don.trang_thai_don = "da_huy"


   from KHUYENMAI.services import tra_lai_voucher_cho_don
   tra_lai_voucher_cho_don(don)


   don.save(update_fields=["trang_thai_don"])


   _phat_tin_trang_thai(
       don,
       trang_thai_cu,
       don.trang_thai_don,
   )


   return don




# =========================================================
# KHÁCH HÀNG CẬP NHẬT THÔNG TIN NHẬN HÀNG
# =========================================================


@transaction.atomic
def cap_nhat_thong_tin_nhan(
   don,
   *,
   ten_nguoi_nhan,
   sdt_nguoi_nhan,
   dia_chi_nhan_hang,
   ma_dia_chi=None,
   ghi_chu=None,
):
   don = DonHang.objects.select_for_update().get(
       pk=don.pk
   )


   if don.trang_thai_don != "cho_xac_nhan":
       raise DuLieuDonHangKhongHopLe(
           "Chỉ được sửa thông tin nhận hàng khi đơn đang Chờ xác nhận."
       )


   ten_nguoi_nhan = str(ten_nguoi_nhan or "").strip()
   sdt_nguoi_nhan = str(sdt_nguoi_nhan or "").strip()
   dia_chi_nhan_hang = str(
       dia_chi_nhan_hang or ""
   ).strip()


   if not ten_nguoi_nhan:
       raise DuLieuDonHangKhongHopLe(
           "Tên người nhận không được để trống."
       )


   if not sdt_nguoi_nhan:
       raise DuLieuDonHangKhongHopLe(
           "Số điện thoại không được để trống."
       )


   if not dia_chi_nhan_hang:
       raise DuLieuDonHangKhongHopLe(
           "Địa chỉ nhận hàng không được để trống."
       )


   don.ten_nguoi_nhan = ten_nguoi_nhan
   don.sdt_nguoi_nhan = sdt_nguoi_nhan
   don.dia_chi_nhan_hang = dia_chi_nhan_hang


   if ma_dia_chi is not None:
       don.ma_dia_chi = ma_dia_chi


   if ghi_chu is not None:
       don.ghi_chu = ghi_chu


   don.phi_van_chuyen = tinh_phi_van_chuyen(
       dia_chi_nhan_hang
   )


   don.tong_tien = max(
       _decimal(don.tong_tien_hang)
       - _decimal(don.so_tien_giam)
       + don.phi_van_chuyen,
       Decimal("0"),
   )


   don.save()


   return don




# =========================================================
# KHÁCH HÀNG XÁC NHẬN ĐÃ NHẬN HÀNG
# =========================================================


@transaction.atomic
def khach_xac_nhan_da_nhan(don):
   don = DonHang.objects.select_for_update().get(
       pk=don.pk
   )


   if don.trang_thai_don != "da_giao":
       raise DuLieuDonHangKhongHopLe(
           "Chỉ được xác nhận nhận hàng khi đơn đã giao."
       )


   if don.khach_da_xac_nhan_nhan:
       raise DuLieuDonHangKhongHopLe(
           "Bạn đã xác nhận nhận đơn hàng này rồi."
       )


   don.khach_da_xac_nhan_nhan = True
   don.save(update_fields=["khach_da_xac_nhan_nhan"])


   return don




# =========================================================
# KHÁCH HÀNG TẠO YÊU CẦU TRẢ HÀNG
# =========================================================


@transaction.atomic
def tao_yeu_cau_tra_hang(
   don,
   *,
   ly_do_tra,
   mo_ta_van_de,
   san_pham,
   ma_van_don_khach="",
   ngan_hang_hoan_tien=None,
   ten_chu_tai_khoan=None,
   so_tai_khoan=None,
   tep_minh_chung=None,
):
   don = DonHang.objects.select_for_update().get(
       pk=don.pk
   )


   if don.trang_thai_don != "da_giao":
       raise DuLieuDonHangKhongHopLe(
           "Chỉ được yêu cầu trả hàng khi đơn đã giao."
       )


   if don.khach_da_xac_nhan_nhan:
       raise DuLieuDonHangKhongHopLe(
           "Bạn đã xác nhận nhận hàng nên không thể tạo yêu cầu trả hàng."
       )


   if YeuCauTraHang.objects.filter(
       ma_don_hang=don
   ).exists():
       raise DuLieuDonHangKhongHopLe(
           "Đơn hàng này đã có yêu cầu trả hàng."
       )


   ly_do_tra = str(ly_do_tra or "").strip()
   mo_ta_van_de = str(mo_ta_van_de or "").strip()


   if not ly_do_tra:
       raise DuLieuDonHangKhongHopLe(
           "Vui lòng chọn lý do trả hàng."
       )


   if not mo_ta_van_de:
       raise DuLieuDonHangKhongHopLe(
           "Vui lòng mô tả vấn đề của sản phẩm."
       )


   # Kiểm tra danh sách sản phẩm và số lượng khách muốn trả.
   if not san_pham:
       raise DuLieuDonHangKhongHopLe(
           "Vui lòng chọn sản phẩm cần trả."
       )


   if not isinstance(san_pham, dict):
       raise DuLieuDonHangKhongHopLe(
           "Danh sách sản phẩm trả không hợp lệ."
       )


   # Lấy các chi tiết sản phẩm thuộc đơn hàng.
   cac_chi_tiet = {
       str(chi_tiet.pk): chi_tiet
       for chi_tiet in don.chi_tiet.all()
   }


   chi_tiet_tra = []


   for item_id, so_luong_raw in san_pham.items():
       item_id = str(item_id)


       # Kiểm tra sản phẩm có thuộc đơn hàng không.
       chi_tiet = cac_chi_tiet.get(item_id)


       if chi_tiet is None:
           raise DuLieuDonHangKhongHopLe(
               "Có sản phẩm không thuộc đơn hàng này."
           )


       # Kiểm tra số lượng khách muốn trả.
       so_luong = _so_nguyen_duong(
           so_luong_raw,
           "Số lượng sản phẩm trả",
       )


       if so_luong > chi_tiet.so_luong:
           raise DuLieuDonHangKhongHopLe(
               "Số lượng trả không được vượt quá số lượng đã mua."
           )


       chi_tiet_tra.append((chi_tiet, so_luong))


   # Kiểm tra tệp minh chứng.
   tep_minh_chung = list(tep_minh_chung or [])


   if len(tep_minh_chung) > 5:
       raise DuLieuDonHangKhongHopLe(
           "Bạn chỉ được tải lên tối đa 5 tệp minh chứng."
       )


   for tep in tep_minh_chung:
       if tep.size > 10 * 1024 * 1024:
           raise DuLieuDonHangKhongHopLe(
               "Mỗi tệp minh chứng không được vượt quá 10 MB."
           )
   # Tìm giao dịch thanh toán gốc đã thành công.
   giao_dich_thanh_cong = ThanhToan.objects.filter(
       DonHang=don,
       LoaiGiaoDich="ThanhToan",
       TrangThaiThanhToan="DaThanhToan",
   ).first()


   if not giao_dich_thanh_cong:
       raise DuLieuDonHangKhongHopLe(
           "Không tìm thấy giao dịch thanh toán thành công của đơn hàng."
       )
   # Tạo yêu cầu trả hàng.
   yeu_cau = YeuCauTraHang.objects.create(
       ma_yeu_cau_tra=_ma("RT"),
       ma_don_hang=don,
       ma_thanh_toan=giao_dich_thanh_cong.MaThanhToan,
       ly_do_tra=ly_do_tra,
       mo_ta_van_de=mo_ta_van_de,
       ma_van_don_khach=ma_van_don_khach or "",
       phuong_thuc_hoan_tien=(
           "tai_khoan_thanh_toan"
           if giao_dich_thanh_cong.PhuongThucThanhToan == "COD"
           else "tai_khoan_thanh_toan"
       ),
       ngan_hang_hoan_tien=ngan_hang_hoan_tien,
       ten_chu_tai_khoan=ten_chu_tai_khoan,
       so_tai_khoan=so_tai_khoan,
       trang_thai_tra="cho_xu_ly",
   )


   # Lưu đúng số lượng từng sản phẩm khách chọn trả.
   for chi_tiet, so_luong in chi_tiet_tra:
       ChiTietYeuCauTraHang.objects.create(
           yeu_cau=yeu_cau,
           chi_tiet_don_hang=chi_tiet,
           so_luong=so_luong,
       )


   # Lưu tệp minh chứng.
   for tep in tep_minh_chung:
       ten_tep = Path(tep.name).name
       phan_mo_rong = Path(ten_tep).suffix.lower()


       BangChungYeuCauTraHang.objects.create(
           yeu_cau=yeu_cau,
           tep=tep,
           ten_tep=ten_tep,
           loai_tep=phan_mo_rong,
       )


   # Chuyển trạng thái đơn hàng sang Trả hàng.
   trang_thai_cu = don.trang_thai_don
   don.trang_thai_don = "tra_hang"
   don.save(update_fields=["trang_thai_don"])


   _phat_tin_trang_thai(
       don,
       trang_thai_cu,
       don.trang_thai_don,
   )


   return yeu_cau


# =========================================================
# KHÁCH HÀNG HỦY YÊU CẦU TRẢ HÀNG
# =========================================================

@transaction.atomic
def huy_yeu_cau_tra_hang(don):
    don = DonHang.objects.select_for_update().get(pk=don.pk)

    # Lấy yêu cầu trả hàng của đơn
    yeu_cau = YeuCauTraHang.objects.select_for_update().filter(
        ma_don_hang=don
    ).first()

    if not yeu_cau:
        raise DuLieuDonHangKhongHopLe(
            "Không tìm thấy yêu cầu trả hàng."
        )

    # Chỉ được hủy khi yêu cầu đang chờ xử lý
    if yeu_cau.trang_thai_tra != "cho_xu_ly":
        raise DuLieuDonHangKhongHopLe(
            "Chỉ được hủy yêu cầu trả hàng đang chờ xử lý."
        )

    # Cho phép cả đơn đã giao và đơn trả hàng
    if don.trang_thai_don not in ["da_giao", "tra_hang"]:
        raise DuLieuDonHangKhongHopLe(
            "Trạng thái đơn hàng không cho phép hủy yêu cầu trả hàng."
        )

    # Đánh dấu yêu cầu đã hủy, không xóa dữ liệu
    yeu_cau.trang_thai_tra = "da_huy"
    yeu_cau.ket_qua_xl = "Khách hàng đã hủy yêu cầu trả hàng."
    yeu_cau.ngay_xu_ly = timezone.now()
    yeu_cau.save(update_fields=[
        "trang_thai_tra",
        "ket_qua_xl",
        "ngay_xu_ly",
    ])

    # Đưa đơn hàng về trạng thái Đã giao
    trang_thai_cu = don.trang_thai_don
    don.trang_thai_don = "da_giao"
    don.save(update_fields=["trang_thai_don"])

    _phat_tin_trang_thai(
        don,
        trang_thai_cu,
        don.trang_thai_don,
    )

    return yeu_cau

# =========================================================
# SUPERUSER XỬ LÝ YÊU CẦU TRẢ HÀNG
# =========================================================




@transaction.atomic
def xu_ly_yeu_cau_tra_hang(
   yeu_cau,
   *,
   hanh_dong,
   ket_qua="",
   don_vi_van_chuyen_tra=None,
   ma_van_don_tra=None,
   nguoi_thuc_hien=None,
   ip_thuc_hien=None,
):
   yeu_cau = YeuCauTraHang.objects.select_for_update().get(
       pk=yeu_cau.pk
   )


   don = DonHang.objects.select_for_update().get(
       pk=yeu_cau.ma_don_hang_id
   )


   if hanh_dong == "da_duyet":
       if yeu_cau.trang_thai_tra != "cho_xu_ly":
           raise DuLieuDonHangKhongHopLe(
               "Chỉ được duyệt yêu cầu đang chờ xử lý."
           )


       if not don_vi_van_chuyen_tra:
           raise DuLieuDonHangKhongHopLe(
               "Vui lòng nhập đơn vị vận chuyển trả hàng."
           )


       yeu_cau.trang_thai_tra = "da_duyet"
       yeu_cau.don_vi_van_chuyen_tra = don_vi_van_chuyen_tra
       yeu_cau.ma_van_don_tra = ma_van_don_tra or ""


   elif hanh_dong == "tu_choi":
       if yeu_cau.trang_thai_tra != "cho_xu_ly":
           raise DuLieuDonHangKhongHopLe(
               "Chỉ được từ chối yêu cầu đang chờ xử lý."
           )


       yeu_cau.trang_thai_tra = "tu_choi"


       # Đơn được trả lại trạng thái đã giao.
       don.trang_thai_don = "da_giao"
       don.save(update_fields=["trang_thai_don"])


       _phat_tin_trang_thai(
           don,
           "tra_hang",
           "da_giao",
       )




   elif hanh_dong == "cho_hoan_tien":


       if yeu_cau.trang_thai_tra != "da_duyet":
           raise DuLieuDonHangKhongHopLe(


               "Chỉ được xác nhận nhận hàng trả đối với yêu cầu đã duyệt."


           )


       # Lấy đúng giao dịch thanh toán gốc.


       giao_dich_goc = ThanhToan.objects.select_for_update().filter(


           pk=yeu_cau.ma_thanh_toan,


           DonHang=don,


           LoaiGiaoDich="ThanhToan",


           TrangThaiThanhToan="DaThanhToan",


       ).first()


       if not giao_dich_goc:
           raise DuLieuDonHangKhongHopLe(


               "Không tìm thấy giao dịch thanh toán thành công."


           )


       # Không cho phép tạo giao dịch hoàn tiền trùng.


       if ThanhToan.objects.filter(


               DonHang=don,


               LoaiGiaoDich="HoanTien",


       ).exists():
           raise DuLieuDonHangKhongHopLe(


               "Đơn hàng này đã có giao dịch hoàn tiền."


           )


       # Lấy danh sách sản phẩm khách được duyệt trả.


       chi_tiet_tra = list(


           yeu_cau.san_pham_tra.select_related(


               "chi_tiet_don_hang"


           ).all()


       )


       if not chi_tiet_tra:
           raise DuLieuDonHangKhongHopLe(


               "Không tìm thấy sản phẩm trong yêu cầu trả hàng."


           )


       # Tính giá trị sản phẩm khách trả.


       gia_tri_hang_tra = sum(


           (


               Decimal(str(item.so_luong))


               * Decimal(str(item.chi_tiet_don_hang.don_gia))


               for item in chi_tiet_tra


           ),


           Decimal("0"),


       )


       tong_tien_hang = Decimal(str(don.tong_tien_hang or 0))


       so_tien_giam = Decimal(str(don.so_tien_giam or 0))


       if tong_tien_hang <= 0 or gia_tri_hang_tra <= 0:
           raise DuLieuDonHangKhongHopLe(


               "Giá trị sản phẩm trả không hợp lệ."


           )


       if gia_tri_hang_tra > tong_tien_hang:
           raise DuLieuDonHangKhongHopLe(


               "Giá trị sản phẩm trả vượt quá giá trị hàng của đơn."


           )


       # Xác định khách trả toàn bộ hay chỉ trả một phần.


       tat_ca_chi_tiet = list(don.chi_tiet.all())


       so_luong_tra_theo_chi_tiet = {


           item.chi_tiet_don_hang_id: item.so_luong


           for item in chi_tiet_tra


       }


       tra_toan_bo = bool(tat_ca_chi_tiet) and all(


           so_luong_tra_theo_chi_tiet.get(item.pk, 0)


           == item.so_luong


           for item in tat_ca_chi_tiet


       )


       if tra_toan_bo:


           so_tien_hoan = Decimal(str(don.tong_tien or 0))


       else:


           so_tien_hoan = (


                   gia_tri_hang_tra


                   - gia_tri_hang_tra * so_tien_giam / tong_tien_hang


           ).quantize(


               Decimal("1"),


               rounding=ROUND_HALF_UP,


           )


       if so_tien_hoan <= 0:
           raise DuLieuDonHangKhongHopLe(


               "Số tiền hoàn không hợp lệ."


           )


       # COD và VNPay đều hoàn tiền bằng chuyển khoản thủ công.
       if giao_dich_goc.PhuongThucThanhToan in ["COD", "VNPAY"]:
           if not all([
               yeu_cau.ngan_hang_hoan_tien,
               yeu_cau.ten_chu_tai_khoan,
               yeu_cau.so_tai_khoan,
           ]):
               raise DuLieuDonHangKhongHopLe(
                   "Vui lòng bổ sung đầy đủ thông tin tài khoản nhận tiền."
               )


       # Tạo giao dịch hoàn tiền ở trạng thái chờ xử lý.


       ThanhToan.objects.create(


           MaThanhToan=f"TT{uuid4().hex[:8].upper()}",


           DonHang=don,


           PhuongThucThanhToan=giao_dich_goc.PhuongThucThanhToan,


           SoTienThanhToan=so_tien_hoan,


           TrangThaiThanhToan="ChoHoanTien",


           LoaiGiaoDich="HoanTien",


           MaGiaoDich=None,


       )


       # Đã nhận và kiểm tra hàng trả, đang chờ hoàn tiền.


       yeu_cau.trang_thai_tra = "cho_hoan_tien"




   elif hanh_dong == "xac_nhan_hoan_tien":


       if yeu_cau.trang_thai_tra != "cho_hoan_tien":
           raise DuLieuDonHangKhongHopLe(


               "Yêu cầu trả hàng chưa ở trạng thái chờ hoàn tiền."


           )


       # Lấy giao dịch hoàn tiền đang chờ xử lý.


       giao_dich_hoan = ThanhToan.objects.select_for_update().filter(


           DonHang=don,


           LoaiGiaoDich="HoanTien",


           TrangThaiThanhToan="ChoHoanTien",


       ).first()


       if not giao_dich_hoan:
           raise DuLieuDonHangKhongHopLe(


               "Không tìm thấy giao dịch hoàn tiền đang chờ xử lý."


           )


       # Chỉ xác nhận hoàn tất sau khi tiền đã được chuyển thành công.


       giao_dich_hoan.TrangThaiThanhToan = "DaHoanTien"


       giao_dich_hoan.NgayThanhToan = timezone.now()


       giao_dich_hoan.save(


           update_fields=[


               "TrangThaiThanhToan",


               "NgayThanhToan",


           ]


       )


       # =====================================================
       # TỰ ĐỘNG THU HỒI ĐIỂM KHI HOÀN TIỀN THÀNH CÔNG
       # =====================================================


       from KHACHHANG.loyalty_services import (
           xu_ly_diem_theo_thanh_toan
       )


       xu_ly_diem_theo_thanh_toan(giao_dich_hoan)
       # Cộng lại tồn kho của các sản phẩm khách đã trả.
       chi_tiet_tra = list(
           yeu_cau.san_pham_tra.select_related(
               "chi_tiet_don_hang"
           ).all()
       )

       danh_sach_hoan_kho = [
           {
               "ma_bien_the": item.chi_tiet_don_hang.ma_bien_the,
               "so_luong": item.so_luong,
           }
           for item in chi_tiet_tra
       ]

       _cap_nhat_ton_kho(
           danh_sach_hoan_kho,
           cong=True,
       )

       yeu_cau.trang_thai_tra = "hoan_tat"


   else:
       raise DuLieuDonHangKhongHopLe(
           "Thao tác xử lý yêu cầu trả hàng không hợp lệ."
       )


   yeu_cau.ket_qua_xl = ket_qua
   yeu_cau.ngay_xu_ly = timezone.now()
   yeu_cau.save()


   return yeu_cau


# =========================================================
# TỰ ĐỘNG HỦY ĐƠN CHƯA THANH TOÁN QUÁ 24 GIỜ
# =========================================================


@transaction.atomic
def het_han_don_chua_thanh_toan(ma_don_hang=None):
   moc_thoi_gian = timezone.now() - timedelta(hours=24)


   cac_don = DonHang.objects.select_for_update().filter(
       trang_thai_don="cho_xac_nhan",
       ngay_dat__lte=moc_thoi_gian,
   )


   # Nếu truyền mã đơn, chỉ kiểm tra đơn đó.
   # Nếu không truyền, xử lý tất cả đơn quá hạn như trước.
   if ma_don_hang:
       cac_don = cac_don.filter(pk=ma_don_hang)


   so_don_da_huy = 0
   for don in cac_don:
       try:
           cac_giao_dich = ThanhToan.objects.filter(
               DonHang=don,
               LoaiGiaoDich="ThanhToan",
           )


           if not cac_giao_dich.exists():
               continue


           # Không tự hủy COD.
           la_cod = any(
               _chuan_hoa_chuoi(
                   getattr(giao_dich, "PhuongThucThanhToan", "")
               ) in ("cod", "thanh toan khi nhan hang")
               for giao_dich in cac_giao_dich
           )


           if la_cod:
               continue


           da_thanh_toan = cac_giao_dich.filter(
               TrangThaiThanhToan="DaThanhToan"
           ).exists()


           if da_thanh_toan:
               continue


           trang_thai_cu = don.trang_thai_don
           _hoan_ton_kho_don_hang(don)
           don.trang_thai_don = "da_huy"
           don.save(update_fields=["trang_thai_don"])


           _phat_tin_trang_thai(
               don,
               trang_thai_cu,
               don.trang_thai_don,
           )


           so_don_da_huy += 1


       except Exception:
           # Không để một đơn lỗi làm dừng xử lý các đơn còn lại.
           continue


   return so_don_da_huy




# =========================================================
# HÀM TƯƠNG THÍCH VỚI CODE CŨ
# =========================================================


def chot_don_cho_xac_nhan_qua_han():
   """
   Giữ tên hàm cũ để các view đang gọi không bị lỗi.
   Không tự động hoàn tất đơn hàng.
   """
   return het_han_don_chua_thanh_toan()



