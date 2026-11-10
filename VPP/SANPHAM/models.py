
from django.db import models
from django.utils import timezone
from django.conf import settings

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
    logo = models.ImageField(
        upload_to="thuong_hieu/",
        blank=True,
        null=True
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

TRANG_THAI_CHOICES = [
    ("Đang bán", "Đang bán"),
    ("Ngừng bán", "Ngừng bán"),
]
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

class SanPhamQuaTang(models.Model):
    VI_TRI_CHOICES = [
        (1, "Vị trí 1"),
        (2, "Vị trí 2"),
        (3, "Vị trí 3"),
        (4, "Vị trí 4"),
        (5, "Vị trí 5"),
        (6, "Vị trí 6"),
        (7, "Vị trí 7"),
        (8, "Vị trí 8"),
    ]

    san_pham = models.OneToOneField(
        SanPham,
        on_delete=models.CASCADE,
        related_name="bo_suu_tap_qua_tang",
        db_column="MaSanPham",
    )

    vi_tri = models.PositiveSmallIntegerField(
        choices=VI_TRI_CHOICES,
        unique=True,
        db_column="ViTri",
    )

    class Meta:
        verbose_name = "Sản phẩm quà tặng"
        verbose_name_plural = "Bộ sưu tập quà tặng"
        ordering = ["vi_tri"]

    def __str__(self):
        return f"{self.vi_tri} - {self.san_pham.ten_san_pham}"
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

class BaiViet(models.Model):
    ma_bai_viet = models.CharField(
        max_length=10,
        primary_key=True,
        db_column="MaBaiViet",
    )

    tieu_de = models.CharField(
        max_length=200,
        db_column="TieuDe",
    )

    hinh_anh = models.ImageField(
        upload_to="bai_viet/",
        db_column="HinhAnh",
    )

    noi_dung = models.TextField(
        db_column="NoiDung",
    )

    ngay_dang = models.DateTimeField(
        default=timezone.now,
        db_column="NgayDang",
    )

    trang_thai = models.CharField(
        max_length=20,
        choices=[
            ("Bản nháp", "Bản nháp"),
            ("Đã đăng", "Đã đăng"),
        ],
        default="Bản nháp",
        db_column="TrangThai",
    )

    class Meta:
        verbose_name = "Bài viết"
        verbose_name_plural = "Bài viết"
        ordering = ["-ngay_dang"]

    def __str__(self):
        return self.tieu_de
class DanhGiaSanPham(models.Model):
    san_pham = models.ForeignKey(
        SanPham,
        on_delete=models.CASCADE,
        related_name="danh_gia"
    )

    # Lưu mã hồ sơ khách hàng NOSCO, không dùng ForeignKey xuyên database.
    ma_khach_hang = models.CharField(
        max_length=10,
        db_index=True,
        verbose_name="Mã khách hàng"
    )

    so_sao = models.PositiveSmallIntegerField(
        choices=[
            (1, "1 sao"),
            (2, "2 sao"),
            (3, "3 sao"),
            (4, "4 sao"),
            (5, "5 sao"),
        ]
    )

    noi_dung = models.TextField(max_length=1000)
    hinh_anh = models.ImageField(
        upload_to="danh_gia_san_pham/",
        null=True,
        blank=True,
        verbose_name="Hình ảnh đánh giá"
    )

    ngay_danh_gia = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ngay_danh_gia"]
        verbose_name = "Đánh giá sản phẩm"
        verbose_name_plural = "Đánh giá sản phẩm"

    def __str__(self):
        return f"{self.san_pham.ten_san_pham} - {self.so_sao} sao"

class SanPhamYeuThich(models.Model):
    ma_khach_hang = models.CharField(
        max_length=10,
        db_index=True,
        verbose_name="Mã khách hàng",
    )

    san_pham = models.ForeignKey(
        SanPham,
        on_delete=models.CASCADE,
        related_name="luot_yeu_thich",
        verbose_name="Sản phẩm",
    )

    ngay_them = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sản phẩm yêu thích"
        verbose_name_plural = "Sản phẩm yêu thích"
        constraints = [
            models.UniqueConstraint(
                fields=["ma_khach_hang", "san_pham"],
                name="unique_khach_hang_san_pham_yeu_thich",
            )
        ]

    def __str__(self):
        return f"{self.ma_khach_hang} - {self.san_pham.ten_san_pham}"