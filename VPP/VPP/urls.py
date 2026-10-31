
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("thanh_toan/", include("THANHTOAN.urls")),
    path("khuyen_mai/", include("KHUYENMAI.urls")),
]
