
from django.urls import path
from . import views

app_name = "DONHANG"

urlpatterns = [
    path("", views.danh_sach_don_hang, name="danh_sach"),
    path("nhan-vien/", views.xu_ly_danh_sach_don_hang, name="nhan_vien_don_hang"),
    path("nhan-vien/tra-hang/", views.danh_sach_yeu_cau_tra_hang, name="nhan_vien_tra_hang"),
    path("nhan-vien/tra-hang/<str:ma_yeu_cau_tra>/", views.nhan_vien_xu_ly_tra_hang, name="nhan_vien_xu_ly_tra_hang"),
    path("tra-hang/minh-chung/<int:evidence_id>/", views.xem_minh_chung_tra_hang, name="minh_chung_tra_hang"),
    path("api/tao/", views.tao_don_hang_api, name="api_tao"),
    path("api/<str:ma_don_hang>/giao-hang/", views.cap_nhat_giao_hang_api, name="api_giao_hang"),
    path("api/<str:ma_don_hang>/", views.tra_cuu_don_hang_api, name="api_chi_tiet"),
    path("<str:ma_don_hang>/sua/", views.sua_don_hang, name="sua"),
    path("<str:ma_don_hang>/huy/", views.huy_don_hang, name="huy"),
    path("<str:ma_don_hang>/xac-nhan-da-nhan/", views.xac_nhan_da_nhan, name="xac_nhan_da_nhan"),
    path("<str:ma_don_hang>/tra-hang/huong-dan/", views.huong_dan_tra_hang, name="huong_dan_tra_hang"),
    path("<str:ma_don_hang>/tra-hang/theo-doi/", views.theo_doi_yeu_cau_tra, name="theo_doi_yeu_cau_tra"),
    path("<str:ma_don_hang>/tra-hang/", views.yeu_cau_tra_hang, name="yeu_cau_tra_hang"),
    path("nhan-vien/<str:ma_don_hang>/xu-ly/", views.nhan_vien_xu_ly_don_hang, name="nhan_vien_xu_ly_don"),
    path("nhan-vien/<str:ma_don_hang>/giao-hang/", views.nhan_vien_cap_nhat_giao_hang, name="nhan_vien_cap_nhat_giao_hang"),
    path(
        "<str:ma_don_hang>/",
        views.chi_tiet_don_hang,
        name="chi_tiet",
    ),
]
