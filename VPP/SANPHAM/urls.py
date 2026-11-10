
from django.urls import path
from . import views

app_name = "sanpham"

urlpatterns = [
    path("", views.danh_sach_san_pham, name="danh_sach_san_pham"),

    path("thuong-hieu/", views.danh_sach_thuong_hieu, name="danh_sach_thuong_hieu"),

    path("bai-viet/", views.danh_sach_bai_viet, name="danh_sach_bai_viet"),

    # Trang danh sách yêu thích
    path("yeu-thich/", views.san_pham_yeu_thich, name="san_pham_yeu_thich"),

    # Thêm hoặc bỏ yêu thích
    path("yeu-thich/toggle/", views.toggle_favorite, name="toggle_favorite"),
path(
    "<str:ma_san_pham>/danh-gia/",
    views.viet_danh_gia_san_pham,
    name="viet_danh_gia_san_pham",
),
    # Chi tiết sản phẩm: đặt cuối cùng
    path("<str:ma_san_pham>/", views.chi_tiet_san_pham, name="chi_tiet_san_pham"),

]
