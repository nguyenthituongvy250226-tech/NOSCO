from django.contrib import admin
from .models import GioHang, ChiTietGioHang


class ChiTietGioHangInline(admin.TabularInline):
    model = ChiTietGioHang
    extra = 1


@admin.register(GioHang)
class GioHangAdmin(admin.ModelAdmin):
    list_display = (
        "ma_gio_hang",
        "ma_khach_hang",
        "ngay_tao",
        "ngay_cap_nhat",
        "loai_gio_hang",
    )

    search_fields = (
        "ma_gio_hang",
        "ma_khach_hang",
    )

    list_filter = ("loai_gio_hang",)

    inlines = [ChiTietGioHangInline]


@admin.register(ChiTietGioHang)
class ChiTietGioHangAdmin(admin.ModelAdmin):
    list_display = (
        "ma_chi_tiet_gio_hang",
        "gio_hang",
        "ma_bien_the_sp",
        "so_luong",
        "trang_thai_chon",
    )

    search_fields = (
        "ma_chi_tiet_gio_hang",
        "gio_hang__ma_gio_hang",
        "ma_bien_the_sp",
    )

    list_filter = ("trang_thai_chon",)