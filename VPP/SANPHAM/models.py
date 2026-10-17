
from django.db import models
from django.utils import timezone


class DanhMucSanPham(models.Model):
    ma_danh_muc = models.CharField(
        max_length=10,
        primary_key=True,
        db_column="MaDanhMuc",
    )
    ten_danh_muc = models.CharField(
        max_length=100,
        db_column="TenDanhMuc",
    )
    mo_ta = models.TextField(
        blank=True,
        db_column="MoTa",
    )
    danh_muc_cha = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="danh_muc_con",
        db_column="MaDanhMucCha",
    )

    class Meta:
        verbose_name = "Danh mục sản phẩm"
        verbose_name_plural = "Danh mục sản phẩm"
        ordering = ["ten_danh_muc"]

    def __str__(self):
        return self.ten_danh_muc


class ThuongHieu(models.Model):
    ma_thuong_hieu = models.CharField(
        max_length=10,
        primary_key=True,
        db_column="MaThuongHieu",
    )
    ten_thuong_hieu = models.CharField(
        max_length=100,
        db_column="TenThuongHieu",
    )
    logo = models.CharField(
        max_length=255,
        blank=True,
        db_column="Logo",
    )
    mo_ta = models.TextField(
        blank=True,
        db_column="MoTa",
    )

    class Meta:
        verbose_name = "Thương hiệu"
        verbose_name_plural = "Thương hiệu"
        ordering = ["ten_thuong_hieu"]

    def __str__(self):
        return self.ten_thuong_hieu


class SanPham(models.Model):
    TRANG_THAI_CHOICES = [
        ("Đang bán", "Đang bán"),
        ("Ngừng bán", "Ngừng bán"),
        ("Ẩn", "Ẩn"),
    ]

    ma_san_pham = models.CharField(
        max_length=10,
        primary_key=True,
        db_column="MaSanPham",
    )
    danh_muc = models.ForeignKey(
        DanhMucSanPham,
        on_delete=models.PROTECT,
        related_name="san_pham",
        db_column="MaDanhMuc",
    )
    thuong_hieu = models.ForeignKey(
        ThuongHieu,
        on_delete=models.PROTECT,
        related_name="san_pham",
        db_column="MaThuongHieu",
    )
    ten_san_pham = models.CharField(
        max_length=150,
        db_column="TenSanPham",
    )
    mo_ta = models.TextField(
        blank=True,
        db_column="MoTa",
    )
    trang_thai_ban = models.CharField(
        max_length=50,
        choices=TRANG_THAI_CHOICES,
        default="Đang bán",
        db_column="TrangThaiBan",
    )
    ngay_tao = models.DateField(
        default=timezone.localdate,
        db_column="NgayTao",
    )

    class Meta:
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Sản phẩm"
        ordering = ["ten_san_pham"]

    def __str__(self):
        return self.ten_san_pham


class BienTheSanPham(models.Model):
    ma_bien_the = models.CharField(
        max_length=10,
        primary_key=True,
        db_column="MaBienThe",
    )
    san_pham = models.ForeignKey(
        SanPham,
        on_delete=models.CASCADE,
        related_name="bien_the",
        db_column="MaSanPham",
    )
    mau_sac = models.CharField(
        max_length=50,
        blank=True,
        db_column="MauSac",
    )
    kich_thuoc = models.CharField(
        max_length=50,
        blank=True,
        db_column="KichThuoc",
    )
    gia_ban = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        db_column="GiaBan",
    )
    so_luong_ton = models.PositiveIntegerField(
        default=0,
        db_column="SoLuongTon",
    )

    class Meta:
        verbose_name = "Biến thể sản phẩm"
        verbose_name_plural = "Biến thể sản phẩm"

    def __str__(self):
        return f"{self.san_pham.ten_san_pham} - {self.ma_bien_the}"


class HinhAnhSanPham(models.Model):
    ma_hinh_anh = models.CharField(
        max_length=10,
        primary_key=True,
        db_column="MaHinhAnh",
    )
    bien_the = models.ForeignKey(
        BienTheSanPham,
        on_delete=models.CASCADE,
        related_name="hinh_anh",
        db_column="MaBienThe",
    )
    duong_dan_anh = models.ImageField(
        upload_to="products/",
        max_length=255,
        db_column="DuongDanAnh"
    )
    thu_tu_hien_thi = models.PositiveIntegerField(
        default=0,
        db_column="ThuTuHienThi",
    )
    anh_dai_dien = models.BooleanField(
        default=False,
        db_column="AnhDaiDien",
    )

    class Meta:
        verbose_name = "Hình ảnh sản phẩm"
        verbose_name_plural = "Hình ảnh sản phẩm"
        ordering = ["thu_tu_hien_thi"]

    def __str__(self):
        return f"Hình ảnh {self.ma_hinh_anh}"
