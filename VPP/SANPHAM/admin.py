from django.contrib import admin
from .models import (
    DanhMucSanPham,
    ThuongHieu,
    SanPham,
    BienTheSanPham,
    HinhAnhSanPham,
    BaiViet,
    SanPhamQuaTang,
DanhGiaSanPham,

)


@admin.register(DanhMucSanPham)
class DanhMucSanPhamAdmin(admin.ModelAdmin):
    list_display = ("ma_danh_muc", "ten_danh_muc", "danh_muc_cha")
    search_fields = ("ma_danh_muc", "ten_danh_muc")


@admin.register(ThuongHieu)
class ThuongHieuAdmin(admin.ModelAdmin):
    list_display = ("ma_thuong_hieu", "ten_thuong_hieu")
    search_fields = ("ma_thuong_hieu", "ten_thuong_hieu")


class BienTheSanPhamInline(admin.TabularInline):
    model = BienTheSanPham
    extra = 1


@admin.register(SanPham)
class SanPhamAdmin(admin.ModelAdmin):
    list_display = (
        "ma_san_pham",
        "ten_san_pham",
        "danh_muc",
        "thuong_hieu",
        "trang_thai_ban",
        "ngay_tao",
    )
    list_filter = ("trang_thai_ban", "danh_muc", "thuong_hieu")
    search_fields = ("ma_san_pham", "ten_san_pham")
    inlines = [BienTheSanPhamInline]


class HinhAnhSanPhamInline(admin.TabularInline):
    model = HinhAnhSanPham
    extra = 1


@admin.register(BienTheSanPham)
class BienTheSanPhamAdmin(admin.ModelAdmin):
    list_display = (
        "ma_bien_the",
        "san_pham",
        "mau_sac",
        "kich_thuoc",
        "gia_ban",
        "so_luong_ton",
    )
    search_fields = ("ma_bien_the", "san_pham__ten_san_pham")
    inlines = [HinhAnhSanPhamInline]


@admin.register(HinhAnhSanPham)
class HinhAnhSanPhamAdmin(admin.ModelAdmin):
    list_display = (
        "ma_hinh_anh",
        "bien_the",
        "thu_tu_hien_thi",
        "anh_dai_dien",
    )
    list_filter = ("anh_dai_dien",)


# QUẢN LÝ BÀI VIẾT
@admin.register(BaiViet)
class BaiVietAdmin(admin.ModelAdmin):
    list_display = (
        "ma_bai_viet",
        "tieu_de",
        "ngay_dang",
        "trang_thai",
    )
    list_filter = ("trang_thai", "ngay_dang")
    search_fields = ("ma_bai_viet", "tieu_de")
    ordering = ("-ngay_dang",)

@admin.register(SanPhamQuaTang)
class SanPhamQuaTangAdmin(admin.ModelAdmin):
    list_display = ["san_pham", "vi_tri"]
    list_editable = ["vi_tri"]
    ordering = ["vi_tri"]
    list_per_page = 8

@admin.register(DanhGiaSanPham)
class DanhGiaSanPhamAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "san_pham",
        "ma_khach_hang",
        "so_sao",
        "ngay_danh_gia",
    )
    list_filter = ("so_sao", "ngay_danh_gia")
    search_fields = ("noi_dung",)