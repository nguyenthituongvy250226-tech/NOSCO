from django.shortcuts import render
from .models import SanPham


def danh_sach_san_pham(request):
    san_pham_queryset = (
        SanPham.objects
        .filter(trang_thai_ban="Đang bán")
        .select_related("danh_muc", "thuong_hieu")
        .prefetch_related("bien_the__hinh_anh")
    )

    danh_sach_san_pham = []

    for san_pham in san_pham_queryset:
        cac_bien_the = list(san_pham.bien_the.all())
        anh_dai_dien = None

        # Tìm ảnh đại diện của sản phẩm
        for bien_the in cac_bien_the:
            cac_anh = list(bien_the.hinh_anh.all())

            anh_dai_dien = next(
                (anh for anh in cac_anh if anh.anh_dai_dien),
                None
            )

            # Nếu chưa chọn ảnh đại diện, lấy ảnh đầu tiên
            if anh_dai_dien is None and cac_anh:
                anh_dai_dien = cac_anh[0]

            if anh_dai_dien is not None:
                break

        # Lấy giá thấp nhất trong các biến thể
        cac_gia = [
            bien_the.gia_ban
            for bien_the in cac_bien_the
        ]

        danh_sach_san_pham.append({
            "san_pham": san_pham,
            "anh_dai_dien": anh_dai_dien,
            "gia_thap_nhat": min(cac_gia) if cac_gia else None,
        })

    return render(
        request,
        "SANPHAM/giao_dien_thu.html",
        {"danh_sach_san_pham": danh_sach_san_pham}
    )