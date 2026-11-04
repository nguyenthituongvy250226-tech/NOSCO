import uuid

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)


# =====================================================
# HÀM TẠO MÃ TỰ ĐỘNG 10 KÝ TỰ
# =====================================================

def tao_ma():
    return uuid.uuid4().hex[:10].upper()


# =====================================================
# KIỂU DỮ LIỆU CHAR(10)
# =====================================================

class Char10Field(models.CharField):
    """
    Trường dữ liệu CHAR(10).
    Sử dụng để mô phỏng kiểu dữ liệu trong báo cáo.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 10)
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        return "char(10)"


# =====================================================
# 1. BẢNG NGƯỜI DÙNG
# =====================================================

class NguoiDungManager(BaseUserManager):

    def create_user(
        self,
        TenDangNhap,
        Email,
        password=None,
        VaiTro="KHACH_HANG",
        **extra_fields
    ):
        if not TenDangNhap:
            raise ValueError("Tên đăng nhập không được để trống")

        if not Email:
            raise ValueError("Email không được để trống")

        Email = self.normalize_email(Email)

        user = self.model(
            MaNguoiDung=tao_ma(),
            TenDangNhap=TenDangNhap,
            Email=Email,
            VaiTro=VaiTro,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(
        self,
        TenDangNhap,
        Email,
        password=None,
        **extra_fields
    ):
        extra_fields.setdefault("VaiTro", "NHAN_VIEN")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("KichHoat", True)

        return self.create_user(
            TenDangNhap=TenDangNhap,
            Email=Email,
            password=password,
            **extra_fields
        )


class NguoiDung(AbstractBaseUser, PermissionsMixin):

    VAI_TRO_CHOICES = [
        ("KHACH_HANG", "Khách hàng"),
        ("NHAN_VIEN", "Nhân viên"),
    ]

    MaNguoiDung = Char10Field(
        primary_key=True,
        default=tao_ma,
        editable=False,
        db_column="MaNguoiDung"
    )

    TenDangNhap = models.CharField(
        max_length=50,
        unique=True,
        db_column="TenDangNhap"
    )

    password = models.CharField(
        max_length=255,
        db_column="MatKhau"
    )

    Email = models.EmailField(
        max_length=100,
        unique=True,
        db_column="Email"
    )

    VaiTro = models.CharField(
        max_length=30,
        choices=VAI_TRO_CHOICES,
        default="KHACH_HANG",
        db_column="VaiTro"
    )

    KichHoat = models.BooleanField(
        default=True,
        db_column="KichHoat"
    )

    is_staff = models.BooleanField(default=False)

    objects = NguoiDungManager()

    USERNAME_FIELD = "TenDangNhap"
    REQUIRED_FIELDS = ["Email"]

    class Meta:
        db_table = "NguoiDung"
        verbose_name = "Người dùng"
        verbose_name_plural = "Người dùng"

    def __str__(self):
        return self.TenDangNhap

    @property
    def is_active(self):
        return self.KichHoat

    @is_active.setter
    def is_active(self, value):
        self.KichHoat = value


# =====================================================
# 2. BẢNG HỒ SƠ KHÁCH HÀNG
# =====================================================

class HoSoKhachHang(models.Model):

    GIOI_TINH_CHOICES = [
        ("Nam", "Nam"),
        ("Nữ", "Nữ"),
        ("Khác", "Khác"),
    ]

    MaHoSo = Char10Field(
        primary_key=True,
        default=tao_ma,
        editable=False,
        db_column="MaHoSo"
    )

    MaNguoiDung = models.OneToOneField(
        NguoiDung,
        on_delete=models.CASCADE,
        related_name="ho_so_khach_hang",
        db_column="MaNguoiDung"
    )

    HoVaTen = models.CharField(
        max_length=100,
        db_column="HoVaTen"
    )

    SoDienThoai = models.CharField(
        max_length=15,
        db_column="SoDienThoai"
    )

    GioiTinh = models.CharField(
        max_length=20,
        choices=GIOI_TINH_CHOICES,
        null=True,
        blank=True,
        db_column="GioiTinh"
    )

    DiemTichLuy = models.PositiveIntegerField(
        default=0,
        db_column="DiemTichLuy"
    )

    HangThanhVien = models.CharField(
        max_length=50,
        default="Thành viên",
        db_column="HangThanhVien"
    )

    class Meta:
        db_table = "HoSoKhachHang"
        verbose_name = "Hồ sơ khách hàng"
        verbose_name_plural = "Hồ sơ khách hàng"

    def __str__(self):
        return self.HoVaTen


# =====================================================
# 3. BẢNG SỔ ĐỊA CHỈ
# =====================================================

class SoDiaChi(models.Model):

    MaDiaChi = Char10Field(
        primary_key=True,
        default=tao_ma,
        editable=False,
        db_column="MaDiaChi"
    )

    MaKhachHang = models.ForeignKey(
        HoSoKhachHang,
        on_delete=models.CASCADE,
        related_name="danh_sach_dia_chi",
        db_column="MaKhachHang"
    )

    TenNguoiNhan = models.CharField(
        max_length=100,
        db_column="TenNguoiNhan"
    )

    SoDienThoai = models.CharField(
        max_length=15,
        db_column="SoDienThoai"
    )

    DiaChi = models.CharField(
        max_length=255,
        db_column="DiaChi"
    )

    MacDinh = models.BooleanField(
        default=False,
        db_column="MacDinh"
    )

    class Meta:
        db_table = "SoDiaChi"
        verbose_name = "Sổ địa chỉ"
        verbose_name_plural = "Sổ địa chỉ"

    def __str__(self):
        return f"{self.TenNguoiNhan} - {self.DiaChi}"


# =====================================================
# 4. BẢNG HỒ SƠ NHÂN VIÊN
# =====================================================

class HoSoNhanVien(models.Model):

    MaHoSoNV = Char10Field(
        primary_key=True,
        default=tao_ma,
        editable=False,
        db_column="MaHoSoNV"
    )

    MaNguoiDung = models.OneToOneField(
        NguoiDung,
        on_delete=models.CASCADE,
        related_name="ho_so_nhan_vien",
        db_column="MaNguoiDung"
    )

    HoTen = models.CharField(
        max_length=100,
        db_column="HoTen"
    )

    SoDienThoai = models.CharField(
        max_length=15,
        db_column="SoDienThoai"
    )

    DiachiNV = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        db_column="DiachiNV"
    )

    GioiTinh = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_column="GioiTinh"
    )

    NgaySinh = models.DateField(
        null=True,
        blank=True,
        db_column="NgaySinh"
    )

    ChucVu = models.CharField(
        max_length=50,
        db_column="ChucVu"
    )

    NgayVaoLam = models.DateField(
        db_column="NgayVaoLam"
    )

    TrangThai = models.BooleanField(
        default=True,
        db_column="TrangThai"
    )

    class Meta:
        db_table = "HoSoNhanVien"
        verbose_name = "Hồ sơ nhân viên"
        verbose_name_plural = "Hồ sơ nhân viên"

    def __str__(self):
        return self.HoTen


# =====================================================
# 5. BẢNG LỊCH SỬ TÍCH ĐIỂM
# =====================================================

class LichSuTichDiem(models.Model):

    LOAI_GIAO_DICH = [
        ("CONG", "Cộng điểm"),
        ("TRU", "Trừ điểm"),
    ]

    MaLichSuDiem = Char10Field(
        primary_key=True,
        default=tao_ma,
        editable=False,
        db_column="MaLichSuDiem"
    )

    MaKhachHang = models.ForeignKey(
        HoSoKhachHang,
        on_delete=models.CASCADE,
        related_name="lich_su_tich_diem",
        db_column="MaKhachHang"
    )

    # Chưa liên kết ForeignKey vì báo cáo chưa cung cấp
    # cấu trúc bảng đơn hàng của hệ thống.

    MaDonHang = Char10Field(
        null=True,
        blank=True,
        db_column="MaDonHang"
    )

    LoaiGiaoDich = models.CharField(
        max_length=20,
        choices=LOAI_GIAO_DICH,
        db_column="LoaiGiaoDich"
    )

    SoDiem = models.IntegerField(
        db_column="SoDiem"
    )

    NoiDung = models.CharField(
        max_length=255,
        db_column="NoiDung"
    )

    SoDuDiem = models.PositiveIntegerField(
        db_column="SoDuDiem"
    )

    NgayTao = models.DateTimeField(
        auto_now_add=True,
        db_column="NgayTao"
    )

    class Meta:
        db_table = "LichSuTichDiem"
        ordering = ["-NgayTao"]
        verbose_name = "Lịch sử tích điểm"
        verbose_name_plural = "Lịch sử tích điểm"

    def __str__(self):
        return f"{self.MaKhachHang} - {self.SoDiem} điểm"


# =====================================================
# 6. BẢNG THÔNG BÁO
# =====================================================

class ThongBao(models.Model):

    LOAI_THONG_BAO = [
        ("DON_HANG", "Đơn hàng"),
        ("KHUYEN_MAI", "Khuyến mãi"),
        ("THANH_VIEN", "Khách hàng thân thiết"),
        ("HO_TRO", "Hỗ trợ"),
        ("TAI_KHOAN", "Tài khoản"),
    ]

    MaThongBao = Char10Field(
        primary_key=True,
        default=tao_ma,
        editable=False,
        db_column="MaThongBao"
    )

    MaNguoiNhan = models.ForeignKey(
        NguoiDung,
        on_delete=models.CASCADE,
        related_name="thong_bao_nhan",
        db_column="MaNguoiNhan"
    )

    MaNguoiGui = models.ForeignKey(
        NguoiDung,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="thong_bao_da_gui",
        db_column="MaNguoiGui"
    )

    TieuDe = models.CharField(
        max_length=150,
        db_column="TieuDe"
    )

    NoiDung = models.TextField(
        db_column="NoiDung"
    )

    LoaiThongBao = models.CharField(
        max_length=30,
        choices=LOAI_THONG_BAO,
        default="TAI_KHOAN",
        db_column="LoaiThongBao"
    )

    DaDoc = models.BooleanField(
        default=False,
        db_column="DaDoc"
    )

    NgayTao = models.DateTimeField(
        auto_now_add=True,
        db_column="NgayTao"
    )

    class Meta:
        db_table = "ThongBao"
        ordering = ["-NgayTao"]
        verbose_name = "Thông báo"
        verbose_name_plural = "Thông báo"

    def __str__(self):
        return self.TieuDe


# =====================================================
# 7. BẢNG YÊU CẦU HỖ TRỢ
# BỔ SUNG ĐỂ ĐÁP ỨNG USE CASE TRONG BÁO CÁO
# =====================================================

class YeuCauHoTro(models.Model):

    TRANG_THAI_CHOICES = [
        ("MOI", "Mới gửi"),
        ("DANG_XU_LY", "Đang xử lý"),
        ("DA_XU_LY", "Đã xử lý"),
        ("TU_CHOI", "Từ chối"),
    ]

    MaYeuCau = Char10Field(
        primary_key=True,
        default=tao_ma,
        editable=False,
        db_column="MaYeuCau"
    )

    MaKhachHang = models.ForeignKey(
        HoSoKhachHang,
        on_delete=models.CASCADE,
        related_name="yeu_cau_ho_tro",
        db_column="MaKhachHang"
    )

    TieuDe = models.CharField(
        max_length=150,
        db_column="TieuDe"
    )

    NoiDung = models.TextField(
        db_column="NoiDung"
    )

    TrangThai = models.CharField(
        max_length=20,
        choices=TRANG_THAI_CHOICES,
        default="MOI",
        db_column="TrangThai"
    )

    PhanHoi = models.TextField(
        null=True,
        blank=True,
        db_column="PhanHoi"
    )

    NguoiXuLy = models.ForeignKey(
        NguoiDung,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="yeu_cau_da_xu_ly",
        db_column="NguoiXuLy"
    )

    NgayTao = models.DateTimeField(
        auto_now_add=True,
        db_column="NgayTao"
    )

    NgayCapNhat = models.DateTimeField(
        auto_now=True,
        db_column="NgayCapNhat"
    )

    class Meta:
        db_table = "YeuCauHoTro"
        ordering = ["-NgayTao"]
        verbose_name = "Yêu cầu hỗ trợ"
        verbose_name_plural = "Yêu cầu hỗ trợ"

    def __str__(self):
        return self.TieuDe