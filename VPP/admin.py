
from django.contrib import admin

from datetime import date
from django.utils import timezone
class NOSCOAdminSite(admin.AdminSite):
    site_header = 'NOSCO | Hệ thống quản trị'
    site_title = 'NOSCO Admin'
    index_title = 'Quản lý hệ thống'
from django.apps import apps
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from django.contrib import admin


class NOSCOAdminSite(admin.AdminSite):
    site_header = 'NOSCO | Hệ thống quản trị'
    site_title = 'NOSCO Admin'
    index_title = 'Quản lý hệ thống'

    def index(self, request, extra_context=None):
        SanPham = apps.get_model('SANPHAM', 'SanPham')
        BienTheSanPham = apps.get_model('SANPHAM', 'BienTheSanPham')
        DonHang = apps.get_model('DONHANG', 'DonHang')
        HoSoKhachHang = apps.get_model('KHACHHANG', 'HoSoKhachHang')
        ThanhToan = apps.get_model('THANHTOAN', 'ThanhToan')

        # Xác định đơn hàng đã thanh toán
        don_da_thanh_toan = ThanhToan.objects.filter(
            DonHang__isnull=False,
            TrangThaiThanhToan='DaThanhToan',
            LoaiGiaoDich='ThanhToan'
        ).values_list('DonHang_id', flat=True)

        # Xác định đơn hàng đã có giao dịch hoàn tiền
        don_da_hoan_tien = ThanhToan.objects.filter(
            DonHang__isnull=False
        ).filter(
            Q(LoaiGiaoDich='HoanTien') |
            Q(TrangThaiThanhToan='DaHoanTien')
        ).values_list('DonHang_id', flat=True)

        # Chỉ tính doanh thu từ đơn đã giao, đã thanh toán và chưa hoàn tiền
        don_doanh_thu = DonHang.objects.filter(
            trang_thai_don='da_giao',
            ma_don_hang__in=don_da_thanh_toan
        ).exclude(
            ma_don_hang__in=don_da_hoan_tien
        )

        doanh_thu = don_doanh_thu.aggregate(
            total=Sum('tong_tien')
        )['total'] or 0

        # Thống kê đơn hàng
        thong_ke_don = {
            'cho_xac_nhan': DonHang.objects.filter(
                trang_thai_don='cho_xac_nhan'
            ).count(),
            'da_giao': DonHang.objects.filter(
                trang_thai_don='da_giao'
            ).count(),
            'tra_hang': DonHang.objects.filter(
                trang_thai_don='tra_hang'
            ).count(),
            'da_huy': DonHang.objects.filter(
                trang_thai_don='da_huy'
            ).count(),
        }

        # Doanh thu theo tháng
        doanh_thu_thang = don_doanh_thu.annotate(
            thang=TruncMonth('ngay_dat')
        ).values('thang').annotate(
            tong=Sum('tong_tien')
        ).order_by('thang')
        # Chuẩn bị dữ liệu biểu đồ doanh thu 6 tháng gần nhất
        du_lieu_thang = {
            item['thang'].strftime('%Y-%m'): item['tong']
            for item in doanh_thu_thang
        }

        hom_nay = timezone.localdate()
        cac_thang = []

        for i in range(5, -1, -1):
            thang = hom_nay.month - i
            nam = hom_nay.year

            while thang <= 0:
                thang += 12
                nam -= 1

            ngay_dau_thang = date(nam, thang, 1)
            khoa = ngay_dau_thang.strftime('%Y-%m')
            gia_tri = du_lieu_thang.get(khoa, 0) or 0

            cac_thang.append({
                'label': f'T{thang:02d}/{nam}',
                'amount': gia_tri,
            })

        gia_tri_lon_nhat = max(
            [float(item['amount']) for item in cac_thang],
            default=0
        )

        for item in cac_thang:
            if gia_tri_lon_nhat > 0 and item['amount'] > 0:
                item['height'] = max(
                    8,
                    round(float(item['amount']) / gia_tri_lon_nhat * 100)
                )
            else:
                item['height'] = 0

        context = {
            'tong_san_pham': SanPham.objects.count(),
            'tong_bien_the': BienTheSanPham.objects.count(),
            'tong_ton_kho': BienTheSanPham.objects.aggregate(
                total=Sum('so_luong_ton')
            )['total'] or 0,
            'tong_don_hang': DonHang.objects.count(),
            'tong_khach_hang': HoSoKhachHang.objects.count(),
            'doanh_thu': doanh_thu,
            'so_don_tinh_doanh_thu': don_doanh_thu.count(),
            'thong_ke_don': thong_ke_don,
            'doanh_thu_thang': doanh_thu_thang,
            'don_hang_moi': DonHang.objects.order_by(
                '-ngay_dat'
            )[:5],
            'cac_thang': cac_thang,
        }

        if extra_context:
            context.update(extra_context)

        return super().index(request, extra_context=context)