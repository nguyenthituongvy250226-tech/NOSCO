from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services import kiem_tra_va_tinh_voucher


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