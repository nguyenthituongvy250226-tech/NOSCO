

import uuid
import secrets

from KHUYENMAI.services import tinh_gia_khuyen_mai
from decimal import Decimal


from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from KHACHHANG.views import khach_hang_required
from .models import GioHang, ChiTietGioHang, ChiaSeGioHang
from SANPHAM.models import BienTheSanPham




SO_BIEN_THE_TOI_DA = 10


# Mã khách hàng cố định để demo






def tao_ma(model):
   """
   Tạo mã ngẫu nhiên gồm 10 ký tự,
   kiểm tra để tránh trùng khóa chính.
   """
   while True:
       ma = uuid.uuid4().hex[:10].upper()


       if not model.objects.filter(pk=ma).exists():
           return ma




# ==========================================
# LẤY GIỎ HÀNG DEMO
# ==========================================


def lay_gio_hang(request):
   """
   Lấy giỏ hàng theo mã hồ sơ của khách hàng đang đăng nhập.
   Nếu chưa có thì tạo giỏ hàng mới.
   """
   ma_khach_hang = request.session.get("ma_khach_hang")


   if not ma_khach_hang:
       raise ValueError("Không tìm thấy mã khách hàng trong session.")


   gio_hang = GioHang.objects.filter(
       ma_khach_hang=ma_khach_hang,
       loai_gio_hang=False,
   ).first()


   if gio_hang is None:
       gio_hang = GioHang.objects.create(
           ma_gio_hang=tao_ma(GioHang),
           ma_khach_hang=ma_khach_hang,
           loai_gio_hang=False,
       )


   return gio_hang




# ==========================================
# LẤY CHI TIẾT GIỎ HÀNG
# ==========================================


def lay_chi_tiet_gio_hang(request, id):
   gio_hang = lay_gio_hang(request)


   return get_object_or_404(
       ChiTietGioHang,
       ma_chi_tiet_gio_hang=id,
       gio_hang=gio_hang,
   )




# ==========================================
# BỔ SUNG THÔNG TIN SẢN PHẨM ĐỂ HIỂN THỊ
# ==========================================


def bo_sung_thong_tin_san_pham(danh_sach):
   """
   Lấy thông tin biến thể và sản phẩm trực tiếp từ SANPHAM.
   """
   ma_bien_the_list = [
       item.ma_bien_the_sp for item in danh_sach
   ]


   bien_the_dict = {
       bt.ma_bien_the: bt
       for bt in BienTheSanPham.objects
       .filter(ma_bien_the__in=ma_bien_the_list)
       .select_related("san_pham")
       .prefetch_related("hinh_anh")
   }


   for item in danh_sach:
       bien_the = bien_the_dict.get(item.ma_bien_the_sp)


       if bien_the:
           san_pham = bien_the.san_pham


           item.ten_san_pham = san_pham.ten_san_pham
           item.mau_sac = bien_the.mau_sac
           item.kich_thuoc = bien_the.kich_thuoc
           item.don_gia = tinh_gia_khuyen_mai(
               san_pham.ma_san_pham,
               bien_the.gia_ban
           )
           item.so_luong_ton = bien_the.so_luong_ton


           # Lấy ảnh đại diện của biến thể.
           anh = bien_the.hinh_anh.filter(
               anh_dai_dien=True
           ).first()


           if anh is None:
               anh = bien_the.hinh_anh.order_by(
                   "thu_tu_hien_thi"
               ).first()


           item.hinh_anh = (
               anh.duong_dan_anh.url
               if anh and anh.duong_dan_anh
               else ""
           )


           item.thanh_tien = (
               item.so_luong * item.don_gia
           )


       else:
           item.ten_san_pham = "Sản phẩm không còn tồn tại"
           item.mau_sac = ""
           item.kich_thuoc = ""
           item.don_gia = Decimal("0")
           item.hinh_anh = ""
           item.so_luong_ton = 0
           item.thanh_tien = Decimal("0")


   return danh_sach




# ==========================================
# XEM GIỎ HÀNG
# ==========================================
@khach_hang_required
def xem_gio_hang(request):
   gio_hang = lay_gio_hang(request)


   danh_sach = list(
       gio_hang.chi_tiet.all().order_by(
           "ma_chi_tiet_gio_hang"
       )
   )


   danh_sach = bo_sung_thong_tin_san_pham(danh_sach)


   # Tổng số lượng sản phẩm trong giỏ
   tong_so_luong = sum(
       item.so_luong for item in danh_sach
   )


   # Số lượng của các sản phẩm được chọn
   so_luong_chon = sum(
       item.so_luong
       for item in danh_sach
       if item.trang_thai_chon
   )


   # Tổng tiền các sản phẩm được chọn
   tam_tinh = sum(
       (
           item.thanh_tien
           for item in danh_sach
           if item.trang_thai_chon
       ),
       Decimal("0"),
   )


   context = {
       "gio_hang": gio_hang,
       "danh_sach": danh_sach,
       "tam_tinh": tam_tinh,
       "tong_so_luong": tong_so_luong,
       "so_luong_chon": so_luong_chon,
       "tat_ca_duoc_chon": bool(danh_sach) and all(
           item.trang_thai_chon for item in danh_sach
       ),
   }


   return render(
       request,
       "GIOHANG/gio_hang.html",
       context
   )




