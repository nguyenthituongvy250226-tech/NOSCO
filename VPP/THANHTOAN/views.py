
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from decimal import Decimal
from .models import ThanhToan
from django.db import transaction
import uuid
from .vnpay import tao_url_thanh_toan, kiem_tra_chu_ky_vnpay
from django.http import JsonResponse


def trang_thanh_toan(request):
    return render(request, 'thanh_toan.html')


def ket_qua_thanh_toan(request):
    params = request.GET.dict()

    if not kiem_tra_chu_ky_vnpay(params):
        return render(request, 'ket_qua_thanh_toan.html', {
            'thong_bao': 'Thông tin thanh toán không hợp lệ.',
            'thanh_cong': False,
        })

    thanh_cong = (
            params.get('vnp_ResponseCode') == '00'
            and params.get('vnp_TransactionStatus') == '00'
    )
    if thanh_cong:
        thong_bao = 'Thanh toán thành công!'
    else:
        thong_bao = 'Thanh toán không thành công hoặc đã bị hủy.'

    context = {
        'thong_bao': thong_bao,
        'thanh_cong': thanh_cong,
        'ma_giao_dich': params.get('vnp_TxnRef'),
        'ma_giao_dich_vnpay': params.get('vnp_TransactionNo'),
        'so_tien': int(params.get('vnp_Amount', 0)) // 100,
        'ma_phan_hoi': params.get('vnp_ResponseCode'),
    }

    return render(request, 'ket_qua_thanh_toan.html', context)

def ipn_vnpay(request):
    params = request.GET.dict()

    # 1. Kiểm tra chữ ký
    if not kiem_tra_chu_ky_vnpay(params):
        return JsonResponse({
            'RspCode': '97',
            'Message': 'Invalid signature'
        })

    # 2. Kiểm tra dữ liệu bắt buộc
    cac_truong_bat_buoc = [
        'vnp_TxnRef',
        'vnp_Amount',
        'vnp_ResponseCode',
        'vnp_TransactionStatus',
    ]

    if not all(params.get(key) for key in cac_truong_bat_buoc):
        return JsonResponse({
            'RspCode': '99',
            'Message': 'Missing required data'
        })

    try:
        with transaction.atomic():

            # 3. Tìm giao dịch trong database
            thanh_toan = ThanhToan.objects.select_for_update().filter(
                MaGiaoDich=params['vnp_TxnRef']
            ).first()

            if thanh_toan is None:
                return JsonResponse({
                    'RspCode': '01',
                    'Message': 'Order not found'
                })

            # 4. Kiểm tra số tiền
            so_tien_vnpay = int(params['vnp_Amount'])
            so_tien_he_thong = int(
                thanh_toan.SoTienThanhToan * 100
            )

            if so_tien_vnpay != so_tien_he_thong:
                return JsonResponse({
                    'RspCode': '04',
                    'Message': 'Invalid amount'
                })

            # 5. Kiểm tra giao dịch đã xử lý chưa
            if thanh_toan.TrangThaiThanhToan != 'ChoThanhToan':
                return JsonResponse({
                    'RspCode': '02',
                    'Message': 'Order already confirmed'
                })

            # 6. Cập nhật trạng thái
            if (
                params['vnp_ResponseCode'] == '00'
                and params['vnp_TransactionStatus'] == '00'
            ):
                thanh_toan.TrangThaiThanhToan = 'DaThanhToan'
            else:
                thanh_toan.TrangThaiThanhToan = 'ThatBai'

            thanh_toan.save(update_fields=['TrangThaiThanhToan'])

        # 7. Phản hồi VNPay
        return JsonResponse({
            'RspCode': '00',
            'Message': 'Confirm Success'
        })

    except (ValueError, TypeError):
        return JsonResponse({
            'RspCode': '99',
            'Message': 'Invalid data'
        })
@require_POST
def thanh_toan_thu(request):
    ma_thanh_toan = f"TT{uuid.uuid4().hex[:8].upper()}"
    ma_giao_dich = f"TEST{uuid.uuid4().hex[:12].upper()}"

    so_tien = Decimal('10000')

    # Lưu giao dịch vào database trước
    ThanhToan.objects.create(
        MaThanhToan=ma_thanh_toan,
        MaGiaoDich=ma_giao_dich,
        PhuongThucThanhToan='VNPAY',
        SoTienThanhToan=so_tien,
        TrangThaiThanhToan='ChoThanhToan',
        LoaiGiaoDich='ThanhToan'
    )

    # Tạo URL thanh toán VNPay
    url = tao_url_thanh_toan(
        request,
        ma_giao_dich,
        so_tien
    )

    return redirect(url)
@require_POST
def thanh_toan_cod(request):
    ma_thanh_toan = f"TT{uuid.uuid4().hex[:8].upper()}"

    so_tien = Decimal('10000')

    ThanhToan.objects.create(
        MaThanhToan=ma_thanh_toan,
        MaGiaoDich=None,
        PhuongThucThanhToan='COD',
        SoTienThanhToan=so_tien,
        TrangThaiThanhToan='ChoThanhToan',
        LoaiGiaoDich='ThanhToan'
    )

    return render(request, 'ket_qua_cod.html', {
        'thong_bao': 'Đặt hàng với phương thức thanh toán khi nhận hàng thành công!',
        'ma_thanh_toan': ma_thanh_toan,
        'so_tien': so_tien,
    })