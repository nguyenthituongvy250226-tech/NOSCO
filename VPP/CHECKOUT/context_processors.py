
from .models import DanhMucSanPham


def danh_muc_menu(request):
    danh_muc_list = DanhMucSanPham.objects.all()

    return {
        "danh_muc_menu": danh_muc_list
    }
