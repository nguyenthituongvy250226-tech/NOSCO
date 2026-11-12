

from types import SimpleNamespace
from urllib.parse import urlencode


from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse




from KHACHHANG.models import HoSoKhachHang, SoDiaChi
from SANPHAM.forms import DanhGiaSanPhamForm
from SANPHAM.models import DanhGiaSanPham, BienTheSanPham
from THANHTOAN.models import ThanhToan
from KHUYENMAI.services import kiem_tra_va_tinh_voucher


from .forms import (
   SuaDonHangForm,
   YeuCauTraHangForm,
)


from .models import (
   DonHang,
   ChiTietDonHang,
   YeuCauTraHang,
   ChiTietYeuCauTraHang,
   BangChungYeuCauTraHang,
)


from .services import (
   DuLieuDonHangKhongHopLe,
   _ma,
   tinh_phi_van_chuyen,
   tao_don_hang,
   tao_yeu_cau_tra_hang,
   khach_huy_don_hang,
   cap_nhat_thong_tin_nhan,
   chot_don_cho_xac_nhan_qua_han,
   khach_xac_nhan_da_nhan,
   huy_yeu_cau_tra_hang as huy_yeu_cau_tra_hang_service,
)




MA_GHI_CHU_DON_MAU = "[ĐƠN HÀNG MẪU KIỂM THỬ]"




# =========================================================
# HÀM DÙNG CHUNG
# =========================================================


def _ma_khach_hang(request):
   return request.session.get("ma_khach_hang") or getattr(
       request.user,
       "ma_khach_hang",
       None,
   )




def _ten_hien_thi_tai_khoan(request):
   user = request.user
   candidates = []


   if user.is_authenticated:
       candidates.append(getattr(user, "username", ""))


       get_full_name = getattr(user, "get_full_name", None)
       if callable(get_full_name):
           candidates.append(get_full_name())


       candidates.extend([
           getattr(user, "ho_ten", ""),
           getattr(user, "ten_khach_hang", ""),
       ])


   candidates.extend([
       request.session.get("ten_dang_nhap"),
       request.session.get("username"),
       request.session.get("ho_ten"),
       request.session.get("ten_khach_hang"),
   ])


   return next(
       (
           str(value).strip()
           for value in candidates
           if value and str(value).strip()
       ),
       "Khách hàng NOSCO",
   )




def _don_cua_khach_hang(request, ma_don_hang):
   don = get_object_or_404(
       DonHang,
       ma_don_hang=ma_don_hang,
   )


   customer_id = _ma_khach_hang(request)


   if (
       not customer_id
       or str(don.ma_khach_hang) != str(customer_id)
   ):
       raise Http404


   return don




def _lay_yeu_cau_tra_hang(don):
   return YeuCauTraHang.objects.filter(
       ma_don_hang=don,
   ).first()






def _buoc_tien_do_tra_hang(yeu_cau):
    if not yeu_cau or yeu_cau.trang_thai_tra == "tu_choi":
        return []

    current = {
        "cho_xu_ly": 0,
        "da_duyet": 1,
        "cho_hoan_tien": 2,
        "hoan_tat": 3,
    }.get(yeu_cau.trang_thai_tra, 0)

    labels = [
        "Đang xử lý",
        "Đã duyệt",
        "Đã nhận hàng và kiểm tra",
        "Hoàn tất",
    ]

    da_hoan_tat_toan_bo = (
        yeu_cau.trang_thai_tra == "hoan_tat"
    )

    return [
        {
            "ten": label,
            "hoan_tat": (
                index < current
                or (
                    da_hoan_tat_toan_bo
                    and index == current
                )
            ),
            "hien_tai": (
                index == current
                and not da_hoan_tat_toan_bo
            ),
        }
        for index, label in enumerate(labels)
    ]



def _thong_tin_giao_hang(don):
   """
   Thông tin vận chuyển được lưu trực tiếp trong DonHang.
   Không sử dụng model GiaoHang hoặc trạng thái giao hàng riêng.
   """
   return SimpleNamespace(
       don_vi_van_chuyen=don.don_vi_van_chuyen,
       ma_van_don=don.ma_van_don,
       phi_van_chuyen=don.phi_van_chuyen,
       ly_do_that_bai=don.ly_do_that_bai,
       ngay_ban_giao=don.ngay_ban_giao,
       ngay_giao_thanh_cong=don.ngay_giao_thanh_cong,
       cap_nhat_luc=don.cap_nhat_van_chuyen_luc,
   )




