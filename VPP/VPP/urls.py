from django.contrib import admin
from django.urls import path
from SANPHAM import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.base, name="base"),
    path("home", views.home, name="home"),

]