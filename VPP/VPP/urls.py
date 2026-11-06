
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from SANPHAM import views
from GIOHANG import views as giohang_views
from CHECKOUT import views as checkout_views
from DONHANG.views import thong_tin_tai_khoan


urlpatterns = [
    path("admin/", admin.site.urls),
    # Giỏ hàng
    path('gio-hang/', include('GIOHANG.urls')),

    # Checkout
    path('checkout/', include('CHECKOUT.urls')),

    # Giao diện chung
    path("", views.base, name="base"),
    path("home", views.home, name="home"),

    path("bai-viet/", views.danh_sach_bai_viet, name="danh_sach_bai_viet"),
    path("ve-chung-toi/", views.ve_chung_toi, name="ve_chung_toi"),

    path("tai-khoan/", thong_tin_tai_khoan, name="thong_tin_tai_khoan"),
path("khach-hang/", include("KHACHHANG.urls")),
    path("don-hang/", include("DONHANG.urls_donhang")),



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
