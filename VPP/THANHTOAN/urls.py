from django.urls import path
from . import views

app_name = 'THANHTOAN'

urlpatterns = [
    path('', views.trang_thanh_toan, name='trang_thanh_toan'),
    path('ket-qua/', views.ket_qua_thanh_toan, name='ket_qua_thanh_toan'),
    path('don-hang/<str:ma_don_hang>/thanh-toan-lai/', views.thanh_toan_lai, name='thanh_toan_lai'),
    path('thu-vnpay/', views.thanh_toan_thu, name='thanh_toan_thu'),
    path('ipn/', views.ipn_vnpay, name='ipn_vnpay'),
]