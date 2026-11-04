
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from SANPHAM import views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Giao diện chung
    path("", views.base, name="base"),
    path("home", views.home, name="home"),
    path("bai-viet/", views.danh_sach_bai_viet, name="danh_sach_bai_viet"),
    path("ve-chung-toi/", views.ve_chung_toi, name="ve_chung_toi"),

    # Module sản phẩm
    path("san-pham/", include("SANPHAM.urls")),
# Thanh toan & Khuyen mai
    path("thanh-toan/", include("THANHTOAN.urls")),
    path("khuyen-mai/", include("KHUYENMAI.urls")),
]

# Phục vụ ảnh tải lên khi chạy ở chế độ phát triển
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )