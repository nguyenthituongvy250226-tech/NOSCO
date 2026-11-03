from django.contrib import admin
from .models import Voucher, VoucherKhachHang

@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):

    list_display = (
        'MaVoucher',
        'TenVoucher',
        'LoaiGiamGia',
        'DoiTuongApDung',
        'GiaTriGiam',
        'NgayBatDau',
        'NgayKetThuc',
        'TrangThai',
        'GioiHanSuDung',
        'DieuKienGiam',
    )

    list_filter = (
        'LoaiGiamGia',
        'DoiTuongApDung',
        'TrangThai',
    )

    search_fields = (
        'MaVoucher',
        'TenVoucher',
    )

    ordering = ('-NgayBatDau',)

    fieldsets = (
        ('Thông tin Voucher', {
            'fields': (
                'MaVoucher',
                'TenVoucher',
                'LoaiGiamGia',
                'DoiTuongApDung',
            )
        }),
        ('Thông tin giảm giá', {
            'fields': (
                'GiaTriGiam',
                'DieuKienGiam',
                'GioiHanSuDung',
            )
        }),
        ('Thời gian và trạng thái', {
            'fields': (
                'NgayBatDau',
                'NgayKetThuc',
                'TrangThai',
            )
        }),
    )
@admin.register(VoucherKhachHang)
class VoucherKhachHangAdmin(admin.ModelAdmin):
    list_display = (
        'MaVoucherKhachHang',
        'MaVoucher',
        #'MaKhachHang',                # CHỜ TÍCH HỢP
        #'MaLichSuDiem',                # CHỜ TÍCH HỢP
        'NgayLay',
        'TrangThai',
    )

    list_filter = ('TrangThai', 'NgayLay')
    search_fields = (
        'MaVoucherKhachHang',
        'MaVoucher__MaVoucher',
        # 'MaKhachHang__MaKhachHang',  # CHỜ TÍCH HỢP
    )
    ordering = ('-NgayLay',)