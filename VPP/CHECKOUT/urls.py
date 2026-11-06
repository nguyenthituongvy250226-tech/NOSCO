from django.urls import path
from . import views

app_name = 'CHECKOUT'

urlpatterns = [
    path('', views.checkout, name='checkout'),
]