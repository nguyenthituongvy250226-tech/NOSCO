from django.db import models


class ThanhToan(models.Model):

    MaThanhToan = models.CharField(
        max_length=10,
        primary_key=True
    )
# CHỜ MODEL ĐƠN HÀNG CỦA TÂM TỪ APP DON HANG ĐỂ PULL VỀ
    #MaDonHang = models.ForeignKey(
       # "DONHANG.DonHang",
        #on_delete=models.PROTECT,
        #db_column="MaDonHang"
    #)

    PhuongThucThanhToan = models.CharField(
        max_length=50,
        choices=[
            ('VNPAY', 'Thanh toán qua VNPay'),
            ('COD', 'Thanh toán khi nhận hàng'),
        ]
    )

    SoTienThanhToan = models.DecimalField(
        max_digits=19,
        decimal_places=4
    )

    TrangThaiThanhToan = models.CharField(
        max_length=50,
        choices=[
            ('ChoThanhToan', 'Đang chờ thanh toán'),
            ('DaThanhToan', 'Đã thanh toán'),
            ('ThatBai', 'Thất bại'),
            ('DaHoanTien', 'Đã hoàn tiền'),
        ],
        default='ChoThanhToan'
    )

    LoaiGiaoDich = models.CharField(
        max_length=50,
        choices=[
            ('ThanhToan', 'Thanh toán'),
            ('HoanTien', 'Hoàn tiền'),
        ],
        default='ThanhToan'
    )

    MaGiaoDich = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True
    )

    class Meta:
        verbose_name = "Thanh toán"
        verbose_name_plural = "Thanh toán"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(SoTienThanhToan__gt=0),
                name='check_so_tien_thanh_toan_positive'
            )
        ]

    def __str__(self):
        return self.MaThanhToan