
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Max
from .models import KhuyenMai, ChiTietKhuyenMai
from .services import kiem_tra_va_tinh_voucher

from SANPHAM.models import SanPham
from SANPHAM.models import SanPham, SanPhamYeuThich

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
    ma_khach_hang = request.session.get("ma_khach_hang")

    danh_sach_yeu_thich = set()

    if ma_khach_hang:
        danh_sach_yeu_thich = set(
            SanPhamYeuThich.objects.filter(
                ma_khach_hang=ma_khach_hang
            ).values_list(
                "san_pham_id",
                flat=True
            )
        )

    chi_tiet = ChiTietKhuyenMai.objects.filter(
        MaKhuyenMai=khuyen_mai,
        TrangThai=True
    )

    # Lấy mã sản phẩm trong chương trình khuyến mãi
    ma_san_pham = [
        item.MaSanPham for item in chi_tiet
    ]

    # Truy vấn sản phẩm từ database SANPHAM
    danh_sach_sp = (
        SanPham.objects.using("sanpham")
        .filter(
            ma_san_pham__in=ma_san_pham,
            trang_thai_ban="Đang bán"
        )
        .select_related("thuong_hieu")
        .prefetch_related("bien_the__hinh_anh")
    )

    san_pham_dict = {
        sp.ma_san_pham: sp for sp in danh_sach_sp
    }

    danh_sach_hien_thi = []

    for item in chi_tiet:
        sp = san_pham_dict.get(item.MaSanPham)

        if not sp:
            continue

        # Lấy giá bán thấp nhất trong các biến thể
        bien_the = list(sp.bien_the.all())
        # Xác định sản phẩm có thể mua trực tiếp hay không
        co_the_mua_truc_tiep = len(bien_the) == 1

        bien_the_duy_nhat = (
            bien_the[0] if co_the_mua_truc_tiep else None
        )
        gia_goc = min(
            (bt.gia_ban for bt in bien_the),
            default=None
        )

        # Tính giá khuyến mãi
        if item.GiaKhuyenMai is not None:
            gia_khuyen_mai = item.GiaKhuyenMai
        elif gia_goc is not None and item.PhanTramGiam is not None:
            gia_khuyen_mai = gia_goc * (
                1 - item.PhanTramGiam / 100
            )
        else:
            gia_khuyen_mai = None

        # Lấy ảnh đại diện
        ds_anh = [
            anh
            for bt in bien_the
            for anh in bt.hinh_anh.all()
            if anh.duong_dan_anh
        ]

        anh_dai_dien = next(
            (anh for anh in ds_anh if anh.anh_dai_dien),
            ds_anh[0] if ds_anh else None
        )

        hinh_anh = (
            anh_dai_dien.duong_dan_anh.url
            if anh_dai_dien else ""
        )

        danh_sach_hien_thi.append({
            "ma_san_pham": sp.ma_san_pham,
            "ten_san_pham": sp.ten_san_pham,
            "co_the_mua_truc_tiep": co_the_mua_truc_tiep,
            "bien_the_duy_nhat": bien_the_duy_nhat,
            "thuong_hieu": sp.thuong_hieu.ten_thuong_hieu,
            "so_luong_da_ban": getattr(
                sp, "so_luong_da_ban", 0
            ),
            "gia_goc_hien_thi": (
                f"{gia_goc:,.0f}".replace(",", ".")
                if gia_goc is not None else None
            ),
            "gia_khuyen_mai_hien_thi": (
                f"{gia_khuyen_mai:,.0f}".replace(",", ".")
                if gia_khuyen_mai is not None else None
            ),

            "phan_tram_giam": item.PhanTramGiam,
            "hinh_anh": hinh_anh,

        })

    return render(
        request,
        "chi_tiet_khuyen_mai.html",
        {
            "khuyen_mai": khuyen_mai,
            "danh_sach_san_pham": danh_sach_hien_thi,
            "danh_sach_yeu_thich": danh_sach_yeu_thich,
        }
    )


