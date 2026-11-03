from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Voucher(models.Model):

    MaVoucher = models.CharField(
        max_length=10,
        primary_key=True
    )

    TenVoucher = models.CharField(
        max_length=50
    )

    LoaiGiamGia = models.CharField(
        max_length=50,
        choices=[
            ('PhanTram', 'Giảm theo phần trăm'),
            ('SoTienCoDinh', 'Giảm số tiền cố định'),
        ]
    )

    DoiTuongApDung = models.CharField(
        max_length=50,
        choices=[
            ('TatCaThanhVien', 'Tất cả thành viên'),
            ('Dong', 'Hạng Đồng'),
            ('Bac', 'Hạng Bạc'),
            ('Vang', 'Hạng Vàng'),
            ('KimCuong', 'Hạng Kim cương'),
        ]
    )

    GiaTriGiam = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        validators=[
            MinValueValidator(0),
        ]
    )

    GioiHanSuDung = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    DieuKienGiam = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
        ]
    )

    NgayBatDau = models.DateTimeField()

    NgayKetThuc = models.DateTimeField()

    TrangThai = models.BooleanField(default=True)

    class Meta:
        db_table = 'Voucher'
        verbose_name = 'Voucher'
        verbose_name_plural = 'Quản lý Voucher'

    def __str__(self):
        return f'{self.MaVoucher} - {self.TenVoucher}'

    def clean(self):
        super().clean()

        if self.NgayBatDau and self.NgayKetThuc:
            if self.NgayKetThuc <= self.NgayBatDau:
                from django.core.exceptions import ValidationError
                raise ValidationError({
                    'NgayKetThuc': 'Ngày kết thúc phải sau ngày bắt đầu.'
                })

        if self.LoaiGiamGia == 'PhanTram':
            if self.GiaTriGiam is not None and self.GiaTriGiam > 100:
                from django.core.exceptions import ValidationError
                raise ValidationError({
                    'GiaTriGiam': 'Mức giảm phần trăm không được vượt quá 100%.'
                })
class VoucherKhachHang(models.Model):
    MaVoucherKhachHang = models.CharField(
        max_length=10,
        primary_key=True
    )

    MaVoucher = models.ForeignKey(
        Voucher,
        on_delete=models.CASCADE,
        db_column='MaVoucher',
        related_name='voucher_khach_hang'
    )

    # CHỜ TÍCH HỢP VỚI APP KHACHHANG
    # MaKhachHang = models.ForeignKey(
    #     'KHACHHANG.KhachHang',
    #     on_delete=models.CASCADE,
    #     db_column='MaKhachHang',
    #     related_name='voucher_da_nhan'
    # )

    # MaLichSuDiem = models.ForeignKey(
    #     'KHACHHANG.LichSuTichDiem',
    #     on_delete=models.PROTECT,
    #     db_column='MaLichSuDiem',
    #     related_name='voucher_da_doi'
    # )

    NgayLay = models.DateTimeField(auto_now_add=True)

    TrangThai = models.CharField(
        max_length=20,
        choices=[
            ('ChuaSuDung', 'Chưa sử dụng'),
            ('DaSuDung', 'Đã sử dụng'),
            ('HetHan', 'Hết hạn'),
        ],
        default='ChuaSuDung'
    )

    class Meta:
        db_table = 'VoucherKhachHang'
        verbose_name = 'Voucher khách hàng'
        verbose_name_plural = 'Quản lý voucher khách hàng'

    def __str__(self):
        return f'{self.MaVoucherKhachHang} - {self.MaVoucher}'