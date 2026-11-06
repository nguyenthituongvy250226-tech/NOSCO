from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect, render

from DONHANG.services import (
    DuLieuDonHangKhongHopLe,
    tao_don_hang,
    tinh_phi_van_chuyen,
)
from GIOHANG.views import (
    bo_sung_thong_tin_san_pham,
    lay_gio_hang,
    lay_thong_tin_bien_the,
)
from KHACHHANG.models import HoSoKhachHang, SoDiaChi
from THANHTOAN.models import ThanhToan
from THANHTOAN.services import tao_thanh_toan_cho_don
from THANHTOAN.vnpay import tao_url_thanh_toan


def checkout(request):
    cac_phuong_thuc_thanh_toan = ThanhToan._meta.get_field(
        "PhuongThucThanhToan"
    ).choices
    gio_hang = lay_gio_hang(request)
    danh_sach = list(
        gio_hang.chi_tiet.filter(trang_thai_chon=True)
        .order_by("ma_chi_tiet_gio_hang")
    )

    if not danh_sach:
        messages.warning(request, "Bạn chưa chọn sản phẩm nào để đặt hàng.")
        return redirect("xem_gio_hang")

    danh_sach = bo_sung_thong_tin_san_pham(danh_sach)
    ma_khach_hang = request.session.get("ma_khach_hang")
    ho_so = HoSoKhachHang.objects.filter(
        MaHoSo=ma_khach_hang,
        MaNguoiDung=request.nguoi_dung,
    ).first()
    if ho_so is None:
        messages.error(request, "Không tìm thấy hồ sơ khách hàng của bạn.")
        return redirect("KHACHHANG:ho_so_ca_nhan")

    dia_chi = SoDiaChi.objects.filter(
        MaKhachHang=ho_so,
    ).order_by("-MacDinh", "TenNguoiNhan").first()

    if request.method == "POST":
        if dia_chi is None:
            messages.warning(request, "Vui lòng thêm địa chỉ nhận hàng trước khi đặt hàng.")
            return redirect("KHACHHANG:so_dia_chi")

        phuong_thuc = request.POST.get("phuong_thuc_thanh_toan", "COD")
        if phuong_thuc not in dict(cac_phuong_thuc_thanh_toan):
            messages.error(request, "Vui lòng chọn phương thức thanh toán hợp lệ.")
            return redirect("checkout")
        if phuong_thuc != "COD" and phuong_thuc != "VNPAY":
            messages.error(
                request,
                "Phương thức thanh toán này chưa được kết nối với cổng thanh toán.",
            )
            return redirect("checkout")
        if phuong_thuc != "COD" and not (
            settings.VNPAY_TMN_CODE and settings.VNPAY_HASH_SECRET
        ):
            messages.error(
                request,
                "Thanh toán VNPay chưa được cấu hình. Vui lòng chọn COD hoặc thử lại sau.",
            )
            return redirect("checkout")

        ghi_chu = request.POST.get("ghi_chu", "").strip()
        if len(ghi_chu) > 300:
            messages.error(request, "Ghi chú đơn hàng không được vượt quá 300 ký tự.")
            return redirect("checkout")

        items = []
        for item in danh_sach:
            san_pham = lay_thong_tin_bien_the(item.ma_bien_the_sp)
            if san_pham is None:
                messages.error(
                    request,
                    f"Sản phẩm {item.ma_bien_the_sp} không còn khả dụng.",
                )
                return redirect("xem_gio_hang")
            items.append({
                "ma_bien_the": item.ma_bien_the_sp,
                "so_luong": item.so_luong,
                "don_gia": str(san_pham["don_gia"]),
            })

        try:
            with transaction.atomic():
                don = tao_don_hang({
                    "ma_khach_hang": ho_so.MaHoSo,
                    "ma_dia_chi": dia_chi.MaDiaChi,
                    "ten_nguoi_nhan": dia_chi.TenNguoiNhan,
                    "sdt_nguoi_nhan": dia_chi.SoDienThoai,
                    "dia_chi_nhan_hang": dia_chi.DiaChi,
                    "ghi_chu": ghi_chu,
                    "phi_van_chuyen": str(tinh_phi_van_chuyen(dia_chi.DiaChi)),
                    "items": items,
                })
                thanh_toan = tao_thanh_toan_cho_don(don, phuong_thuc)
                if phuong_thuc != "COD":
                    url_thanh_toan = tao_url_thanh_toan(
                        request,
                        thanh_toan.MaGiaoDich,
                        thanh_toan.SoTienThanhToan,
                    )
                gio_hang.chi_tiet.filter(trang_thai_chon=True).delete()
        except DuLieuDonHangKhongHopLe as exc:
            messages.error(request, str(exc) or "Không thể tạo đơn hàng.")
            return redirect("checkout")

        if phuong_thuc != "COD":
            return redirect(url_thanh_toan)

        messages.success(
            request,
            f"Đặt hàng thành công. Mã đơn hàng: {don.ma_don_hang}. "
            "Bạn sẽ thanh toán khi nhận hàng.",
        )
        return redirect("DONHANG:danh_sach")

    tam_tinh = sum((item.thanh_tien for item in danh_sach), Decimal("0"))
    dia_chi_giao = dia_chi.DiaChi if dia_chi else ""
    phi_van_chuyen = tinh_phi_van_chuyen(dia_chi_giao)
    mien_phi = phi_van_chuyen == Decimal("0")

    return render(request, "CHECKOUT/checkout.html", {
        "danh_sach": danh_sach,
        "tam_tinh": tam_tinh,
        "dia_chi": dia_chi,
        "phi_van_chuyen": phi_van_chuyen,
        "tong_tien": tam_tinh + phi_van_chuyen,
        "mien_phi": mien_phi,
        "phuong_thuc_thanh_toan": (
            request.POST.get("phuong_thuc_thanh_toan", "COD")
            if request.method == "POST" else "COD"
        ),
        "cac_phuong_thuc_thanh_toan": cac_phuong_thuc_thanh_toan,
    })