def _lay_thong_tin_thoi_han_tra(don):
   """
   Không giới hạn trả hàng theo 7 ngày hoặc 24 giờ.


   Khách được gửi yêu cầu khi:
   - Đơn đang ở trạng thái da_giao.
   - Khách chưa xác nhận đã nhận hàng.
   - Chưa có yêu cầu trả hàng trước đó.
   """
   delivered_at = don.ngay_giao_thanh_cong


   co_the_tra = bool(
       don.trang_thai_don == "da_giao"
       and not don.khach_da_xac_nhan_nhan
       and not YeuCauTraHang.objects.filter(
           ma_don_hang=don,
       ).exists()
   )


   return delivered_at, None, co_the_tra




def _context_co_ban(request):
   return {
       "ten_hien_thi": _ten_hien_thi_tai_khoan(request),
       "dang_la_nhan_vien": False,
   }




# =========================================================
# DANH SÁCH ĐƠN HÀNG
# =========================================================


def danh_sach_don_hang(request, trang_thai=None):
   # Xử lý đơn chưa thanh toán quá hạn.
   chot_don_cho_xac_nhan_qua_han()


   customer_id = _ma_khach_hang(request)


   don_hang_goc = (
       DonHang.objects.filter(ma_khach_hang=customer_id)
       if customer_id
       else DonHang.objects.none()
   )


   legacy_status = request.GET.get("trang_thai")


   legacy_status_map = {
       "all": "tat-ca",
       "cho_xac_nhan": "cho-xac-nhan",
       "cho_lay_hang": "cho-lay-hang",
       "cho_giao_hang": "cho-giao-hang",
       "da_giao": "da-giao",
       "tra_hang": "tra-hang",
       "da_huy": "da-huy",
   }


   trang_thai_slug = trang_thai or legacy_status_map.get(
       legacy_status,
       "tat-ca",
   )


   cac_trang_thai = [
       {"ma": "all", "slug": "tat-ca", "ten": "Tất cả"},
       {
           "ma": "cho_xac_nhan",
           "slug": "cho-xac-nhan",
           "ten": "Chờ xác nhận",
       },
       {
           "ma": "cho_lay_hang",
           "slug": "cho-lay-hang",
           "ten": "Chờ lấy hàng",
       },
       {
           "ma": "cho_giao_hang",
           "slug": "cho-giao-hang",
           "ten": "Chờ giao hàng",
       },
       {
           "ma": "da_giao",
           "slug": "da-giao",
           "ten": "Đã giao",
       },
       {
           "ma": "tra_hang",
           "slug": "tra-hang",
           "ten": "Trả hàng",
       },
       {
           "ma": "da_huy",
           "slug": "da-huy",
           "ten": "Đã hủy",
       },
   ]


   trang_thai_hop_le = {
       item["slug"]: item["ma"]
       for item in cac_trang_thai
   }


   if trang_thai_slug not in trang_thai_hop_le:
       raise Http404


   trang_thai_hien_tai = trang_thai_hop_le[trang_thai_slug]


   so_don_theo_trang_thai = dict(
       don_hang_goc.values("trang_thai_don")
       .annotate(tong_so=Count("ma_don_hang"))
       .values_list("trang_thai_don", "tong_so")
   )


   tong_so_don = don_hang_goc.count()


   for item in cac_trang_thai:
       item["tong_so"] = (
           tong_so_don
           if item["ma"] == "all"
           else so_don_theo_trang_thai.get(item["ma"], 0)
       )


   don_hang = don_hang_goc.prefetch_related(
       "chi_tiet",
       "thanh_toans",
   )


   if trang_thai_hien_tai != "all":
       don_hang = don_hang.filter(
           trang_thai_don=trang_thai_hien_tai,
       )


   tu_khoa = request.GET.get("q", "").strip()
   ngay_dat = request.GET.get("ngay_dat", "").strip()


   if tu_khoa:
       don_hang = don_hang.filter(
           Q(ma_don_hang__icontains=tu_khoa)
           | Q(chi_tiet__ma_bien_the__icontains=tu_khoa)
       ).distinct()


   if ngay_dat:
       don_hang = don_hang.filter(
           ngay_dat__date=ngay_dat,
       )


   don_hang = list(don_hang)


   # Lấy mã biến thể của tất cả sản phẩm trong các đơn hàng.
   danh_sach_ma_bien_the = {
       ct.ma_bien_the
       for don in don_hang
       for ct in don.chi_tiet.all()
   }


   # Tra cứu mã sản phẩm tương ứng với từng mã biến thể.
   bien_the_to_san_pham = dict(
       BienTheSanPham.objects.using("sanpham")
       .filter(ma_bien_the__in=danh_sach_ma_bien_the)
       .values_list("ma_bien_the", "san_pham_id")
   )


   # Gắn mã sản phẩm vào từng chi tiết đơn hàng.
   for don in don_hang:
       for ct in don.chi_tiet.all():
           ct.ma_san_pham_danh_gia = bien_the_to_san_pham.get(
               ct.ma_bien_the
           )
   for don in don_hang:
       thanh_toans = list(don.thanh_toans.all())


       don.thanh_toan_da_thanh_cong = any(
           payment.TrangThaiThanhToan == "DaThanhToan"
           for payment in thanh_toans
       )


       don.co_the_thanh_toan_lai = (
           don.trang_thai_don == "cho_xac_nhan"
           and not don.thanh_toan_da_thanh_cong
           and any(
               payment.PhuongThucThanhToan != "COD"
               for payment in thanh_toans
           )
       )


       don.trang_thai_hien_thi = don.get_trang_thai_don_display()


   context = {
       **_context_co_ban(request),
       "don_hang": don_hang,
       "cac_trang_thai": cac_trang_thai,
       "trang_thai_hien_tai": trang_thai_hien_tai,
       "trang_thai_slug": trang_thai_slug,
       "so_don_theo_trang_thai": cac_trang_thai,
       "tu_khoa": tu_khoa,
       "ngay_dat": ngay_dat,
       "co_the_tao_don_mau": (
           settings.DEBUG
           and bool(customer_id)
           and not don_hang_goc.filter(
               ghi_chu__startswith=MA_GHI_CHU_DON_MAU,
           ).exists()
       ),
   }


   return render(
       request,
       "donhang/danh_sach.html",
       context,
   )




