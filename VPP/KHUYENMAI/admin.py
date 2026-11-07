
from django.contrib import admin
from django.utils import timezone
from django.utils.safestring import mark_safe

from .models import (
    Voucher,
    VoucherKhachHang,
    KhuyenMai,
    ChiTietKhuyenMai,
)


# ==========================================
# QUẢN LÝ VOUCHER
# ==========================================

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
        'hien_thi_trang_thai',
    )

    list_filter = (
        'LoaiGiamGia',
        'DoiTuongApDung',
        'TrangThai',
        'NgayBatDau',
        'NgayKetThuc',
    )

    search_fields = (
        'MaVoucher',
        'TenVoucher',
    )

    ordering = ('-NgayBatDau',)
    date_hierarchy = 'NgayBatDau'
    list_per_page = 20

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

    @admin.display(description='Trạng thái')
    def hien_thi_trang_thai(self, obj):
        if not obj.TrangThai:
            return mark_safe(
                '<span style="color:#dc2626;font-weight:600;">● Ngừng hoạt động</span>'
            )

        now = timezone.now()

        if now < obj.NgayBatDau:
            return mark_safe(
                '<span style="color:#d97706;font-weight:600;">● Sắp diễn ra</span>'
            )

        if now > obj.NgayKetThuc:
            return mark_safe(
                '<span style="color:#6b7280;font-weight:600;">● Đã kết thúc</span>'
            )

        return mark_safe(
            '<span style="color:#16a34a;font-weight:600;">● Đang diễn ra</span>'
        )


# ==========================================
# QUẢN LÝ VOUCHER KHÁCH HÀNG
# ==========================================

@admin.register(VoucherKhachHang)
class VoucherKhachHangAdmin(admin.ModelAdmin):

    list_display = (
        'MaVoucherKhachHang',
        'MaVoucher',
        'NgayLay',
        'TrangThai',
    )

    list_filter = (
        'TrangThai',
        'NgayLay',
    )

    search_fields = (
        'MaVoucherKhachHang',
        'MaVoucher__MaVoucher',
    )

    ordering = ('-NgayLay',)
    date_hierarchy = 'NgayLay'
    list_per_page = 20


# ==========================================
# CHI TIẾT KHUYẾN MÃI HIỂN THỊ TRONG CHƯƠNG TRÌNH
# ==========================================

class ChiTietKhuyenMaiInline(admin.TabularInline):

    model = ChiTietKhuyenMai
    extra = 0
    show_change_link = True

    fields = (
        'MaChiTietKM',
        'MaSanPham',
        'PhanTramGiam',
        'GiaKhuyenMai',
        'TrangThai',
    )


# ==========================================
# QUẢN LÝ CHƯƠNG TRÌNH KHUYẾN MÃI
# ==========================================

@admin.register(KhuyenMai)
class KhuyenMaiAdmin(admin.ModelAdmin):

    list_display = (
        'MaKhuyenMai',
        'TenKhuyenMai',
        'LoaiKhuyenMai',
        'NgayBatDau',
        'NgayKetThuc',
        'hien_thi_trang_thai',
        'so_san_pham',
    )

    list_filter = (
        'LoaiKhuyenMai',
        'NgayBatDau',
        'NgayKetThuc',
    )

    search_fields = (
        'MaKhuyenMai',
        'TenKhuyenMai',
    )

    ordering = ('-NgayBatDau',)
    date_hierarchy = 'NgayBatDau'
    list_per_page = 20

    inlines = [ChiTietKhuyenMaiInline]

    fieldsets = (
        ('Thông tin chương trình', {
            'fields': (
                'MaKhuyenMai',
                'TenKhuyenMai',
                'LoaiKhuyenMai',
                'MoTa',
            )
        }),
        ('Thời gian áp dụng', {
            'fields': (
                'NgayBatDau',
                'NgayKetThuc',
            )
        }),
    )

    @admin.display(description='Trạng thái')
    def hien_thi_trang_thai(self, obj):
        now = timezone.now()

        if now < obj.NgayBatDau:
            return mark_safe(
                '<span style="color:#d97706;font-weight:600;">● Sắp diễn ra</span>'
            )

        if now > obj.NgayKetThuc:
            return mark_safe(
                '<span style="color:#6b7280;font-weight:600;">● Đã kết thúc</span>'
            )

        return mark_safe(
            '<span style="color:#16a34a;font-weight:600;">● Đang diễn ra</span>'
        )

    @admin.display(description='Số sản phẩm')
    def so_san_pham(self, obj):
        return obj.chi_tiet_khuyen_mai.count()


# ==========================================
# QUẢN LÝ CHI TIẾT KHUYẾN MÃI
# ==========================================

@admin.register(ChiTietKhuyenMai)
class ChiTietKhuyenMaiAdmin(admin.ModelAdmin):

    list_display = (
        'MaChiTietKM',
        'MaKhuyenMai',
        'MaSanPham',
        'PhanTramGiam',
        'GiaKhuyenMai',
        'TrangThai',
    )

    list_filter = (
        'TrangThai',
        'MaKhuyenMai',
    )

    search_fields = (
        'MaChiTietKM',
        'MaKhuyenMai__TenKhuyenMai',
        'MaSanPham',
    )

    ordering = ('MaChiTietKM',)
    list_per_page = 20
