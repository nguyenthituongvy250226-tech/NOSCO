import hashlib
import hmac
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from uuid import uuid4
from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo






from django.conf import settings
from .models import ThanhToan
logger = logging.getLogger(__name__)
def lay_ip_vnpay(ip_thuc_hien=None):
   return (
       getattr(settings, "VNPAY_QUERY_IP", "")
       or ip_thuc_hien
       or "127.0.0.1"
   )




def tao_url_thanh_toan(request, ma_giao_dich, so_tien):
   thoi_gian = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
   thoi_gian_vnpay = thoi_gian.strftime("%Y%m%d%H%M%S")


   thanh_toan = ThanhToan.objects.get(
       MaGiaoDich=ma_giao_dich,
       LoaiGiaoDich="ThanhToan",
   )


   thanh_toan.ThoiGianTaoVNPay = thoi_gian_vnpay
   thanh_toan.save(update_fields=["ThoiGianTaoVNPay"])


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
       "vnp_CreateDate": thoi_gian_vnpay,
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




def kiem_tra_chu_ky_phan_hoi_querydr_vnpay(params):
   cac_truong_bat_buoc = [
       "vnp_ResponseId",
       "vnp_ResponseCode",
       "vnp_TmnCode",
       "vnp_TxnRef",
       "vnp_Amount",
       "vnp_OrderInfo",
   ]


   if not all(key in params for key in cac_truong_bat_buoc):
       return False


   cac_truong_ky = [
       "vnp_ResponseId",
       "vnp_Command",
       "vnp_ResponseCode",
       "vnp_Message",
       "vnp_TmnCode",
       "vnp_TxnRef",
       "vnp_Amount",
       "vnp_BankCode",
       "vnp_PayDate",
       "vnp_TransactionNo",
       "vnp_TransactionType",
       "vnp_TransactionStatus",
       "vnp_OrderInfo",
       "vnp_PromotionCode",
       "vnp_PromotionAmount",
   ]


   chuoi_ky = "|".join(
       str(params.get(key, ""))
       for key in cac_truong_ky
   )


   chu_ky_tinh = hmac.new(
       settings.VNPAY_HASH_SECRET.encode("utf-8"),
       chuoi_ky.encode("utf-8"),
       hashlib.sha512,
   ).hexdigest()


   chu_ky_nhan = params.get("vnp_SecureHash", "")


   return hmac.compare_digest(chu_ky_tinh, chu_ky_nhan)




def truy_van_giao_dich_vnpay(
   giao_dich_goc,
   nguoi_thuc_hien,
   ip_thuc_hien,
):
   """
   Truy vấn giao dịch VNPay, không gửi yêu cầu hoàn tiền.
   """
   ip_thuc_hien = lay_ip_vnpay(ip_thuc_hien)


   if not giao_dich_goc.MaGiaoDich:
       raise ValueError("Thiếu mã giao dịch gốc.")


   if not giao_dich_goc.ThoiGianTaoVNPay:
       raise ValueError("Thiếu thời gian giao dịch VNPay gốc.")


   if not settings.VNPAY_TMN_CODE or not settings.VNPAY_HASH_SECRET:
       raise ValueError("Chưa cấu hình thông tin kết nối VNPay.")


   thoi_gian = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))


   params = {
       "vnp_RequestId": uuid4().hex,
       "vnp_Version": "2.1.0",
       "vnp_Command": "querydr",
       "vnp_TmnCode": settings.VNPAY_TMN_CODE,
       "vnp_TxnRef": giao_dich_goc.MaGiaoDich,
       "vnp_OrderInfo": (
           f"Truy van giao dich {giao_dich_goc.MaGiaoDich}"
       ),
       "vnp_TransactionDate": giao_dich_goc.ThoiGianTaoVNPay,
       "vnp_CreateDate": thoi_gian.strftime("%Y%m%d%H%M%S"),
       "vnp_IpAddr": ip_thuc_hien,
   }


   cac_truong_ky = [
       "vnp_RequestId",
       "vnp_Version",
       "vnp_Command",
       "vnp_TmnCode",
       "vnp_TxnRef",
       "vnp_TransactionDate",
       "vnp_CreateDate",
       "vnp_IpAddr",
       "vnp_OrderInfo",
   ]


   chuoi_ky = "|".join(
       params[key] for key in cac_truong_ky
   )


   params["vnp_SecureHash"] = hmac.new(
       settings.VNPAY_HASH_SECRET.encode("utf-8"),
       chuoi_ky.encode("utf-8"),
       hashlib.sha512,
   ).hexdigest()
   logger.warning(
       "VNPay QueryDR request: %s",
       {
           key: params.get(key)
           for key in [
               "vnp_RequestId",
               "vnp_Version",
               "vnp_Command",
               "vnp_TmnCode",
               "vnp_TxnRef",
               "vnp_TransactionDate",
               "vnp_CreateDate",
               "vnp_IpAddr",
               "vnp_OrderInfo",
           ]
       },
   )


   request = Request(
       "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction",
       data=json.dumps(params).encode("utf-8"),
       headers={"Content-Type": "application/json"},
       method="POST",
   )


   try:
       with urlopen(request, timeout=30) as response:
           du_lieu_tra_ve = response.read().decode("utf-8")


       phan_hoi = json.loads(du_lieu_tra_ve)


       if not isinstance(phan_hoi, dict):
           raise ValueError("Dữ liệu phản hồi VNPay không hợp lệ.")


       logger.warning(
           "VNPay QueryDR response: %s",
           {
               key: phan_hoi.get(key)
               for key in [
               "vnp_ResponseId",
               "vnp_Command",
               "vnp_ResponseCode",
               "vnp_Message",
               "vnp_TmnCode",
               "vnp_TxnRef",
               "vnp_Amount",
               "vnp_BankCode",
               "vnp_PayDate",
               "vnp_TransactionNo",
               "vnp_TransactionType",
               "vnp_TransactionStatus",
               "vnp_OrderInfo",
               "vnp_PromotionCode",
               "vnp_PromotionAmount",
           ]
           },
       )


       ma_phan_hoi = str(phan_hoi.get("vnp_ResponseCode", ""))


       if ma_phan_hoi != "00":
           raise ValueError(
               f"VNPay QueryDR thất bại: "
               f"mã {ma_phan_hoi} - "
               f"{phan_hoi.get('vnp_Message', 'Không có thông báo')}"
           )


       if not kiem_tra_chu_ky_phan_hoi_querydr_vnpay(phan_hoi):
           raise ValueError("Chữ ký phản hồi QueryDR không hợp lệ.")


       if phan_hoi.get("vnp_TmnCode") != settings.VNPAY_TMN_CODE:
           raise ValueError("Mã merchant QueryDR không khớp.")


       if phan_hoi.get("vnp_TxnRef") != giao_dich_goc.MaGiaoDich:
           raise ValueError("Mã giao dịch QueryDR không khớp.")


       return phan_hoi


   except HTTPError as exc:
       noi_dung = exc.read().decode("utf-8", errors="replace")
       raise ValueError(
           f"VNPay trả về lỗi HTTP {exc.code}: {noi_dung}"
       ) from exc


   except URLError as exc:
       raise ValueError(
           f"Không kết nối được VNPay: {exc.reason}"
       ) from exc


   except json.JSONDecodeError as exc:
       raise ValueError(
           "VNPay trả về dữ liệu QueryDR không đúng định dạng JSON."
       ) from exc

