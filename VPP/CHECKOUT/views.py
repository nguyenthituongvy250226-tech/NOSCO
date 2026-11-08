from decimal import Decimal
from types import SimpleNamespace


from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods


from GIOHANG.views import (
   lay_gio_hang,
   bo_sung_thong_tin_san_pham,
)


from SANPHAM.models import BienTheSanPham
from KHACHHANG.models import HoSoKhachHang, SoDiaChi


from DONHANG.services import tao_don_hang
from THANHTOAN.services import tao_thanh_toan_cho_don
from THANHTOAN.vnpay import tao_url_thanh_toan




# ==========================================
# CẤU HÌNH
# ==========================================


PHI_VAN_CHUYEN_TIEU_CHUAN = Decimal("30000")
KHU_VUC_MIEN_PHI = "Đà Nẵng"


SESSION_MUA_NGAY = "checkout_mua_ngay"
SESSION_DON_HANG_THANH_CONG = "checkout_don_hang_thanh_cong"




# ==========================================
# LẤY ẢNH ĐẠI DIỆN CỦA BIẾN THỂ
# ==========================================


def lay_anh_bien_the(bien_the):
   anh = (
       bien_the.hinh_anh.filter(anh_dai_dien=True).first()
       or bien_the.hinh_anh.order_by("thu_tu_hien_thi").first()
   )


   if anh and anh.duong_dan_anh:
       return anh.duong_dan_anh.url


   return ""




# ==========================================
# TẠO DỮ LIỆU SẢN PHẨM MUA NGAY
# ==========================================


def tao_san_pham_mua_ngay(ma_bien_the, so_luong):
   bien_the = get_object_or_404(
       BienTheSanPham.objects.select_related("san_pham"),
       ma_bien_the=ma_bien_the,
   )


   san_pham = bien_the.san_pham


   if san_pham.trang_thai_ban != "Đang bán":
       raise ValueError("Sản phẩm hiện không được kinh doanh.")


   if bien_the.gia_ban is None or bien_the.gia_ban <= 0:
       raise ValueError("Giá bán của sản phẩm không hợp lệ.")


   if bien_the.so_luong_ton <= 0:
       raise ValueError("Sản phẩm hiện đã hết hàng.")


   if so_luong > bien_the.so_luong_ton:
       raise ValueError(
           f"Sản phẩm chỉ còn {bien_the.so_luong_ton} sản phẩm trong kho."
       )


   don_gia = Decimal(str(bien_the.gia_ban))
   thanh_tien = don_gia * so_luong


   return SimpleNamespace(
       ma_bien_the_sp=bien_the.ma_bien_the,
       so_luong=so_luong,
       ten_san_pham=san_pham.ten_san_pham,
       mau_sac=bien_the.mau_sac,
       kich_thuoc=bien_the.kich_thuoc,
       don_gia=don_gia,
       so_luong_ton=bien_the.so_luong_ton,
       hinh_anh=lay_anh_bien_the(bien_the),
       thanh_tien=thanh_tien,
   )




# ==========================================
# LẤY MÃ BIẾN THỂ TỪ SẢN PHẨM TRONG CHECKOUT
# ==========================================


def lay_ma_bien_the_tu_item(item):
   ma_bien_the = getattr(item, "ma_bien_the_sp", None)


   if not ma_bien_the:
       ma_bien_the = getattr(item, "ma_bien_the", None)


   # Trường hợp ma_bien_the là một đối tượng model
   if hasattr(ma_bien_the, "ma_bien_the"):
       ma_bien_the = ma_bien_the.ma_bien_the


   if not ma_bien_the:
       raise ValueError(
           "Không xác định được biến thể của một sản phẩm trong đơn hàng."
       )


   return str(ma_bien_the)




# ==========================================
# TRANG THANH TOÁN
# ==========================================


