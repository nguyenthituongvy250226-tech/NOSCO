from django.contrib import admin
from django.urls import path
from SANPHAM import views
from GIOHANG import views as giohang_views
from CHECKOUT import views as checkout_views
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.base, name="base"),
    path("home", views.home, name="home"),
    path('gio_hang/', giohang_views.xem_gio_hang, name='xem_gio_hang'),

    path('gio_hang/them_vao_gio/', giohang_views.them_vao_gio, name='them_vao_gio'),

    path('gio_hang/tang_so_luong/<str:id>/', giohang_views.tang_so_luong, name='tang_so_luong'),

    path('gio_hang/giam_so_luong/<str:id>/', giohang_views.giam_so_luong, name='giam_so_luong'),

    path('gio_hang/cap_nhat_so_luong/<str:id>/', giohang_views.cap_nhat_so_luong, name='cap_nhat_so_luong'),

    path('gio_hang/xoa_san_pham/<str:id>/', giohang_views.xoa_san_pham, name='xoa_san_pham'),

    path('gio_hang/chon_san_pham/<str:id>/', giohang_views.chon_san_pham, name='chon_san_pham'),

    path('gio_hang/chon_tat_ca/', giohang_views.chon_tat_ca, name='chon_tat_ca'),
    path('gio_hang/xoa_da_chon/', giohang_views.xoa_da_chon, name='xoa_da_chon'),
    path('checkout/', checkout_views.checkout, name='checkout'),


]
