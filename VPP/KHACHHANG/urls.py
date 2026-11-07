from django.urls import path
from . import views
from SANPHAM import views as sanpham_views

app_name = "KHACHHANG"

urlpatterns = [
    path("", views.home, name="home"),

    # Đăng ký - đăng nhập - đăng xuất
    path("dang_ky/", views.dang_ky, name="dang_ky"),
    path("dang-nhap/", views.dang_nhap, name="dang_nhap"),
    path("dang-xuat/", views.dang_xuat, name="dang_xuat"),

    # Hồ sơ cá nhân
    path("ho-so/", views.ho_so_ca_nhan, name="ho_so_ca_nhan"),

    # Sổ địa chỉ
    path("so-dia-chi/", views.so_dia_chi, name="so_dia_chi"),
    path("so-dia-chi/them/", views.them_dia_chi, name="them_dia_chi"),
    path("so-dia-chi/sua/<str:ma_dia_chi>/", views.sua_dia_chi, name="sua_dia_chi"),
    path("so-dia-chi/xoa/<str:ma_dia_chi>/", views.xoa_dia_chi, name="xoa_dia_chi"),
    path("so-dia-chi/mac-dinh/<str:ma_dia_chi>/", views.dat_dia_chi_mac_dinh, name="dat_dia_chi_mac_dinh"),
# Sản phẩm yêu thích
path(
    "yeu-thich/",
    sanpham_views.san_pham_yeu_thich,
    name="san_pham_yeu_thich"
),
    # Lịch sử tích điểm
    path("lich-su-tich-diem/", views.lich_su_tich_diem, name="lich_su_tich_diem"),
    path("voucher/", views.voucher_cua_toi, name="voucher_cua_toi"),

    # Thông báo
    path("thong-bao/", views.danh_sach_thong_bao, name="danh_sach_thong_bao"),
    path("thong-bao/da-doc/<str:ma_thong_bao>/", views.danh_dau_da_doc, name="danh_dau_da_doc"),

    # Hỗ trợ
    path("ho-tro/gui/", views.gui_yeu_cau_ho_tro, name="gui_yeu_cau_ho_tro"),
    path("ho-tro/", views.danh_sach_yeu_cau, name="danh_sach_yeu_cau"),

    # Nhân viên quản lý khách hàng
    path("nhan-vien/khach-hang/", views.danh_sach_khach_hang, name="danh_sach_khach_hang"),
    path("nhan-vien/khach-hang/<str:ma_ho_so>/", views.chi_tiet_khach_hang, name="chi_tiet_khach_hang"),

    # Nhân viên quản lý hỗ trợ
    path("nhan-vien/ho-tro/", views.quan_ly_yeu_cau_ho_tro, name="quan_ly_yeu_cau_ho_tro"),
    path("nhan-vien/ho-tro/xu-ly/<str:ma_yeu_cau>/", views.xu_ly_yeu_cau_ho_tro, name="xu_ly_yeu_cau_ho_tro"),
]