# =========================================================
# TẠO ĐƠN HÀNG MẪU KIỂM THỬ
# =========================================================


@require_POST
def tao_don_hang_mau(request):
   if not settings.DEBUG:
       raise Http404


   ma_khach_hang = _ma_khach_hang(request)


   if not ma_khach_hang:
       return redirect("KHACHHANG:dang_nhap")


   nguoi_dung_id = request.session.get(
       "khachhang_ma_nguoi_dung",
   )


   if not nguoi_dung_id:
       messages.error(
           request,
           "Không xác định được tài khoản khách hàng.",
       )
       return redirect("DONHANG:danh_sach")


   ho_so = HoSoKhachHang.objects.filter(
       MaHoSo=ma_khach_hang,
       MaNguoiDung_id=nguoi_dung_id,
   ).first()


   if ho_so is None:
       messages.error(
           request,
           "Không tìm thấy hồ sơ khách hàng của bạn.",
       )
       return redirect("KHACHHANG:ho_so_ca_nhan")


   dia_chi = SoDiaChi.objects.filter(
       MaKhachHang=ho_so,
   ).order_by(
       "-MacDinh",
       "TenNguoiNhan",
   ).first()


   if dia_chi is None:
       thong_tin_nhan_hang = {
           "ma_dia_chi": "TESTADDR01",
           "ten_nguoi_nhan": ho_so.HoVaTen or "Khách hàng kiểm thử",
           "sdt_nguoi_nhan": ho_so.SoDienThoai or "0000000000",
           "dia_chi_nhan_hang": (
               "Đà Nẵng (địa chỉ giả lập, chỉ dùng kiểm thử)"
           ),
       }
   else:
       thong_tin_nhan_hang = {
           "ma_dia_chi": dia_chi.MaDiaChi,
           "ten_nguoi_nhan": dia_chi.TenNguoiNhan,
           "sdt_nguoi_nhan": dia_chi.SoDienThoai,
           "dia_chi_nhan_hang": dia_chi.DiaChi,
       }


   if DonHang.objects.filter(
       ma_khach_hang=ho_so.MaHoSo,
       ghi_chu__startswith=MA_GHI_CHU_DON_MAU,
   ).exists():
       messages.info(
           request,
           "Tài khoản đã có bộ đơn hàng mẫu để kiểm thử.",
       )
       return redirect("DONHANG:danh_sach")


   cac_don_mau = [
       ("cho_xac_nhan", "Đơn mẫu — chờ xác nhận"),
       ("cho_lay_hang", "Đơn mẫu — chờ lấy hàng"),
       ("cho_giao_hang", "Đơn mẫu — chờ giao hàng"),
       ("da_giao", "Đơn mẫu — đã giao"),
       ("tra_hang", "Đơn mẫu — trả hàng"),
       ("da_huy", "Đơn mẫu — đã hủy"),
   ]


   try:
       with transaction.atomic():
           from THANHTOAN.services import tao_thanh_toan_cho_don


           for trang_thai, mo_ta in cac_don_mau:
               don = tao_don_hang({
                   "ma_khach_hang": ho_so.MaHoSo,
                   **thong_tin_nhan_hang,
                   "ghi_chu": f"{MA_GHI_CHU_DON_MAU} {mo_ta}",
                   "phi_van_chuyen": str(
                       tinh_phi_van_chuyen(
                           thong_tin_nhan_hang["dia_chi_nhan_hang"]
                       )
                   ),
                   "items": [{
                       "ma_bien_the": "BT001",
                       "so_luong": 1,
                       "don_gia": "5000",
                   }],
               })


               tao_thanh_toan_cho_don(don, "COD")


               chi_tiet = don.chi_tiet.get()


               if trang_thai in {
                   "cho_giao_hang",
                   "da_giao",
                   "tra_hang",
               }:
                   don.don_vi_van_chuyen = "NOSCO Express"
                   don.ma_van_don = f"TEST{don.pk}"
                   don.ngay_ban_giao = timezone.now()
                   don.cap_nhat_van_chuyen_luc = timezone.now()


               if trang_thai in {"da_giao", "tra_hang"}:
                   don.ngay_giao_thanh_cong = timezone.now()


               if trang_thai == "tra_hang":
                   yeu_cau_tra = YeuCauTraHang.objects.create(
                       ma_yeu_cau_tra=_ma("YT"),
                       ma_don_hang=don,
                       ly_do_tra="Sản phẩm mẫu cần kiểm tra",
                       mo_ta_van_de=(
                           "Yêu cầu trả hàng mẫu để kiểm thử giao diện."
                       ),
                   )


                   ChiTietYeuCauTraHang.objects.create(
                       yeu_cau=yeu_cau_tra,
                       chi_tiet_don_hang=chi_tiet,
                       so_luong=1,
                   )


               don.trang_thai_don = trang_thai
               don.save()


   except DuLieuDonHangKhongHopLe as exc:
       messages.error(
           request,
           str(exc) or "Không thể tạo bộ đơn mẫu.",
       )
       return redirect("DONHANG:danh_sach")


   messages.success(
       request,
       "Đã tạo 6 đơn hàng mẫu theo 6 trạng thái đơn hàng.",
   )


   return redirect("DONHANG:danh_sach")




# =========================================================
# THÔNG TIN TÀI KHOẢN
# =========================================================


def thong_tin_tai_khoan(request):
   return redirect("KHACHHANG:ho_so_ca_nhan")




# =========================================================
# CHI TIẾT ĐƠN HÀNG
# =========================================================


def chi_tiet_don_hang(request, ma_don_hang):
   don_hang = _don_cua_khach_hang(request, ma_don_hang)


   chot_don_cho_xac_nhan_qua_han()


   don_hang = get_object_or_404(
       DonHang.objects.prefetch_related(
           "chi_tiet",
           "thanh_toans",
       ),
       pk=don_hang.pk,
   )


   chi_tiet = list(don_hang.chi_tiet.all())


   from SANPHAM.models import BienTheSanPham


   danh_sach_ma_bien_the = [
       item.ma_bien_the for item in chi_tiet
   ]


   bien_the_map = {
       bt.ma_bien_the: bt
       for bt in BienTheSanPham.objects.filter(
           ma_bien_the__in=danh_sach_ma_bien_the,
       ).select_related(
           "san_pham",
       ).prefetch_related(
           "hinh_anh",
       )
   }


   for item in chi_tiet:
       bien_the = bien_the_map.get(item.ma_bien_the)
       item.bien_the_san_pham = bien_the
       item.hinh_anh_hien_thi = None


       if bien_the:
           danh_sach_anh = list(bien_the.hinh_anh.all())


           item.hinh_anh_hien_thi = next(
               (
                   anh for anh in danh_sach_anh
                   if anh.anh_dai_dien
               ),
               danh_sach_anh[0] if danh_sach_anh else None,
           )


   cac_thanh_toan = list(
       don_hang.thanh_toans.filter(
           LoaiGiaoDich="ThanhToan",
       )
   )


   yeu_cau_tra = _lay_yeu_cau_tra_hang(don_hang)
   giao_hang = _thong_tin_giao_hang(don_hang)


   delivered_at, han_tra_hang, co_the_tra = (
       _lay_thong_tin_thoi_han_tra(don_hang)
   )


   giao_hang_thanh_cong = (
       don_hang.trang_thai_don in {"da_giao", "tra_hang"}
   )


   dang_cho_khach_chon = bool(
       co_the_tra and not yeu_cau_tra
   )


   trang_thai_hien_thi = don_hang.get_trang_thai_don_display()


   co_the_tra_hang = bool(
       giao_hang_thanh_cong
       and co_the_tra
       and not yeu_cau_tra
   )


   khach_co_the_sua_don = (
       don_hang.trang_thai_don == "cho_xac_nhan"
   )


   khach_co_the_huy_don = (
       don_hang.trang_thai_don == "cho_xac_nhan"
   )


   context = {
       **_context_co_ban(request),
       "don_hang": don_hang,
       "chi_tiet": chi_tiet,
       "cac_thanh_toan": cac_thanh_toan,
       "giao_hang": giao_hang,
       "phi_van_chuyen": don_hang.phi_van_chuyen,
       "yeu_cau_tra": yeu_cau_tra,
       "yeu_cau_tra_cu": yeu_cau_tra,
       "buoc_tien_do_tra": _buoc_tien_do_tra_hang(yeu_cau_tra),
       "giao_hang_thanh_cong": giao_hang_thanh_cong,
       "han_tra_hang": han_tra_hang,
       "trong_thoi_han_tra_hang": co_the_tra,
       "trang_thai_hien_thi": trang_thai_hien_thi,
       "co_the_tra_hang": co_the_tra_hang,
       "duoc_tra_hang": co_the_tra_hang,
       "da_co_yeu_cau_tra_hang": bool(yeu_cau_tra),
       "dang_cho_khach_chon": dang_cho_khach_chon,
       "khach_co_the_sua_don": khach_co_the_sua_don,
       "khach_co_the_huy_don": khach_co_the_huy_don,
       "khach_da_xac_nhan_nhan": don_hang.khach_da_xac_nhan_nhan,
   }


   status_steps = [
       "Chờ xác nhận",
       "Chờ lấy hàng",
       "Chờ giao hàng",
       "Đã giao",
   ]


   status_index = {
       "cho_xac_nhan": 0,
       "cho_lay_hang": 1,
       "cho_giao_hang": 2,
       "da_giao": 3,
       "tra_hang": 3,
       "da_huy": -1,
   }.get(don_hang.trang_thai_don, -1)


   context["cac_buoc"] = [
       {
           "ten": label,
           "hoan_tat": index < status_index,
           "hien_tai": (
               index == status_index
               and don_hang.trang_thai_don != "tra_hang"
           ),
       }
       for index, label in enumerate(status_steps)
   ]


   context["tien_do"] = (
       100 if status_index == 3 else max(status_index, 0) * 28
   )


   if don_hang.trang_thai_don == "tra_hang":
       template_name = "donhang/chi-tiet-don-hang/tra_hang.html"
   else:
       template_map = {
           "cho_xac_nhan": (
               "donhang/chi-tiet-don-hang/cho_xac_nhan.html"
           ),
           "cho_lay_hang": (
               "donhang/chi-tiet-don-hang/cho_lay_hang.html"
           ),
           "cho_giao_hang": (
               "donhang/chi-tiet-don-hang/cho_giao_hang.html"
           ),
           "da_giao": (
               "donhang/chi-tiet-don-hang/da_giao.html"
           ),
           "da_huy": (
               "donhang/chi-tiet-don-hang/da_huy.html"
           ),
       }


       template_name = template_map[don_hang.trang_thai_don]


   return render(request, template_name, context)




