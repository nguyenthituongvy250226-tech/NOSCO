from django.urls import path
from . import views

app_name = 'CHECKOUT'

urlpatterns = [
    path('', views.checkout, name='checkout'),
    path(  'dat-hang-thanh-cong/', views.xem_trang_thanh_cong, name='xem_trang_thanh_cong' ),
]