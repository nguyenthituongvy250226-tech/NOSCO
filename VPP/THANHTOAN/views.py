

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import ThanhToan
from django.db import transaction
from .vnpay import tao_url_thanh_toan, kiem_tra_chu_ky_vnpay
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from DONHANG.models import DonHang
from DONHANG.services import het_han_don_chua_thanh_toan
from .services import tao_thanh_toan_cho_don


def cap_nhat_giao_dich_vnpay(params):
   if not kiem_tra_chu_ky_vnpay(params):
       return None, "Invalid signature", "97", False


   required = (
       "vnp_TxnRef",
       "vnp_Amount",
       "vnp_ResponseCode",
       "vnp_TransactionStatus",
   )
   if not all(params.get(key) for key in required):
       return None, "Missing required data", "99", False


   try:
       with transaction.atomic():
           thanh_toan = ThanhToan.objects.select_for_update().filter(
               MaGiaoDich=params["vnp_TxnRef"],
           ).first()
           if thanh_toan is None:
               return None, "Order not found", "01", False


           don_lien_quan = thanh_toan.DonHang
           if don_lien_quan:
               het_han_don_chua_thanh_toan(don_lien_quan.pk)
               don = DonHang.objects.select_for_update().get(
                   pk=don_lien_quan.pk
               )
               if don.trang_thai_don == "da_huy":
                   return thanh_toan, "Order expired", "04", False


           so_tien_vnpay = int(params["vnp_Amount"])
           so_tien_he_thong = int(thanh_toan.SoTienThanhToan * 100)
           if so_tien_vnpay != so_tien_he_thong:
               return thanh_toan, "Invalid amount", "04", False


           thanh_cong = (
               params["vnp_ResponseCode"] == "00"
               and params["vnp_TransactionStatus"] == "00"
           )


           if thanh_toan.TrangThaiThanhToan == "DaThanhToan":
               ma_vnpay = params.get("vnp_TransactionNo")


               if (
                       thanh_cong
                       and not thanh_toan.MaGiaoDichVNPay
                       and ma_vnpay
               ):
                   thanh_toan.MaGiaoDichVNPay = ma_vnpay
                   thanh_toan.save(
                       update_fields=["MaGiaoDichVNPay"]
                   )


               # Bổ sung: kiểm tra và xử lý điểm.
               # Service tự chống cộng điểm trùng.
               if thanh_cong:
                   from KHACHHANG.loyalty_services import (
                       xu_ly_diem_theo_thanh_toan
                   )


                   xu_ly_diem_theo_thanh_toan(thanh_toan)


               return (
                   thanh_toan,
                   "Confirm Success" if thanh_cong else "Order already confirmed",
                   "00" if thanh_cong else "02",
                   thanh_cong,
               )
           if thanh_toan.TrangThaiThanhToan != "ChoThanhToan":
               return thanh_toan, "Order already confirmed", "02", False


           thanh_toan.TrangThaiThanhToan = (
               "DaThanhToan" if thanh_cong else "ThatBai"
           )
           if thanh_cong:
               thanh_toan.NgayThanhToan = timezone.now()
               thanh_toan.MaGiaoDichVNPay = params.get(
                   "vnp_TransactionNo"
               )


           thanh_toan.save(update_fields=[
               "TrangThaiThanhToan",
               "NgayThanhToan",
               "MaGiaoDichVNPay",
           ])


           # Chỉ cộng điểm khi VNPay xác nhận thanh toán thành công.
           if thanh_cong:
               from KHACHHANG.loyalty_services import (
                   xu_ly_diem_theo_thanh_toan
               )


               xu_ly_diem_theo_thanh_toan(thanh_toan)


           return thanh_toan, "Confirm Success", "00", thanh_cong
   except (ValueError, TypeError):
       return None, "Invalid data", "99", False




def ket_qua_thanh_toan(request):
   params = request.GET.dict()
   thanh_toan, loi, _, thanh_cong = cap_nhat_giao_dich_vnpay(params)
   if loi == "Confirm Success":
       thong_bao = (
           "Thanh toán thành công!"
           if thanh_cong
           else "Thanh toán không thành công hoặc đã bị hủy."
       )
   else:
       thong_bao = {
           "Invalid signature": "Thông tin thanh toán không hợp lệ.",
           "Missing required data": "Thông tin thanh toán không đầy đủ.",
           "Order not found": "Không tìm thấy giao dịch thanh toán.",
           "Order expired": "Đơn hàng đã hết hạn thanh toán và bị hủy.",
           "Invalid amount": "Số tiền thanh toán không khớp với đơn hàng.",
           "Order already confirmed": "Giao dịch thanh toán đã được xử lý.",
           "Invalid data": "Dữ liệu thanh toán không hợp lệ.",
       }.get(loi, "Không thể xác nhận kết quả thanh toán.")


   try:
       so_tien = int(params.get("vnp_Amount", 0) or 0) // 100
   except (ValueError, TypeError):
       so_tien = 0


   context = {
       'thong_bao': thong_bao,
       'thanh_cong': thanh_cong,
       'ma_giao_dich': params.get('vnp_TxnRef'),
       'ma_giao_dich_vnpay': params.get('vnp_TransactionNo'),
       'so_tien': so_tien,
       'ma_phan_hoi': params.get('vnp_ResponseCode'),
       'ma_don_hang': thanh_toan.DonHang_id if thanh_toan else None,
   }


   return render(request, 'ket_qua_thanh_toan.html', context)


def ipn_vnpay(request):
   params = request.GET.dict()
   _, message, response_code, _ = cap_nhat_giao_dich_vnpay(params)
   return JsonResponse({"RspCode": response_code, "Message": message})




def thanh_toan_lai(request, ma_don_hang):
   ma_khach_hang = request.session.get("ma_khach_hang")
   if not ma_khach_hang:
       return redirect("KHACHHANG:dang_nhap")


   het_han_don_chua_thanh_toan(ma_don_hang)
   don = get_object_or_404(
       DonHang,
       pk=ma_don_hang,
       ma_khach_hang=str(ma_khach_hang),
       trang_thai_don="cho_xac_nhan",
   )
   if don.ngay_dat <= timezone.now() - timedelta(hours=24):
       messages.error(request, "Đơn hàng đã hết hạn thanh toán.")
       return redirect("DONHANG:danh_sach")
   if not ThanhToan.objects.filter(
       DonHang=don,
       PhuongThucThanhToan="VNPAY",
   ).exists() or ThanhToan.objects.filter(
       DonHang=don,
       TrangThaiThanhToan="DaThanhToan",
   ).exists():
       return redirect("DONHANG:danh_sach")
   if not (settings.VNPAY_TMN_CODE and settings.VNPAY_HASH_SECRET):
       messages.error(request, "Thanh toán VNPay hiện chưa được cấu hình.")
       return redirect("DONHANG:danh_sach")


   thanh_toan = tao_thanh_toan_cho_don(don, "VNPAY")
   return redirect(tao_url_thanh_toan(
       request,
       thanh_toan.MaGiaoDich,
       thanh_toan.SoTienThanhToan,
   ))





