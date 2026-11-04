from django.contrib import admin
from django.urls import path
from SANPHAM import views
from GIOHANG import views as giohang_views
from CHECKOUT import views as checkout_views
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.base, name="base"),
    path("home", views.home, name="home"),
    path('gio-hang/', giohang_views.xem_gio_hang, name='xem_gio_hang'),

    path('gio-hang/them-vao-gio/', giohang_views.them_vao_gio, name='them_vao_gio'),

    path('gio-hang/tang-so-luong/<str:id>/', giohang_views.tang_so_luong, name='tang_so_luong'),

    path('gio-hang/giam-so-luong/<str:id>/', giohang_views.giam_so_luong, name='giam_so_luong'),

    path('gio-hang/cap-nhat-so-luong/<str:id>/', giohang_views.cap_nhat_so_luong, name='cap_nhat_so_luong'),

    path('gio-hang/xoa-san-pham/<str:id>/', giohang_views.xoa_san_pham, name='xoa_san_pham'),

    path('gio-hang/chon-san-pham/<str:id>/', giohang_views.chon_san_pham, name='chon_san_pham'),

    path('gio-hang/chon-tat-ca/', giohang_views.chon_tat_ca, name='chon_tat_ca'),
    path('gio-hang/xoa-da-chon/', giohang_views.xoa_da_chon, name='xoa_da_chon'),
    path('checkout/', checkout_views.checkout, name='checkout'),
    path('gio-hang/chia-se/', giohang_views.tao_chia_se, name='tao_chia_se'),
    path('gio-hang/chia-se/<str:ma>/', giohang_views.trang_chia_se, name='trang_chia_se'),
    path('gio-hang/nhan/<str:ma>/', giohang_views.nhan_gio_hang, name='nhan_gio_hang'),


]
