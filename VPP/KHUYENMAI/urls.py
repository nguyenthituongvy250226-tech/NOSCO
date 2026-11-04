
from django.urls import path
from . import views

app_name = "khuyenmai"

urlpatterns = [
    path("", views.danh_sach_khuyen_mai, name="danh_sach_khuyen_mai"),
    path("ap-dung/", views.ap_dung_voucher, name="ap_dung_voucher"),
    path("popup/", views.popup_voucher, name="popup_voucher"),
    path("<str:ma_khuyen_mai>/", views.chi_tiet_khuyen_mai, name="chi_tiet_khuyen_mai"),
]
