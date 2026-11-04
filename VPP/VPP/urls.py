
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from SANPHAM import views
from DONHANG.views import thong_tin_tai_khoan

urlpatterns = [
    path("admin/", admin.site.urls),

    # Giao diện chung
    path("", views.base, name="base"),
    path("home", views.home, name="home"),
    path("tai-khoan/", thong_tin_tai_khoan, name="thong_tin_tai_khoan"),
    path("don-hang/", include("DONHANG.urls_donhang")),

    # Module sản phẩm
    path("san-pham/", include("SANPHAM.urls")),
]

# Phục vụ ảnh tải lên khi chạy ở chế độ phát triển
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