# =========================================================
# SỬA THÔNG TIN NHẬN HÀNG
# =========================================================


def sua_don_hang(request, ma_don_hang):
   don = _don_cua_khach_hang(request, ma_don_hang)


   if don.trang_thai_don != "cho_xac_nhan":
       messages.error(
           request,
           "Chỉ sửa được đơn đang chờ xác nhận.",
       )
       return redirect(
           "DONHANG:chi_tiet",
           ma_don_hang=don.pk,
       )


   form = SuaDonHangForm(
       request.POST or None,
       instance=don,
   )


   if request.method == "POST" and form.is_valid():
       try:
           cap_nhat_thong_tin_nhan(
               don,
               **form.cleaned_data,
           )
       except DuLieuDonHangKhongHopLe as exc:
           form.add_error(None, str(exc))
       else:
           messages.success(
               request,
               "Thông tin nhận hàng đã được cập nhật.",
           )
           return redirect(
               "DONHANG:chi_tiet",
               ma_don_hang=don.pk,
           )


   return render(
       request,
       "donhang/sua_don.html",
       {
           **_context_co_ban(request),
           "form": form,
           "don_hang": don,
       },
   )




# =========================================================
# CHỌN ĐỊA CHỈ NHẬN HÀNG
# =========================================================


def chon_dia_chi(request, ma_don_hang):
   don = _don_cua_khach_hang(request, ma_don_hang)


   if don.trang_thai_don != "cho_xac_nhan":
       messages.error(
           request,
           "Chỉ có thể thay đổi địa chỉ khi đơn đang chờ xác nhận.",
       )
       return redirect(
           "DONHANG:chi_tiet",
           ma_don_hang=don.pk,
       )


   danh_sach_dia_chi = SoDiaChi.objects.filter(
       MaKhachHang_id=don.ma_khach_hang,
   ).order_by(
       "-MacDinh",
       "TenNguoiNhan",
   )


   url_chon_dia_chi = reverse(
       "DONHANG:chon_dia_chi",
       kwargs={"ma_don_hang": don.pk},
   )


   url_them_dia_chi = (
       reverse("KHACHHANG:them_dia_chi")
       + "?"
       + urlencode({"next": url_chon_dia_chi})
   )


   return render(
       request,
       "donhang/chi-tiet-don-hang/chon_dia_chi.html",
       {
           **_context_co_ban(request),
           "don_hang": don,
           "danh_sach_dia_chi": danh_sach_dia_chi,
           "url_them_dia_chi": url_them_dia_chi,
       },
   )




