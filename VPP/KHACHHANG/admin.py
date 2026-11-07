
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import (
    NguoiDung,
    HoSoKhachHang,
    SoDiaChi,
    HoSoNhanVien,
    LichSuTichDiem,
    ThongBao,
    YeuCauHoTro
)


class NguoiDungCreationForm(UserCreationForm):
    class Meta:
        model = NguoiDung
        fields = ("TenDangNhap", "Email", "VaiTro")


class NguoiDungChangeForm(UserChangeForm):
    class Meta:
        model = NguoiDung
        fields = "__all__"


@admin.register(NguoiDung)
class NguoiDungAdmin(UserAdmin):
    model = NguoiDung
    form = NguoiDungChangeForm
    add_form = NguoiDungCreationForm

    ordering = ("TenDangNhap",)

    list_display = (
        "MaNguoiDung",
        "TenDangNhap",
        "Email",
        "VaiTro",
        "KichHoat",
        "is_staff",
    )

    search_fields = ("TenDangNhap", "Email")

    list_filter = ("VaiTro", "KichHoat", "is_staff")

    fieldsets = (
        ("Thông tin tài khoản", {
            "fields": ("TenDangNhap", "password")
        }),
        ("Thông tin cá nhân", {
            "fields": ("Email", "VaiTro", "KichHoat")
        }),
        ("Phân quyền", {
            "fields": (
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Thời gian", {
            "fields": ("last_login",)
        }),
    )

    add_fieldsets = (
        ("Tạo tài khoản", {
            "classes": ("wide",),
            "fields": (
                "TenDangNhap",
                "Email",
                "VaiTro",
                "password1",
                "password2",
                "KichHoat",
                "is_staff",
            )
        }),
    )

    readonly_fields = ("MaNguoiDung", "last_login")


@admin.register(HoSoKhachHang)
class HoSoKhachHangAdmin(admin.ModelAdmin):
    list_display = (
        "MaHoSo", "HoVaTen", "MaNguoiDung",
        "SoDienThoai", "DiemTichLuy", "HangThanhVien"
    )
    search_fields = (
        "MaHoSo", "HoVaTen", "SoDienThoai",
        "MaNguoiDung__Email"
    )
    list_filter = ("GioiTinh", "HangThanhVien")
    readonly_fields = ("MaHoSo",)


@admin.register(SoDiaChi)
class SoDiaChiAdmin(admin.ModelAdmin):
    list_display = (
        "MaDiaChi", "MaKhachHang", "TenNguoiNhan",
        "SoDienThoai", "DiaChi", "MacDinh"
    )
    search_fields = ("TenNguoiNhan", "SoDienThoai", "DiaChi")
    list_filter = ("MacDinh",)
    readonly_fields = ("MaDiaChi",)


@admin.register(HoSoNhanVien)
class HoSoNhanVienAdmin(admin.ModelAdmin):
    list_display = (
        "MaHoSoNV", "HoTen", "MaNguoiDung",
        "SoDienThoai", "ChucVu", "NgayVaoLam", "TrangThai"
    )
    search_fields = ("HoTen", "SoDienThoai", "ChucVu")
    list_filter = ("ChucVu", "TrangThai")
    readonly_fields = ("MaHoSoNV",)


@admin.register(LichSuTichDiem)
class LichSuTichDiemAdmin(admin.ModelAdmin):
    list_display = (
        "MaLichSuDiem", "MaKhachHang", "MaDonHang",
        "LoaiGiaoDich", "SoDiem", "SoDuDiem", "NgayTao"
    )
    search_fields = (
        "MaLichSuDiem", "MaDonHang",
        "MaKhachHang__HoVaTen"
    )
    list_filter = ("LoaiGiaoDich", "NgayTao")
    readonly_fields = ("MaLichSuDiem", "NgayTao")


@admin.register(ThongBao)
class ThongBaoAdmin(admin.ModelAdmin):
    list_display = (
        "MaThongBao", "MaNguoiNhan", "MaNguoiGui",
        "TieuDe", "LoaiThongBao", "DaDoc", "NgayTao"
    )
    search_fields = ("TieuDe", "NoiDung")
    list_filter = ("LoaiThongBao", "DaDoc", "NgayTao")
    readonly_fields = ("MaThongBao", "NgayTao")


@admin.register(YeuCauHoTro)
class YeuCauHoTroAdmin(admin.ModelAdmin):
    list_display = (
        "MaYeuCau", "MaKhachHang", "TieuDe",
        "TrangThai", "NguoiXuLy", "NgayTao"
    )
    search_fields = (
        "TieuDe", "NoiDung",
        "MaKhachHang__HoVaTen"
    )
    list_filter = ("TrangThai", "NgayTao")
    readonly_fields = ("MaYeuCau", "NgayTao", "NgayCapNhat")
