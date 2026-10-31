
from django.urls import path
from . import views

app_name = "thanhtoan"

urlpatterns = [
    path("", views.trang_thanh_toan, name="trang_thanh_toan"),
]
