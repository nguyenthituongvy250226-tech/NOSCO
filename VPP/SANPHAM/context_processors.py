from .models import DanhMucSanPham

def danh_muc_menu(request):
    return {
        "danh_muc_menu": DanhMucSanPham.objects.using("sanpham").all()
    }