@require_POST
def xac_nhan_dia_chi(request, ma_don_hang):
   don = _don_cua_khach_hang(request, ma_don_hang)


   if don.trang_thai_don != "cho_xac_nhan":
       messages.error(
           request,
           "Đơn hàng không còn được phép thay đổi địa chỉ.",
       )
       return redirect(
           "DONHANG:chi_tiet",
           ma_don_hang=don.pk,
       )


   ma_dia_chi = request.POST.get("ma_dia_chi")


   dia_chi = get_object_or_404(
       SoDiaChi,
       MaDiaChi=ma_dia_chi,
       MaKhachHang_id=don.ma_khach_hang,
   )


   phi_van_chuyen_moi = tinh_phi_van_chuyen(
       dia_chi.DiaChi
   )


   don.ma_dia_chi = dia_chi.MaDiaChi
   don.ten_nguoi_nhan = dia_chi.TenNguoiNhan
   don.sdt_nguoi_nhan = dia_chi.SoDienThoai
   don.dia_chi_nhan_hang = dia_chi.DiaChi
   don.phi_van_chuyen = phi_van_chuyen_moi


   don.tong_tien = max(
       don.tong_tien_hang
       - don.so_tien_giam
       + phi_van_chuyen_moi,
       0,
   )


   don.save(update_fields=[
       "ma_dia_chi",
       "ten_nguoi_nhan",
       "sdt_nguoi_nhan",
       "dia_chi_nhan_hang",
       "phi_van_chuyen",
       "tong_tien",
   ])


   messages.success(
       request,
       "Đã cập nhật địa chỉ nhận hàng cho đơn hàng.",
   )


   return redirect(
       "DONHANG:chi_tiet",
       ma_don_hang=don.pk,
   )




# =========================================================
# KHÁCH HỦY ĐƠN
# =========================================================


@require_POST
def huy_don_hang(request, ma_don_hang):
   don = _don_cua_khach_hang(request, ma_don_hang)


   try:
       khach_huy_don_hang(don)
   except DuLieuDonHangKhongHopLe as exc:
       messages.error(request, str(exc))
   else:
       messages.success(request, "Đơn hàng đã được hủy.")


   return redirect(
       "DONHANG:chi_tiet",
       ma_don_hang=don.pk,
   )




# =========================================================
# HƯỚNG DẪN TRẢ HÀNG
# =========================================================


def huong_dan_tra_hang_chung(request):
   return render(
       request,
       "donhang/huong_dan_tra_hang_chung.html",
       _context_co_ban(request),
   )




# =========================================================
# KHÁCH XÁC NHẬN ĐÃ NHẬN HÀNG
# =========================================================


@require_POST
def xac_nhan_da_nhan(request, ma_don_hang):
   don = _don_cua_khach_hang(request, ma_don_hang)


   chot_don_cho_xac_nhan_qua_han()


   don.refresh_from_db()


   try:
       khach_xac_nhan_da_nhan(don)
   except DuLieuDonHangKhongHopLe as exc:
       messages.error(request, str(exc))
   else:
       messages.success(
           request,
           "Bạn đã xác nhận nhận hàng. Trạng thái đơn hàng vẫn là Đã giao.",
       )


   return redirect(
       "DONHANG:chi_tiet",
       ma_don_hang=don.pk,
   )




# =========================================================
# TẠO YÊU CẦU TRẢ HÀNG
# =========================================================