# ==========================================
# THÊM SẢN PHẨM VÀO GIỎ HÀNG
# ==========================================


@khach_hang_required
@require_POST
def them_vao_gio(request):
   is_ajax = (
       request.headers.get("x-requested-with") == "XMLHttpRequest"
   )


   def tra_ve(thanh_cong, thong_bao, status=200, gio_hang=None):
       if is_ajax:
           so_san_pham = (
               gio_hang.chi_tiet.count() if gio_hang else 0
           )
           return JsonResponse({
               "success": thanh_cong,
               "message": thong_bao,
               "cart_count": so_san_pham,
               "limit_reached": (
   not thanh_cong
   and "tối đa" in thong_bao.lower()
),
           }, status=status)


       if thanh_cong:
           messages.success(request, thong_bao)
       else:
           messages.error(request, thong_bao)


       return redirect("GIOHANG:xem_gio_hang")


   ma_bien_the = (
       request.POST.get("ma_bien_the")
       or request.POST.get("ma_bien_the_sp")
       or ""
   ).strip()


   if not ma_bien_the:
       return tra_ve(
           False, "Vui lòng chọn phân loại sản phẩm.", 400
       )


   try:
       so_luong = int(request.POST.get("so_luong", 1))
   except (ValueError, TypeError):
       return tra_ve(False, "Số lượng không hợp lệ.", 400)


   if so_luong < 1 or so_luong > 999:
       return tra_ve(
           False, "Số lượng phải từ 1 đến 999.", 400
       )


   bien_the = BienTheSanPham.objects.filter(
       ma_bien_the=ma_bien_the
   ).first()


   if not bien_the:
       return tra_ve(
           False, "Không tìm thấy biến thể sản phẩm.", 404
       )


   gio_hang = lay_gio_hang(request)


   chi_tiet = ChiTietGioHang.objects.filter(
       gio_hang=gio_hang,
       ma_bien_the_sp=ma_bien_the,
   ).first()


   so_luong_hien_tai = chi_tiet.so_luong if chi_tiet else 0


   if so_luong_hien_tai + so_luong > bien_the.so_luong_ton:
       return tra_ve(
           False, "Số lượng vượt quá tồn kho.", 400, gio_hang
       )


   if (
       chi_tiet is None
       and gio_hang.chi_tiet.count() >= SO_BIEN_THE_TOI_DA
   ):
       return tra_ve(
           False,
           f"Giỏ hàng chỉ chứa tối đa {SO_BIEN_THE_TOI_DA} sản phẩm khác nhau.",
           400,
           gio_hang,
       )


   if chi_tiet:
       chi_tiet.so_luong += so_luong
       chi_tiet.save(update_fields=["so_luong"])
   else:
       ChiTietGioHang.objects.create(
           ma_chi_tiet_gio_hang=tao_ma(ChiTietGioHang),
           gio_hang=gio_hang,
           ma_bien_the_sp=ma_bien_the,
           so_luong=so_luong,
           trang_thai_chon=True,
       )


   return tra_ve(
       True,
       "Sản phẩm đã được thêm vào giỏ hàng thành công!",
       gio_hang=gio_hang,
   )




# ==========================================
# CẬP NHẬT SỐ LƯỢNG
# ==========================================
@khach_hang_required
@require_POST
def cap_nhat_so_luong(request, id):
   chi_tiet = lay_chi_tiet_gio_hang(request, id)


   try:
       so_luong = int(request.POST.get("so_luong", 1))
   except (ValueError, TypeError):
       messages.error(request, "Số lượng không hợp lệ.")
       return redirect("GIOHANG:xem_gio_hang")


   bien_the = BienTheSanPham.objects.filter(
       ma_bien_the=chi_tiet.ma_bien_the_sp
   ).first()


   if so_luong < 1 or so_luong > 999:
       messages.error(request, "Số lượng phải từ 1 đến 999.")


   elif not bien_the:
       messages.error(request, "Không tìm thấy thông tin sản phẩm.")


   elif so_luong > bien_the.so_luong_ton:
       messages.error(request, "Số lượng vượt quá tồn kho.")


   else:
       chi_tiet.so_luong = so_luong
       chi_tiet.save(update_fields=["so_luong"])
       messages.success(request, "Đã cập nhật số lượng.")


   return redirect("GIOHANG:xem_gio_hang")




