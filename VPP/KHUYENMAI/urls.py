from django.urls import path
from . import views

app_name = "khuyenmai"

urlpatterns = [
    path("ap-dung/", views.ap_dung_voucher, name="ap_dung_voucher"),
    path("popup/", views.popup_voucher, name="popup_voucher"),
]