def yeu_cau_tra_hang(request, ma_don_hang):
   don = _don_cua_khach_hang(request, ma_don_hang)


   chot_don_cho_xac_nhan_qua_han()
   don.refresh_from_db()


   _, _, co_the_tra = _lay_thong_tin_thoi_han_tra(don)


   if not co_the_tra:
       messages.error(
           request,
           "Đơn hàng chưa đủ điều kiện yêu cầu trả hàng. "
           "Bạn chỉ có thể gửi yêu cầu khi đơn đã ở trạng thái "
           "Đã giao và chưa xác nhận đã nhận hàng.",
       )
       return redirect(
           "DONHANG:chi_tiet",
           ma_don_hang=don.pk,
       )


   giao_dich_thanh_cong = ThanhToan.objects.filter(
       DonHang=don,
       LoaiGiaoDich="ThanhToan",
       TrangThaiThanhToan="DaThanhToan",
   ).first()


   phuong_thuc_thanh_toan = (
       giao_dich_thanh_cong.PhuongThucThanhToan
       if giao_dich_thanh_cong else None
   )


   form = YeuCauTraHangForm(
       request.POST or None,
       request.FILES or None,
       don_hang=don,
       phuong_thuc_thanh_toan=phuong_thuc_thanh_toan,
   )


   if request.method == "POST" and form.is_valid():
       quantities = {
           item_id: request.POST.get(
               f"so_luong_{item_id}",
               "1",
           )
           for item_id in form.cleaned_data["chi_tiet_ids"]
       }


       try:
           yeu_cau = tao_yeu_cau_tra_hang(
               don,
               ly_do_tra=form.cleaned_data["ly_do_tra"],
               mo_ta_van_de=form.cleaned_data["mo_ta_van_de"],
               ma_van_don_khach=form.cleaned_data["ma_van_don_khach"],
               ngan_hang_hoan_tien=form.cleaned_data[
                   "ngan_hang_hoan_tien"
               ],
               ten_chu_tai_khoan=form.cleaned_data[
                   "ten_chu_tai_khoan"
               ],
               so_tai_khoan=form.cleaned_data["so_tai_khoan"],
               san_pham=quantities,
               tep_minh_chung=form.cleaned_data["tep_minh_chung"],
           )
       except DuLieuDonHangKhongHopLe as exc:
           form.add_error(None, str(exc))
       else:
           return render(
               request,
                 "donhang/chi-tiet-don-hang/thong_bao_gui_yeu_cau_tc.html",
               {
                   **_context_co_ban(request),
                   "yeu_cau": yeu_cau,
                   "don_hang": don,
               },
           )


   return render(
       request,
       "donhang/yeu_cau_tra_hang.html",
       {
           **_context_co_ban(request),
           "form": form,
           "don_hang": don,
           "phuong_thuc_thanh_toan": phuong_thuc_thanh_toan,
           "return_deadline": None,
           "selected_item_ids": (
               form["chi_tiet_ids"].value() or []
           ),
       },
   )




# =========================================================
# THEO DÕI YÊU CẦU TRẢ HÀNG
# =========================================================


def theo_doi_yeu_cau_tra(request, ma_don_hang):
   don = _don_cua_khach_hang(request, ma_don_hang)


   yeu_cau = get_object_or_404(
       YeuCauTraHang.objects.select_related(
           "ma_don_hang",
       ).prefetch_related(
           "san_pham_tra__chi_tiet_don_hang",
       ),
       ma_don_hang=don,
   )


   return render(
       request,
       "donhang/theo_doi_yeu_cau_tra.html",
       {
           **_context_co_ban(request),
           "don_hang": don,
           "yeu_cau_tra": yeu_cau,
           "buoc_tien_do_tra": _buoc_tien_do_tra_hang(yeu_cau),
       },
   )




# =========================================================
# KHÁCH HỦY YÊU CẦU TRẢ HÀNG
# =========================================================


@require_POST
def huy_yeu_cau_tra_hang(request, ma_don_hang):
   don = _don_cua_khach_hang(request, ma_don_hang)


   try:
       huy_yeu_cau_tra_hang_service(don)
   except DuLieuDonHangKhongHopLe as exc:
       messages.error(request, str(exc))


   return redirect(
       "DONHANG:chi_tiet",
       ma_don_hang=don.pk,
   )




# =========================================================
# XEM MINH CHỨNG TRẢ HÀNG
# =========================================================


def xem_minh_chung_tra_hang(request, evidence_id):
   evidence = get_object_or_404(
       BangChungYeuCauTraHang.objects.select_related(
           "yeu_cau__ma_don_hang",
       ),
       pk=evidence_id,
   )


   _don_cua_khach_hang(
       request,
       evidence.yeu_cau.ma_don_hang_id,
   )


   response = FileResponse(
       evidence.tep.open("rb"),
       content_type=evidence.loai_tep or "application/octet-stream",
       as_attachment=False,
       filename=evidence.ten_tep,
   )


   response["X-Content-Type-Options"] = "nosniff"


   return response




# =========================================================
# CÁC VIEW QUẢN TRỊ CŨ
# Website không cung cấp chức năng nhân viên xử lý đơn hàng.
# Superuser thực hiện các nghiệp vụ này trong Django Admin.
# =========================================================


def _khong_con_chuc_nang_quan_tri_tren_website(
   request,
   *args,
   **kwargs,
):
   raise Http404




def xu_ly_danh_sach_don_hang(request):
   return _khong_con_chuc_nang_quan_tri_tren_website(request)




def nhan_vien_xu_ly_don_hang(request, ma_don_hang):
   return _khong_con_chuc_nang_quan_tri_tren_website(request)




def nhan_vien_cap_nhat_giao_hang(request, ma_don_hang):
   return _khong_con_chuc_nang_quan_tri_tren_website(request)




def danh_sach_yeu_cau_tra_hang(request):
   return _khong_con_chuc_nang_quan_tri_tren_website(request)




