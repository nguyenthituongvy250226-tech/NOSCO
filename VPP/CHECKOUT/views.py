
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from GIOHANG.views import (
    lay_gio_hang,
    bo_sung_thong_tin_san_pham,
)


# ==========================================
# CẤU HÌNH PHÍ VẬN CHUYỂN
# ==========================================

PHI_VAN_CHUYEN_TIEU_CHUAN = Decimal("30000")
KHU_VUC_MIEN_PHI = "Đà Nẵng"


# ==========================================
# TRANG THANH TOÁN
# ==========================================

@require_http_methods(["GET", "POST"])
def checkout(request):

    # Lấy giỏ hàng hiện tại
    gio_hang = lay_gio_hang(request)

    # Chỉ lấy những sản phẩm đã được chọn
    danh_sach = list(
        gio_hang.chi_tiet.filter(
            trang_thai_chon=True
        ).order_by("ma_chi_tiet_gio_hang")
    )

    # Kiểm tra giỏ hàng có sản phẩm được chọn hay không
    if not danh_sach:
        messages.warning(
            request,
            "Bạn chưa chọn sản phẩm nào để thanh toán."
        )
        return redirect("GIOHANG:xem_gio_hang")

    # Bổ sung thông tin sản phẩm từ app SANPHAM
    danh_sach = bo_sung_thong_tin_san_pham(danh_sach)

    # Kiểm tra sản phẩm có còn tồn tại hay không
    san_pham_khong_hop_le = [
        item for item in danh_sach
        if item.don_gia <= 0 or item.so_luong_ton < item.so_luong
    ]

    if san_pham_khong_hop_le:
        messages.error(
            request,
            "Một số sản phẩm đã hết hàng hoặc không còn hợp lệ. "
            "Vui lòng kiểm tra lại giỏ hàng."
        )
        return redirect("GIOHANG:xem_gio_hang")

    # ======================================
    # TÍNH TIỀN
    # ======================================

    tam_tinh = sum(
        (
            Decimal(str(item.thanh_tien))
            for item in danh_sach
        ),
        Decimal("0")
    )

    # ======================================
    # THÔNG TIN NHẬN HÀNG TẠM THỜI
    # Sau này kết nối với app khách hàng
    # ======================================

    dia_chi = {
        "ho_ten": "Nguyễn Văn A",
        "so_dien_thoai": "0900 000 000",
        "dia_chi": "123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng",
    }

    # ======================================
    # PHÍ VẬN CHUYỂN
    # ======================================

    mien_phi = (
        KHU_VUC_MIEN_PHI.casefold()
        in dia_chi["dia_chi"].casefold()
    )

    phi_van_chuyen = (
        Decimal("0")
        if mien_phi
        else PHI_VAN_CHUYEN_TIEU_CHUAN
    )

    tong_tien = tam_tinh + phi_van_chuyen

    # ======================================
    # XỬ LÝ FORM POST
    # ======================================

    if request.method == "POST":

        ghi_chu = request.POST.get("ghi_chu", "").strip()
        khung_gio = request.POST.get(
            "khung_gio",
            "hanh_chinh"
        )

        van_chuyen = request.POST.get(
            "van_chuyen",
            "tieu_chuan"
        )

        # Kiểm tra khung giờ giao hàng
        khung_gio_hop_le = [
            "hanh_chinh",
            "sang",
            "chieu",
        ]

        if khung_gio not in khung_gio_hop_le:
            messages.error(
                request,
                "Khung giờ giao hàng không hợp lệ."
            )
            return redirect("CHECKOUT:checkout")

        # Kiểm tra phương thức vận chuyển
        if van_chuyen != "tieu_chuan":
            messages.error(
                request,
                "Phương thức vận chuyển không hợp lệ."
            )
            return redirect("CHECKOUT:checkout")

        # Chưa tạo đơn hàng vì chưa kết nối model đơn hàng
        messages.info(
            request,
            "Thông tin thanh toán đã được kiểm tra. "
            "Chức năng tạo đơn hàng đang chờ tích hợp."
        )

        return redirect("CHECKOUT:checkout")

    # ======================================
    # DỮ LIỆU TRUYỀN SANG TEMPLATE
    # ======================================

    context = {
        "gio_hang": gio_hang,
        "danh_sach": danh_sach,
        "dia_chi": dia_chi,

        "tam_tinh": tam_tinh,
        "phi_van_chuyen": phi_van_chuyen,
        "tong_tien": tong_tien,

        "mien_phi": mien_phi,
    }

    return render(
        request,
        "CHECKOUT/checkout.html",
        context
    )
