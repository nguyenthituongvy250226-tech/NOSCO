
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Max
from .models import KhuyenMai, ChiTietKhuyenMai
from .services import kiem_tra_va_tinh_voucher

from SANPHAM.models import SanPham


@require_POST
def ap_dung_voucher(request):
    ma_voucher = request.POST.get("ma_voucher", "")
    tong_tien_hang = request.POST.get("tong_tien_hang", "0")
    hang_thanh_vien = request.POST.get("hang_thanh_vien")

    try:
        ket_qua = kiem_tra_va_tinh_voucher(
            ma_voucher=ma_voucher,
            tong_tien_hang=tong_tien_hang,
            hang_thanh_vien=hang_thanh_vien,
        )
    except (ValueError, TypeError):
        return JsonResponse({
            "hop_le": False,
            "thong_bao": "Thông tin đơn hàng không hợp lệ.",
        }, status=400)

    return JsonResponse({
        "hop_le": ket_qua["hop_le"],
        "thong_bao": ket_qua["thong_bao"],
        "ma_voucher": (
            ket_qua["voucher"].MaVoucher
            if ket_qua["voucher"] else None
        ),
        "so_tien_giam": str(ket_qua["so_tien_giam"]),
    })


def popup_voucher(request):
    return render(request, "popup_voucher.html")


# TRANG DANH SÁCH KHUYẾN MÃI

def danh_sach_khuyen_mai(request):
    hien_tai = timezone.now()

    danh_sach = KhuyenMai.objects.filter(
        NgayKetThuc__gte=hien_tai
    ).order_by("NgayBatDau")

    cac_chuong_trinh = []

    for km in danh_sach:
        if km.NgayBatDau > hien_tai:
            trang_thai = "SapDienRa"
        else:
            trang_thai = "DangDienRa"

        chi_tiet = ChiTietKhuyenMai.objects.filter(
            MaKhuyenMai=km,
            TrangThai=True
        )

        so_san_pham = chi_tiet.count()

        muc_giam_cao_nhat = chi_tiet.aggregate(
            muc_giam=Max("PhanTramGiam")
        )["muc_giam"] or 0

        cac_chuong_trinh.append({
            "khuyen_mai": km,
            "trang_thai": trang_thai,
            "so_san_pham": so_san_pham,
            "muc_giam_cao_nhat": muc_giam_cao_nhat,
        })

    return render(request, "danh_sach_khuyen_mai.html", {
        "danh_sach_khuyen_mai": cac_chuong_trinh,
    })


# TRANG CHI TIẾT KHUYẾN MÃI
def chi_tiet_khuyen_mai(request, ma_khuyen_mai):
    khuyen_mai = get_object_or_404(
        KhuyenMai,
        MaKhuyenMai=ma_khuyen_mai
    )

    chi_tiet = ChiTietKhuyenMai.objects.filter(
        MaKhuyenMai=khuyen_mai,
        TrangThai=True
    )

    ma_san_pham = [
        item.MaSanPham for item in chi_tiet
    ]

    # Lấy sản phẩm từ database SANPHAM
    danh_sach_sp = SanPham.objects.using("sanpham").filter(
        ma_san_pham__in=ma_san_pham,
        trang_thai_ban="Đang bán"
    ).prefetch_related("bien_the")

    san_pham_dict = {
        sp.ma_san_pham: sp for sp in danh_sach_sp
    }

    danh_sach_hien_thi = []
    anh_san_pham = {
        "SP001": "butviet.png",
        "SP005": "product-pastel-pens.jpg",
        "SP002": "product-pencils.jpg",
        "SP0017": "product-pastel-pens1.jpg",
        "SP0014": "about-products.jpg",
        "SP004": "dungcuhoctap.png",
        "SP0016": "about-products.jpg",
        "SP0029": "tips_chon_but.jpg",
        "SP006": "product-pastel-pens1.jpg",
        "SP0012": "dungcuhoctap.png",
        "SP0010": "product-sticky-notes.jpg",
        "SP0021": "giayghichu.png",
        "SP0027": "dungcuhoctap.png",
        "SP0028": "product-notebook.jpg",
        "SP0025": "product-notebook1.jpg",
    }

    for item in chi_tiet:
        sp = san_pham_dict.get(item.MaSanPham)

        if not sp:
            continue

        bien_the = list(sp.bien_the.all())

        if not bien_the:
            continue

        danh_sach_hien_thi.append({
            "ma_san_pham": sp.ma_san_pham,
            "ten_san_pham": sp.ten_san_pham,
            "gia_goc": bien_the[0].gia_ban,
            "gia_khuyen_mai": item.GiaKhuyenMai,
            "gia_goc_hien_thi": f"{bien_the[0].gia_ban:,.0f}".replace(",", "."),
            "gia_khuyen_mai_hien_thi": f"{item.GiaKhuyenMai:,.0f}".replace(",", "."),
            "phan_tram_giam": item.PhanTramGiam,
            "hinh_anh": anh_san_pham.get(sp.ma_san_pham, "about-products.jpg"),
        })

    return render(request, "chi_tiet_khuyen_mai.html", {
        "khuyen_mai": khuyen_mai,
        "danh_sach_san_pham": danh_sach_hien_thi,
    })
