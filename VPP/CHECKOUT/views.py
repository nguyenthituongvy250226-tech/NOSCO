from decimal import Decimal

from django.contrib import messages
from django.shortcuts import render, redirect

from GIOHANG.views import lay_gio_hang, bo_sung_thong_tin_san_pham

# Tạm thời: m đổi theo chính sách thật của NOSCO
PHI_VAN_CHUYEN_TIEU_CHUAN = Decimal("30000")
KHU_VUC_MIEN_PHI = "Đà Nẵng"
def checkout(request):
    gio_hang = lay_gio_hang(request)

    danh_sach = list(
        gio_hang.chi_tiet.filter(trang_thai_chon=True)
        .order_by("ma_chi_tiet_gio_hang")
    )

    # Chưa chọn sản phẩm nào thì đưa về giỏ hàng
    if not danh_sach:
        messages.warning(request, "Bạn chưa chọn sản phẩm nào để đặt hàng.")
        return redirect("xem_gio_hang")

    danh_sach = bo_sung_thong_tin_san_pham(danh_sach)

    tam_tinh = sum((i.thanh_tien for i in danh_sach), Decimal("0"))
    tam_tinh = sum((i.thanh_tien for i in danh_sach), Decimal("0"))

    # Dữ liệu mẫu, sau này lấy từ app khách hàng
    dia_chi = {
        "ho_ten": "Nguyễn Văn A",
        "so_dien_thoai": "0900 000 000",
        "dia_chi": "123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng",
    }

    # Miễn phí nếu địa chỉ nhận hàng ở Đà Nẵng
    mien_phi = KHU_VUC_MIEN_PHI in dia_chi["dia_chi"]
    phi_van_chuyen = Decimal("0") if mien_phi else PHI_VAN_CHUYEN_TIEU_CHUAN

    return render(request, "CHECKOUT/checkout.html", {
        "danh_sach": danh_sach,
        "tam_tinh": tam_tinh,
        "dia_chi": dia_chi,
        "phi_van_chuyen": phi_van_chuyen,
        "tong_tien": tam_tinh + phi_van_chuyen,
        "mien_phi": mien_phi,
    })

