from django.contrib import admin
from django.urls import path, include
from SANPHAM import views
from DONHANG.views import thong_tin_tai_khoan

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.base, name="base"),
    path("home", views.home, name="home"),
    path("tai-khoan/", thong_tin_tai_khoan, name="thong_tin_tai_khoan"),
    path("don-hang/", include("DONHANG.urls_donhang")),

]