@require_http_methods(["GET", "POST"])
def checkout(request):


   gio_hang = None
   danh_sach = []
   che_do_thanh_toan = "gio_hang"


   # ======================================
   # 1. LẤY SỔ ĐỊA CHỈ KHÁCH HÀNG
   # ======================================


   ma_nguoi_dung = request.session.get("khachhang_ma_nguoi_dung")


   ho_so = None
   danh_sach_dia_chi = SoDiaChi.objects.none()
   dia_chi_obj = None


   if ma_nguoi_dung:
       ho_so = HoSoKhachHang.objects.filter(
           MaNguoiDung_id=ma_nguoi_dung
       ).first()


       if ho_so:
           danh_sach_dia_chi = SoDiaChi.objects.filter(
               MaKhachHang=ho_so
           ).order_by("-MacDinh", "TenNguoiNhan")


   # ======================================
   # 2. XỬ LÝ CHỌN ĐỊA CHỈ
   # ======================================


   if (
       request.method == "POST"
       and request.POST.get("hanh_dong") == "chon_dia_chi"
   ):
       ma_dia_chi = request.POST.get("ma_dia_chi", "")


       dia_chi_chon = danh_sach_dia_chi.filter(
           MaDiaChi=ma_dia_chi
       ).first()


       if dia_chi_chon:
           request.session["checkout_ma_dia_chi"] = (
               dia_chi_chon.MaDiaChi
           )
           messages.success(request, "Đã cập nhật địa chỉ nhận hàng.")
       else:
           messages.error(request, "Địa chỉ không hợp lệ.")


       return redirect("CHECKOUT:checkout")


   # ======================================
   # 3. LẤY ĐỊA CHỈ ĐANG ĐƯỢC CHỌN
   # ======================================


   ma_dia_chi_session = request.session.get("checkout_ma_dia_chi")


   if ma_dia_chi_session:
       dia_chi_obj = danh_sach_dia_chi.filter(
           MaDiaChi=ma_dia_chi_session
       ).first()


   if not dia_chi_obj:
       dia_chi_obj = (
           danh_sach_dia_chi.filter(MacDinh=True).first()
           or danh_sach_dia_chi.first()
       )


   if dia_chi_obj:
       request.session["checkout_ma_dia_chi"] = dia_chi_obj.MaDiaChi


       dia_chi = {
           "ma_dia_chi": dia_chi_obj.MaDiaChi,
           "ho_ten": dia_chi_obj.TenNguoiNhan,
           "so_dien_thoai": dia_chi_obj.SoDienThoai,
           "dia_chi": dia_chi_obj.DiaChi,
           "mac_dinh": dia_chi_obj.MacDinh,
       }
   else:
       dia_chi = None


   # ======================================
   # 4. XÁC ĐỊNH LUỒNG THANH TOÁN
   # ======================================


   # Khách nhấn Mua ngay từ trang chi tiết sản phẩm
   if request.method == "POST" and request.POST.get("ma_bien_the"):


       ma_bien_the = request.POST.get("ma_bien_the", "").strip()


       try:
           so_luong = int(request.POST.get("so_luong", "1"))


           if so_luong < 1:
               raise ValueError("Số lượng sản phẩm không hợp lệ.")


           item = tao_san_pham_mua_ngay(
               ma_bien_the,
               so_luong,
           )


       except Exception as error:
           messages.error(request, str(error))
           return redirect("sanpham:danh_sach_san_pham")


       request.session[SESSION_MUA_NGAY] = {
           "ma_bien_the": str(ma_bien_the),
           "so_luong": so_luong,
       }


       che_do_thanh_toan = "mua_ngay"
       danh_sach = [item]


   # Khách đang ở checkout mua ngay và nhấn Đặt hàng
   elif (
       request.POST.get("che_do_thanh_toan") == "mua_ngay"
       or (
           request.method == "GET"
           and SESSION_MUA_NGAY in request.session
       )
   ):


       thong_tin_mua_ngay = request.session.get(SESSION_MUA_NGAY)


       if not thong_tin_mua_ngay:
           messages.warning(
               request,
               "Thông tin mua ngay không còn tồn tại. "
               "Vui lòng chọn lại sản phẩm."
           )
           return redirect("sanpham:danh_sach_san_pham")


       try:
           item = tao_san_pham_mua_ngay(
               thong_tin_mua_ngay["ma_bien_the"],
               int(thong_tin_mua_ngay["so_luong"]),
           )


       except Exception as error:
           messages.error(request, str(error))
           return redirect("sanpham:danh_sach_san_pham")


       che_do_thanh_toan = "mua_ngay"
       danh_sach = [item]


   # Khách thanh toán các sản phẩm đã chọn trong giỏ hàng
   else:


       if request.method == "POST":
           request.session.pop(SESSION_MUA_NGAY, None)


       gio_hang = lay_gio_hang(request)


       danh_sach = list(
           gio_hang.chi_tiet.filter(
               trang_thai_chon=True
           ).order_by("ma_chi_tiet_gio_hang")
       )


       if not danh_sach:
           messages.warning(
               request,
               "Bạn chưa chọn sản phẩm nào để thanh toán."
           )
           return redirect("GIOHANG:xem_gio_hang")


       danh_sach = bo_sung_thong_tin_san_pham(danh_sach)


       san_pham_khong_hop_le = [
           item for item in danh_sach
           if item.don_gia <= 0
           or item.so_luong_ton < item.so_luong
       ]


       if san_pham_khong_hop_le:
           messages.error(
               request,
               "Một số sản phẩm đã hết hàng hoặc không còn hợp lệ. "
               "Vui lòng kiểm tra lại giỏ hàng."
           )
           return redirect("GIOHANG:xem_gio_hang")


   # ======================================
   # 5. TÍNH TIỀN
   # ======================================


   tam_tinh = sum(
       (
           Decimal(str(item.thanh_tien))
           for item in danh_sach
       ),
       Decimal("0")
   )


   mien_phi = (
       dia_chi is not None
       and KHU_VUC_MIEN_PHI.casefold() in dia_chi["dia_chi"].casefold()
   )


   phi_van_chuyen = (
       Decimal("0")
       if mien_phi
       else PHI_VAN_CHUYEN_TIEU_CHUAN
   )


   tong_tien = tam_tinh + phi_van_chuyen


   # ======================================
   # 6. XỬ LÝ FORM ĐẶT HÀNG
   # ======================================


   # Không tạo đơn ở lần POST đầu tiên khi khách nhấn Mua ngay
   if request.method == "POST" and not request.POST.get("ma_bien_the"):


       ghi_chu = request.POST.get("ghi_chu", "").strip()


       khung_gio = request.POST.get(
           "khung_gio",
           "hanh_chinh"
       )


       van_chuyen = request.POST.get(
           "van_chuyen",
           "tieu_chuan"
       )


       phuong_thuc_thanh_toan = request.POST.get(
           "phuong_thuc_thanh_toan",
           ""
       )


       khung_gio_hop_le = ["hanh_chinh", "sang", "chieu"]
       phuong_thuc_hop_le = ["vnpay", "cod"]


       if not ho_so or not ma_nguoi_dung:
           messages.error(
               request,
               "Không tìm thấy thông tin khách hàng. "
               "Vui lòng đăng nhập lại."
           )
           return redirect("CHECKOUT:checkout")


       if not dia_chi_obj:
           messages.error(
               request,
               "Vui lòng thêm địa chỉ nhận hàng trước khi đặt hàng."
           )
           return redirect("CHECKOUT:checkout")


       if khung_gio not in khung_gio_hop_le:
           messages.error(
               request,
               "Khung giờ giao hàng không hợp lệ."
           )
           return redirect("CHECKOUT:checkout")


       if van_chuyen != "tieu_chuan":
           messages.error(
               request,
               "Phương thức vận chuyển không hợp lệ."
           )
           return redirect("CHECKOUT:checkout")


       if phuong_thuc_thanh_toan not in phuong_thuc_hop_le:
           messages.error(
               request,
               "Vui lòng chọn phương thức thanh toán."
           )
           return redirect("CHECKOUT:checkout")


       # Kiểm tra lại số lượng và giá tại thời điểm đặt hàng
       for item in danh_sach:
           if item.so_luong < 1:
               messages.error(request, "Số lượng sản phẩm không hợp lệ.")
               return redirect("CHECKOUT:checkout")


           if item.so_luong > item.so_luong_ton:
               messages.error(
                   request,
                   f"Sản phẩm {item.ten_san_pham} không đủ số lượng tồn kho."
               )
               return redirect("CHECKOUT:checkout")


           if item.don_gia <= 0:
               messages.error(
                   request,
                   f"Giá sản phẩm {item.ten_san_pham} không hợp lệ."
               )
               return redirect("CHECKOUT:checkout")


       # Chuyển danh sách sản phẩm sang định dạng DONHANG.services yêu cầu
       cac_chi_tiet = []


       try:
           for item in danh_sach:
               cac_chi_tiet.append({
                   "ma_bien_the": lay_ma_bien_the_tu_item(item),
                   "so_luong": int(item.so_luong),
                   "don_gia": Decimal(str(item.don_gia)),
               })


       except (ValueError, TypeError, AttributeError) as error:
           messages.error(request, str(error))
           return redirect("CHECKOUT:checkout")


       # Lưu khung giờ giao vào ghi chú vì model DonHang hiện chưa có
       # trường riêng dành cho khung giờ giao hàng.
       ten_khung_gio = {
           "hanh_chinh": "Giờ hành chính (8h - 17h)",
           "sang": "Buổi sáng (8h - 12h)",
           "chieu": "Buổi chiều (13h - 17h)",
       }


       ghi_chu_day_du = ghi_chu


       thong_tin_khung_gio = (
           f"Khung giờ giao hàng: {ten_khung_gio[khung_gio]}"
       )


       ghi_chu_day_du = (
           f"{ghi_chu_day_du}\n{thong_tin_khung_gio}"
           if ghi_chu_day_du
           else thong_tin_khung_gio
       )


       ghi_chu_day_du = ghi_chu_day_du[:300]


       # Chuẩn bị dữ liệu tạo đơn
       du_lieu_don_hang = {
           "items": cac_chi_tiet,
           "ma_khach_hang": str(ho_so.pk),
           "ma_dia_chi": str(dia_chi_obj.pk),
           "ten_nguoi_nhan": dia_chi_obj.TenNguoiNhan,
           "sdt_nguoi_nhan": dia_chi_obj.SoDienThoai,
           "dia_chi_nhan_hang": dia_chi_obj.DiaChi,
           "so_tien_giam": Decimal("0"),
           "phi_van_chuyen": phi_van_chuyen,
           "ma_voucher": None,
           "ghi_chu": ghi_chu_day_du,
       }


       try:
           with transaction.atomic():


               # 1. Tạo đơn hàng và chi tiết đơn hàng
               don_hang = tao_don_hang(du_lieu_don_hang)


               # 2. Tạo bản ghi thanh toán
               loai_thanh_toan = (
                   "VNPAY"
                   if phuong_thuc_thanh_toan == "vnpay"
                   else "COD"
               )


               thanh_toan = tao_thanh_toan_cho_don(
                   don_hang,
                   loai_thanh_toan,
               )


               # 3. Nếu chọn VNPay, tạo URL thanh toán
               if phuong_thuc_thanh_toan == "vnpay":
                   url_vnpay = tao_url_thanh_toan(
                       request,
                       thanh_toan.MaGiaoDich,
                       thanh_toan.SoTienThanhToan,
                   )


       except Exception as error:
           messages.error(
               request,
               f"Không thể tạo đơn hàng: {error}"
           )
           return redirect("CHECKOUT:checkout")


       # ======================================
       # 7. LƯU THÔNG TIN HIỂN THỊ TRANG THÀNH CÔNG
       # ======================================


       if phuong_thuc_thanh_toan == "cod":
           ten_phuong_thuc = "Thanh toán khi nhận hàng (COD)"
       else:
           ten_phuong_thuc = "VNPay"


       request.session[SESSION_DON_HANG_THANH_CONG] = {
           "ma_don_hang": don_hang.ma_don_hang,
           "ho_ten": don_hang.ten_nguoi_nhan,
           "so_dien_thoai": don_hang.sdt_nguoi_nhan,
           "dia_chi": don_hang.dia_chi_nhan_hang,
           "phuong_thuc_thanh_toan": ten_phuong_thuc,
           "tong_tien": str(don_hang.tong_tien),
       }


       # ======================================
       # 8. XÓA SẢN PHẨM ĐÃ ĐẶT KHỎI GIỎ HÀNG
       # ======================================


       if che_do_thanh_toan == "gio_hang" and gio_hang:
           gio_hang.chi_tiet.filter(
               trang_thai_chon=True
           ).delete()


       request.session.pop(SESSION_MUA_NGAY, None)
       request.session.pop("checkout_ma_dia_chi", None)


       # ======================================
       # 9. ĐIỀU HƯỚNG THEO PHƯƠNG THỨC THANH TOÁN
       # ======================================


       if phuong_thuc_thanh_toan == "vnpay":
           return redirect(url_vnpay)


       return redirect("CHECKOUT:xem_trang_thanh_cong")


   # ======================================
   # 10. DỮ LIỆU TRUYỀN SANG TEMPLATE
   # ======================================


   context = {
       "gio_hang": gio_hang,
       "danh_sach": danh_sach,
       "dia_chi": dia_chi,
       "danh_sach_dia_chi": danh_sach_dia_chi,


       "tam_tinh": tam_tinh,
       "phi_van_chuyen": phi_van_chuyen,
       "tong_tien": tong_tien,


       "mien_phi": mien_phi,
       "che_do_thanh_toan": che_do_thanh_toan,
   }


   return render(
       request,
       "CHECKOUT/checkout.html",
       context
   )




# ==========================================
# TRANG ĐẶT HÀNG THÀNH CÔNG
# ==========================================


def xem_trang_thanh_cong(request):
   thong_tin_don_hang = request.session.get(
       SESSION_DON_HANG_THANH_CONG,
       {}
   )


   return render(
       request,
       "CHECKOUT/dat_hang_thanh_cong.html",
       thong_tin_don_hang
   )

