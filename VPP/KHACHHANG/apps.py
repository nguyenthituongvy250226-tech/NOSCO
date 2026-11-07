from django.apps import AppConfig


class KhachhangConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'KHACHHANG'

    def ready(self):
        import KHACHHANG.signals