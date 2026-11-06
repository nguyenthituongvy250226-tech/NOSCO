from django.db.models import Sum

from GIOHANG.models import ChiTietGioHang, GioHang

from .models import NguoiDung, ThongBao


def header_customer_indicators(request):
    ma_nguoi_dung = request.session.get("khachhang_ma_nguoi_dung")
    ma_khach_hang = request.session.get("ma_khach_hang")
    thong_bao_moi = ThongBao.objects.none()
    so_thong_bao_chua_doc = 0
    so_san_pham_trong_gio = 0

    if ma_nguoi_dung:
        nguoi_dung = NguoiDung.objects.filter(
            MaNguoiDung=ma_nguoi_dung,
            KichHoat=True,
        ).first()
        if nguoi_dung:
            thong_bao = ThongBao.objects.filter(MaNguoiNhan=nguoi_dung)
            so_thong_bao_chua_doc = thong_bao.filter(DaDoc=False).count()
            thong_bao_moi = thong_bao.order_by("-NgayTao")[:5]

    if ma_khach_hang:
        gio_hang_ids = GioHang.objects.filter(
            ma_khach_hang=ma_khach_hang,
        ).values("ma_gio_hang")
        so_san_pham_trong_gio = (
            ChiTietGioHang.objects.filter(gio_hang_id__in=gio_hang_ids)
            .aggregate(tong_so=Sum("so_luong"))["tong_so"]
            or 0
        )

    return {
        "header_thong_bao_moi": thong_bao_moi,
        "header_so_thong_bao_chua_doc": so_thong_bao_chua_doc,
        "header_so_san_pham_trong_gio": so_san_pham_trong_gio,
    }
