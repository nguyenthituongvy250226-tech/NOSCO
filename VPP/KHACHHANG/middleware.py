from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from .models import NguoiDung


class CustomerAccessMiddleware(MiddlewareMixin):
    public_routes = {
        ("", "base"),
        ("", "home"),
        ("", "ve_chung_toi"),
        ("", "danh_sach_bai_viet"),
        ("", "trang_ho_tro"),
        ("KHACHHANG", "dang_ky"),
        ("KHACHHANG", "dang_nhap"),
        ("KHACHHANG", "dang_xuat"),
        ("sanpham", "danh_sach_san_pham"),
        ("sanpham", "danh_sach_thuong_hieu"),
        ("sanpham", "danh_sach_bai_viet"),
        ("DONHANG", "huong_dan_tra_hang_chung"),
        ("khuyenmai", "danh_sach_khuyen_mai"),
        ("khuyenmai", "chi_tiet_khuyen_mai"),
    }

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path_info
        if (
            path.startswith("/admin/")
            or path.startswith(settings.STATIC_URL)
            or path.startswith(settings.MEDIA_URL)
        ):
            return None

        match = request.resolver_match
        route = (match.namespace or "", match.url_name)
        if route in self.public_routes:
            return None

        user_id = request.session.get("khachhang_ma_nguoi_dung")
        if user_id:
            try:
                user = NguoiDung.objects.get(
                    MaNguoiDung=user_id,
                    KichHoat=True,
                )
            except NguoiDung.DoesNotExist:
                user = None

            if user is not None:
                request.nguoi_dung = user
                return None

            for key in (
                "khachhang_ma_nguoi_dung",
                "ma_khach_hang",
                "ten_dang_nhap",
                "vai_tro",
            ):
                request.session.pop(key, None)

        messages.info(request, "Vui lòng đăng nhập để tiếp tục.")
        login_url = reverse("KHACHHANG:dang_nhap")
        query = urlencode({"next": request.get_full_path()})
        return redirect(f"{login_url}?{query}")
