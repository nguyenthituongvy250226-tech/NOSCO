from django.urls import path
from . import views

app_name = "sanpham"

urlpatterns = [
    path(
        "",
        views.danh_sach_san_pham,
        name="danh_sach_san_pham"
    ),
]