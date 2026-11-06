from django.urls import path
from . import views

app_name = 'GIOHANG'

urlpatterns = [
    # Xem giỏ hàng
    path('', views.xem_gio_hang, name='xem_gio_hang'),

    # Thêm sản phẩm vào giỏ
    path('them-vao-gio/', views.them_vao_gio, name='them_vao_gio'),

    # Cập nhật số lượng
    path('tang-so-luong/<str:id>/', views.tang_so_luong, name='tang_so_luong'),
    path('giam-so-luong/<str:id>/', views.giam_so_luong, name='giam_so_luong'),
    path('cap-nhat-so-luong/<str:id>/', views.cap_nhat_so_luong, name='cap_nhat_so_luong'),

    # Xóa sản phẩm
    path('xoa-san-pham/<str:id>/', views.xoa_san_pham, name='xoa_san_pham'),
    path('xoa-da-chon/', views.xoa_da_chon, name='xoa_da_chon'),

    # Chọn sản phẩm
    path('chon-san-pham/<str:id>/', views.chon_san_pham, name='chon_san_pham'),
    path('chon-tat-ca/', views.chon_tat_ca, name='chon_tat_ca'),

    # Chia sẻ giỏ hàng
    path('chia-se/', views.tao_chia_se, name='tao_chia_se'),
    path('chia-se/<str:ma>/', views.trang_chia_se, name='trang_chia_se'),
    path('nhan/<str:ma>/', views.nhan_gio_hang, name='nhan_gio_hang'),
]