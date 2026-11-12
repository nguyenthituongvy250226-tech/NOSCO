

from django.db import models


class ThanhToan(models.Model):


   MaThanhToan = models.CharField(
       max_length=10,
       primary_key=True
   )
   DonHang = models.ForeignKey(
       "DONHANG.DonHang",
       on_delete=models.SET_NULL,
       null=True,
       blank=True,
       related_name="thanh_toans",
       db_column="MaDonHang",
   )


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
           ('ChoHoanTien', 'Đang chờ xử lý hoàn tiền'),
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
   MaGiaoDichVNPay = models.CharField(
       max_length=15,
       null=True,
       blank=True,
       verbose_name="Mã giao dịch VNPay"
   )


   ThoiGianTaoVNPay = models.CharField(
       max_length=14,
       null=True,
       blank=True,
       verbose_name="Thời gian tạo giao dịch VNPay"
   )
   MaYeuCauHoanTienVNPay = models.CharField(
       max_length=32,
       null=True,
       blank=True,
       verbose_name="Mã yêu cầu hoàn tiền VNPay"
   )


   MaGiaoDichHoanTienVNPay = models.CharField(
       max_length=15,
       null=True,
       blank=True,
       verbose_name="Mã giao dịch hoàn tiền VNPay"
   )


   MaPhanHoiHoanTienVNPay = models.CharField(
       max_length=2,
       null=True,
       blank=True,
       verbose_name="Mã phản hồi API hoàn tiền VNPay"
   )


   TrangThaiHoanTienVNPay = models.CharField(
       max_length=2,
       null=True,
       blank=True,
       verbose_name="Trạng thái giao dịch hoàn tiền VNPay"
   )
   PhanHoiHoanTienVNPay = models.TextField(
       null=True,
       blank=True,
       verbose_name="Dữ liệu phản hồi hoàn tiền VNPay"
   )
   NgayThanhToan = models.DateTimeField(
       null=True,
       blank=True,
       verbose_name="Thời gian thanh toán"
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

