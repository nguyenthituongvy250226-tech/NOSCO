
from django.contrib import admin
from .models import (
    ChiTietDonHang,
    ChiTietYeuCauTraHang,
    DonHang,
    GiaoHang,
    BangChungYeuCauTraHang,
    YeuCauTraHang,
)


@admin.register(DonHang)
class DonHangAdmin(admin.ModelAdmin):
    list_display = (
        "ma_don_hang",
        "ten_nguoi_nhan",
        "sdt_nguoi_nhan",
        "ngay_dat",
        "tong_tien",
        "trang_thai_don",
    )
    list_filter = ("trang_thai_don", "ngay_dat")
    search_fields = (
        "ma_don_hang",
        "ten_nguoi_nhan",
        "sdt_nguoi_nhan",
    )
    readonly_fields = ("ngay_dat",)
    ordering = ("-ngay_dat",)


@admin.register(ChiTietDonHang)
class ChiTietDonHangAdmin(admin.ModelAdmin):
    list_display = (
        "ma_chi_tiet_dh",
        "ma_don_hang",
        "ma_bien_the",
        "so_luong",
        "don_gia",
        "thanh_tien",
        "trang_thai_giao",
    )
    list_filter = ("trang_thai_giao",)
    search_fields = ("ma_chi_tiet_dh", "ma_bien_the")


class ChiTietYeuCauTraHangInline(admin.TabularInline):
    model = ChiTietYeuCauTraHang
    extra = 0


class BangChungYeuCauTraHangInline(admin.TabularInline):
    model = BangChungYeuCauTraHang
    extra = 0
    readonly_fields = ("ngay_tai_len",)


@admin.register(YeuCauTraHang)
class YeuCauTraHangAdmin(admin.ModelAdmin):
    list_display = (
        "ma_yeu_cau_tra",
        "ma_don_hang",
        "ma_thanh_toan",
        "trang_thai_tra",
        "ngay_tao",
    )
    list_filter = ("trang_thai_tra", "ngay_tao")
    search_fields = ("ma_yeu_cau_tra", "ma_thanh_toan")
    readonly_fields = ("ngay_tao",)
    inlines = (ChiTietYeuCauTraHangInline, BangChungYeuCauTraHangInline)


@admin.register(GiaoHang)
class GiaoHangAdmin(admin.ModelAdmin):
    list_display = ("ma_giao_hang", "don_hang", "don_vi_van_chuyen", "ma_van_don", "trang_thai", "cap_nhat_luc")
    list_filter = ("trang_thai", "don_vi_van_chuyen")
    search_fields = ("ma_giao_hang", "ma_van_don", "don_hang__ma_don_hang")
    readonly_fields = ("cap_nhat_luc",)
