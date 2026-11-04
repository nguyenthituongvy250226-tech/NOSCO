import hashlib
import hmac
from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo


from django.conf import settings


def tao_url_thanh_toan(request, ma_giao_dich, so_tien):
    thoi_gian = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": settings.VNPAY_TMN_CODE,
        "vnp_Amount": str(int(so_tien * 100)),
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": str(ma_giao_dich),
        "vnp_OrderInfo": f"Thanh toan don hang {ma_giao_dich}",
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": request.build_absolute_uri("/thanh-toan/ket-qua/"),
        "vnp_IpAddr": request.META.get("REMOTE_ADDR", "127.0.0.1"),
        "vnp_CreateDate": thoi_gian.strftime("%Y%m%d%H%M%S"),
    }

    du_lieu_ky = urlencode(sorted(params.items()))

    chu_ky = hmac.new(
        settings.VNPAY_HASH_SECRET.encode("utf-8"),
        du_lieu_ky.encode("utf-8"),
        hashlib.sha512
    ).hexdigest()

    params["vnp_SecureHash"] = chu_ky

    return settings.VNPAY_PAYMENT_URL + "?" + urlencode(params)
def kiem_tra_chu_ky_vnpay(params):
    du_lieu = {
        key: value
        for key, value in params.items()
        if key not in ("vnp_SecureHash", "vnp_SecureHashType")
    }

    chu_ky_nhan = params.get("vnp_SecureHash", "")

    du_lieu_ky = urlencode(sorted(du_lieu.items()))

    chu_ky_tinh = hmac.new(
        settings.VNPAY_HASH_SECRET.encode("utf-8"),
        du_lieu_ky.encode("utf-8"),
        hashlib.sha512
    ).hexdigest()

    return hmac.compare_digest(chu_ky_tinh, chu_ky_nhan)