def nhan_vien_xu_ly_tra_hang(request, ma_yeu_cau_tra):
   return _khong_con_chuc_nang_quan_tri_tren_website(request)




def tao_don_hang_api(request):
   return _khong_con_chuc_nang_quan_tri_tren_website(request)




def cap_nhat_giao_hang_api(request, ma_don_hang):
   return _khong_con_chuc_nang_quan_tri_tren_website(request)




def tra_cuu_don_hang_api(request, ma_don_hang):
   return _khong_con_chuc_nang_quan_tri_tren_website(request)


@require_POST
def gui_danh_gia_san_pham(request, ma_don_hang, ma_bien_the):
   # Kiểm tra đơn hàng có thuộc về khách hàng đang đăng nhập không
   don = _don_cua_khach_hang(request, ma_don_hang)


   # Chỉ cho phép đánh giá khi đơn hàng đã giao
   if don.trang_thai_don != "da_giao":
       messages.error(request, "Bạn chỉ có thể đánh giá sản phẩm đã nhận.")
       return redirect("DONHANG:chi_tiet", ma_don_hang=ma_don_hang)


   # Kiểm tra sản phẩm có thực sự nằm trong đơn hàng không
   co_trong_don = ChiTietDonHang.objects.filter(
       ma_don_hang=don,
       ma_bien_the=ma_bien_the,
   ).exists()


   if not co_trong_don:
       raise Http404


   # Lấy thông tin biến thể và sản phẩm
   bien_the = get_object_or_404(
       BienTheSanPham.objects.using("sanpham").select_related("san_pham"),
       ma_bien_the=ma_bien_the,
   )


   ma_khach_hang = _ma_khach_hang(request)


   # Không cho phép khách hàng đánh giá trùng sản phẩm
   da_danh_gia = DanhGiaSanPham.objects.using("sanpham").filter(
       san_pham=bien_the.san_pham,
       ma_khach_hang=ma_khach_hang,
   ).exists()


   if da_danh_gia:
       messages.info(request, "Bạn đã đánh giá sản phẩm này rồi.")
       return redirect("DONHANG:chi_tiet", ma_don_hang=ma_don_hang)


   # Kiểm tra dữ liệu đánh giá
   form = DanhGiaSanPhamForm(request.POST)


   if form.is_valid():
       danh_gia = form.save(commit=False)
       danh_gia.san_pham = bien_the.san_pham
       danh_gia.ma_khach_hang = ma_khach_hang
       danh_gia.save(using="sanpham")


       messages.success(request, "Đánh giá sản phẩm thành công!")
   else:
       messages.error(request, "Thông tin đánh giá chưa hợp lệ. Vui lòng thử lại.")


   return redirect("DONHANG:chi_tiet", ma_don_hang=ma_don_hang)




@require_POST
def ap_dung_voucher(request):
   ma_voucher = request.POST.get("ma_voucher", "")
   tong_tien_hang = request.POST.get("tong_tien_hang", "0")


   # Lấy mã hồ sơ khách hàng bằng hàm có sẵn
   ma_khach_hang = _ma_khach_hang(request)


   if not ma_khach_hang:
       return JsonResponse({
           "hop_le": False,
           "thong_bao": "Vui lòng đăng nhập để sử dụng voucher.",
       }, status=401)


   # Lấy mã tài khoản đang đăng nhập
   ma_nguoi_dung = request.session.get(
       "khachhang_ma_nguoi_dung"
   )


   # Kiểm tra hồ sơ khách hàng
   ho_so = HoSoKhachHang.objects.filter(
       MaHoSo=ma_khach_hang,
       MaNguoiDung_id=ma_nguoi_dung,
       MaNguoiDung__VaiTro="KHACH_HANG",
   ).first()


   if ho_so is None:
       return JsonResponse({
           "hop_le": False,
           "thong_bao": "Không tìm thấy hồ sơ khách hàng.",
       }, status=404)


   # Lấy hạng thành viên mới nhất từ database
   hang_thanh_vien = ho_so.HangThanhVien


   try:
       ket_qua = kiem_tra_va_tinh_voucher(
           ma_voucher=ma_voucher,
           tong_tien_hang=tong_tien_hang,
           hang_thanh_vien=hang_thanh_vien,
           ma_khach_hang=ho_so.MaHoSo,
       )


   except (ValueError, TypeError):
       return JsonResponse({
           "hop_le": False,
           "thong_bao": "Thông tin đơn hàng không hợp lệ.",
       }, status=400)


   return JsonResponse({
       "hop_le": ket_qua["hop_le"],
       "thong_bao": ket_qua["thong_bao"],
       "ma_voucher": (
           ket_qua["voucher"].MaVoucher
           if ket_qua["voucher"] else None
       ),
       "so_tien_giam": str(
           ket_qua["so_tien_giam"]
       ),
   })

