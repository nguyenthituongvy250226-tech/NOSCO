
from django.db import models
from django.db.models import Q
from django.utils import timezone


class GioHang(models.Model):
    ma_gio_hang = models.CharField(
        max_length=10,
        primary_key=True,
        db_column="MaGioHang",
    )

    ma_khach_hang = models.CharField(
        max_length=10,
        db_column="MaKhachHang",
    )

    ngay_tao = models.DateField(
        default=timezone.localdate,
        db_column="NgayTao",
    )

    ngay_cap_nhat = models.DateTimeField(
        auto_now=True,
        db_column="NgayCapNhat",
    )

    loai_gio_hang = models.BooleanField(
        default=False,
        db_column="LoaiGioHang",
    )

    class Meta:
        db_table = "GioHang"
        verbose_name = "Giỏ hàng"
        verbose_name_plural = "Giỏ hàng"

    def __str__(self):
        return self.ma_gio_hang


class ChiTietGioHang(models.Model):
    ma_chi_tiet_gio_hang = models.CharField(
        max_length=10,
        primary_key=True,
        db_column="MaChiTietGioHang",
    )

    gio_hang = models.ForeignKey(
        GioHang,
        on_delete=models.CASCADE,
        related_name="chi_tiet",
        db_column="MaGioHang",
    )

    ma_bien_the_sp = models.CharField(
        max_length=10,
        db_column="MaBienTheSP",
    )

    so_luong = models.IntegerField(
        db_column="SoLuong",
    )

    trang_thai_chon = models.BooleanField(
        default=False,
        db_column="TrangThaiChon",
    )
    constraints = [
        models.CheckConstraint(
            condition=Q(so_luong__gt=0),
            name="check_so_luong_gio_hang_lon_hon_0",
        ),
        models.UniqueConstraint(
            fields=["gio_hang", "ma_bien_the_sp"],
            name="uq_giohang_bienthe",
        ),
    ]
    class Meta:
        db_table = "ChiTietGioHang"
        verbose_name = "Chi tiết giỏ hàng"
        verbose_name_plural = "Chi tiết giỏ hàng"

        constraints = [
            models.CheckConstraint(
                condition=Q(so_luong__gt=0),
                name="check_so_luong_gio_hang_lon_hon_0",
            ),
        ]

        indexes = [
            models.Index(
                fields=["gio_hang"],
                name="idx_chitiet_giohang",
            ),
        ]

    def __str__(self):
        return self.ma_chi_tiet_gio_hang
class ChiaSeGioHang(models.Model):
    ma_chia_se = models.CharField(
        max_length=12,
        primary_key=True,
        db_column="MaChiaSe",
    )

    ma_khach_hang = models.CharField(
        max_length=10,
        db_column="MaKhachHang",
    )

    noi_dung = models.JSONField(
        default=list,
        db_column="NoiDung",
    )

    ngay_tao = models.DateTimeField(
        default=timezone.now,
        db_column="NgayTao",
    )

    class Meta:
        db_table = "ChiaSeGioHang"
        verbose_name = "Chia sẻ giỏ hàng"
        verbose_name_plural = "Chia sẻ giỏ hàng"

    def __str__(self):
        return self.ma_chia_se