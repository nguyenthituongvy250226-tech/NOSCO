from django.contrib import admin
from django.utils.html import format_html
from .models import ThanhToan


@admin.register(ThanhToan)
class ThanhToanAdmin(admin.ModelAdmin):

    list_display = (
        'MaThanhToan',
        'hien_thi_phuong_thuc',
        'hien_thi_so_tien',
        'hien_thi_trang_thai',
        'hien_thi_loai_giao_dich',
        'MaGiaoDich',
    )

    list_filter = (
        'PhuongThucThanhToan',
        'TrangThaiThanhToan',
        'LoaiGiaoDich',
    )

    search_fields = ('MaThanhToan', 'MaGiaoDich')
    ordering = ('MaThanhToan',)
    list_per_page = 20

    @admin.display(description='Phương thức thanh toán')
    def hien_thi_phuong_thuc(self, obj):
        return obj.get_PhuongThucThanhToan_display()

    @admin.display(description='Số tiền thanh toán', ordering='SoTienThanhToan')
    def hien_thi_so_tien(self, obj):
        return f"{obj.SoTienThanhToan:,.0f} VNĐ"

    @admin.display(description='Trạng thái thanh toán')
    def hien_thi_trang_thai(self, obj):
        mau_sac = {
            'ChoThanhToan': '#D97706',
            'DaThanhToan': '#15803D',
            'ThatBai': '#DC2626',
            'DaHoanTien': '#2563EB',
        }

        mau = mau_sac.get(obj.TrangThaiThanhToan, '#64748B')

        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            mau,
            obj.get_TrangThaiThanhToan_display()
        )

    @admin.display(description='Loại giao dịch')
    def hien_thi_loai_giao_dich(self, obj):
        return obj.get_LoaiGiaoDich_display()

    fieldsets = (
        ('Thông tin thanh toán', {
            'fields': (
                'MaThanhToan',
                'PhuongThucThanhToan',
                'SoTienThanhToan',
                'TrangThaiThanhToan',
            )
        }),
        ('Thông tin giao dịch', {
            'fields': (
                'LoaiGiaoDich',
                'MaGiaoDich',
            )
        }),
    )

    readonly_fields = (
        'MaThanhToan',
        'PhuongThucThanhToan',
        'SoTienThanhToan',
        'LoaiGiaoDich',
        'MaGiaoDich',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False