# ==========================================
# TĂNG SỐ LƯỢNG
# ==========================================
@khach_hang_required
@require_POST
def tang_so_luong(request, id):
   chi_tiet = lay_chi_tiet_gio_hang(request, id)


   bien_the = BienTheSanPham.objects.filter(
       ma_bien_the=chi_tiet.ma_bien_the_sp
   ).first()


   if chi_tiet.so_luong >= 999:
       messages.error(request, "Số lượng không được vượt quá 999.")


   elif not bien_the:
       messages.error(request, "Không tìm thấy thông tin sản phẩm.")


   elif chi_tiet.so_luong >= bien_the.so_luong_ton:
       messages.error(request, "Sản phẩm đã đạt số lượng tồn kho.")


   else:
       chi_tiet.so_luong += 1
       chi_tiet.save(update_fields=["so_luong"])
       messages.success(request, "Đã tăng số lượng sản phẩm.")


   return redirect("GIOHANG:xem_gio_hang")




# ==========================================
# GIẢM SỐ LƯỢNG
# ==========================================
@khach_hang_required
@require_POST
def giam_so_luong(request, id):
   chi_tiet = lay_chi_tiet_gio_hang(request, id)


   if chi_tiet.so_luong > 1:
       chi_tiet.so_luong -= 1
       chi_tiet.save(update_fields=["so_luong"])
       messages.success(request, "Đã giảm số lượng sản phẩm.")
   else:
       messages.error(request, "Số lượng tối thiểu là 1.")


   return redirect("GIOHANG:xem_gio_hang")




# ==========================================
# XÓA SẢN PHẨM KHỎI GIỎ HÀNG
# ==========================================
@khach_hang_required
@require_POST
def xoa_san_pham(request, id):
   chi_tiet = lay_chi_tiet_gio_hang(request, id)
   chi_tiet.delete()


   messages.success(request, "Đã xóa sản phẩm khỏi giỏ hàng.")


   return redirect("GIOHANG:xem_gio_hang")




# ==========================================
# CHỌN / BỎ CHỌN MỘT SẢN PHẨM
# ==========================================
@khach_hang_required
@require_POST
def chon_san_pham(request, id):
   chi_tiet = lay_chi_tiet_gio_hang(request, id)


   chi_tiet.trang_thai_chon = not chi_tiet.trang_thai_chon
   chi_tiet.save(update_fields=["trang_thai_chon"])


   return redirect("GIOHANG:xem_gio_hang")




# ==========================================
# CHỌN / BỎ CHỌN TẤT CẢ SẢN PHẨM
# ==========================================
@khach_hang_required
@require_POST
def chon_tat_ca(request):
   gio_hang = lay_gio_hang(request)


   gia_tri = request.POST.get("chon_tat_ca") == "true"


   gio_hang.chi_tiet.update(
       trang_thai_chon=gia_tri
   )


   return redirect("GIOHANG:xem_gio_hang")




# ==========================================
# XÓA CÁC SẢN PHẨM ĐÃ CHỌN
# ==========================================
@khach_hang_required
@require_POST
def xoa_da_chon(request):
   gio_hang = lay_gio_hang(request)


   so_dong, _ = gio_hang.chi_tiet.filter(
       trang_thai_chon=True
   ).delete()


   if so_dong:
       messages.success(
           request,
           f"Đã xóa {so_dong} sản phẩm khỏi giỏ hàng."
       )
   else:
       messages.warning(
           request,
           "Bạn chưa chọn sản phẩm nào để xóa."
       )


   return redirect("GIOHANG:xem_gio_hang")




# ==========================================
# CHIA SẺ GIỎ HÀNG
# ==========================================
@khach_hang_required
@require_POST
def tao_chia_se(request):
   gio_hang = lay_gio_hang(request)
   danh_sach = list(gio_hang.chi_tiet.all())


   if not danh_sach:
       messages.warning(
           request,
           "Giỏ hàng đang trống, chưa có gì để chia sẻ."
       )
       return redirect("GIOHANG:xem_gio_hang")


   chia_se = ChiaSeGioHang.objects.create(
       ma_chia_se=secrets.token_urlsafe(9),
       ma_khach_hang=gio_hang.ma_khach_hang,
       noi_dung=[
           {
               "ma_bien_the": item.ma_bien_the_sp,
               "so_luong": item.so_luong
           }
           for item in danh_sach
       ],
   )


   return redirect(
       "GIOHANG:trang_chia_se",
       ma=chia_se.ma_chia_se
   )




def trang_chia_se(request, ma):
   chia_se = get_object_or_404(
       ChiaSeGioHang,
       ma_chia_se=ma,
       ma_khach_hang=request.session.get("ma_khach_hang")
   )


   duong_dan = request.build_absolute_uri(
       reverse("GIOHANG:nhan_gio_hang", args=[ma])
   )


   return render(
       request,
       "GIOHANG/chia_se.html",
       {
           "duong_dan": duong_dan,
           "so_san_pham": len(chia_se.noi_dung),
       }
   )




def nhan_gio_hang(request, ma):
   # Tạm thời: bước 2 sẽ làm trang xem và nạp vào giỏ
   chia_se = get_object_or_404(
       ChiaSeGioHang,
       ma_chia_se=ma
   )


   return HttpResponse(
       f"Link hợp lệ, gồm {len(chia_se.noi_dung)} sản phẩm. "
       "Bước 2 sẽ làm tiếp."
   )

