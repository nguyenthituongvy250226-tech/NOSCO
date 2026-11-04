
from django.contrib import admin
from django.urls import path, include
from SANPHAM import views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Trang giao diện chung và trang chủ
    path("", views.base, name="base"),
    path("home", views.home, name="home"),

    # Chức năng khách hàng
    path(
        "khach_hang/",
        include("KHACHHANG.urls")
    ),
]