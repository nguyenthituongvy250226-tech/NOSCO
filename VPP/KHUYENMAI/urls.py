
from django.urls import path
from . import views

app_name = "khuyenmai"

urlpatterns = [
    path("", views.trang_khuyen_mai, name="trang_khuyen_mai"),
]
