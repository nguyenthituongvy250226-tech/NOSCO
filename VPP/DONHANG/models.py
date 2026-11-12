

from django.db import models




class DonHang(models.Model):
   TRANG_THAI_CHOICES = [
       ("cho_xac_nhan", "Chờ xác nhận"),
       ("cho_lay_hang", "Chờ lấy hàng"),
       ("cho_giao_hang", "Chờ giao hàng"),
       ("da_giao", "Đã giao"),
       ("tra_hang", "Trả hàng"),
       ("da_huy", "Đã hủy"),
   ]


   ma_don_hang = models.CharField(
       max_length=10,
       primary_key=True,
       verbose_name="Mã đơn hàng",
   )
   ma_khach_hang = models.CharField(
       max_length=10,
       verbose_name="Mã khách hàng",
   )
   ma_dia_chi = models.CharField(
       max_length=10,
       verbose_name="Mã địa chỉ",
   )
   ma_voucher = models.CharField(
       max_length=10,
       blank=True,
       null=True,
       verbose_name="Mã voucher",
   )
   ngay_dat = models.DateTimeField(verbose_name="Ngày đặt")


   ten_nguoi_nhan = models.CharField(
       max_length=100,
       verbose_name="Tên người nhận",
   )
   sdt_nguoi_nhan = models.CharField(
       max_length=11,
       verbose_name="Số điện thoại người nhận",
   )
   dia_chi_nhan_hang = models.CharField(
       max_length=255,
       verbose_name="Địa chỉ nhận hàng",
   )


   trang_thai_don = models.CharField(
       max_length=50,
       choices=TRANG_THAI_CHOICES,
       default="cho_xac_nhan",
       verbose_name="Trạng thái đơn hàng",
   )


   # Khách đã xác nhận nhận hàng hay chưa.
   # Khi xác nhận, trạng thái đơn vẫn giữ là da_giao.
   khach_da_xac_nhan_nhan = models.BooleanField(default=False)


   tong_tien_hang = models.DecimalField(
       max_digits=15,
       decimal_places=0,
       default=0,
       verbose_name="Tổng tiền hàng",
   )
   so_tien_giam = models.DecimalField(
       max_digits=15,
       decimal_places=0,
       default=0,
       verbose_name="Số tiền giảm",
   )
   tong_tien = models.DecimalField(
       max_digits=15,
       decimal_places=0,
       default=0,
       verbose_name="Tổng tiền",
   )
   ghi_chu = models.CharField(
       max_length=300,
       blank=True,
       verbose_name="Ghi chú",
   )


   # Thông tin vận chuyển được lưu trực tiếp trong đơn hàng.
   don_vi_van_chuyen = models.CharField(
       max_length=100,
       blank=True,
       verbose_name="Đơn vị vận chuyển",
   )
   ma_van_don = models.CharField(
       max_length=100,
       blank=True,
       db_index=True,
       verbose_name="Mã vận đơn",
   )
   phi_van_chuyen = models.DecimalField(
       max_digits=15,
       decimal_places=0,
       default=0,
       verbose_name="Phí vận chuyển",
   )
   ly_do_that_bai = models.CharField(
       max_length=255,
       blank=True,
       verbose_name="Lý do giao thất bại",
   )
   ngay_ban_giao = models.DateTimeField(
       null=True,
       blank=True,
       verbose_name="Ngày bàn giao vận chuyển",
   )
   ngay_giao_thanh_cong = models.DateTimeField(
       null=True,
       blank=True,
       verbose_name="Ngày giao thành công",
   )
   cap_nhat_van_chuyen_luc = models.DateTimeField(
       null=True,
       blank=True,
       verbose_name="Cập nhật vận chuyển lúc",
   )
   ton_kho_da_tru = models.BooleanField(default=False)


   class Meta:
       verbose_name = "Đơn hàng"
       verbose_name_plural = "Đơn hàng"
       ordering = ["-ngay_dat"]


   def __str__(self):
       return self.ma_don_hang




class ChiTietDonHang(models.Model):
   ma_chi_tiet_dh = models.CharField(
       max_length=10,
       primary_key=True,
       verbose_name="Mã chi tiết đơn hàng",
   )
   ma_don_hang = models.ForeignKey(
       DonHang,
       on_delete=models.CASCADE,
       db_column="MaDonHang",
       related_name="chi_tiet",
       verbose_name="Đơn hàng",
   )
   ma_bien_the = models.CharField(
       max_length=10,
       verbose_name="Mã biến thể sản phẩm",
   )
   so_luong = models.PositiveIntegerField(verbose_name="Số lượng")
   don_gia = models.DecimalField(
       max_digits=15,
       decimal_places=0,
       verbose_name="Đơn giá",
   )
   thanh_tien = models.DecimalField(
       max_digits=15,
       decimal_places=0,
       verbose_name="Thành tiền",
   )


   class Meta:
       verbose_name = "Chi tiết đơn hàng"
       verbose_name_plural = "Chi tiết đơn hàng"


   def __str__(self):
       return self.ma_chi_tiet_dh




class YeuCauTraHang(models.Model):
   PHUONG_THUC_HOAN_TIEN_CHOICES = [
       ("tai_khoan_thanh_toan", "Hoàn tiền về tài khoản thanh toán"),
       ("vi_nosco", "Hoàn tiền vào ví NOSCO"),
   ]


   NGAN_HANG_CHOICES = [
       ("VCB", "Vietcombank"),
       ("BIDV", "BIDV"),
       ("CTG", "VietinBank"),
       ("TCB", "Techcombank"),
       ("MB", "MB Bank"),
       ("ACB", "ACB"),
       ("VPB", "VPBank"),
       ("TPB", "TPBank"),
       ("OTHER", "Ngân hàng khác"),
   ]


   # Đây là trạng thái của yêu cầu trả hàng,
   # không phải trạng thái của đơn hàng.
   TRANG_THAI_TRA_CHOICES = [
       ("cho_xu_ly", "Chờ xử lý"),
       ("da_duyet", "Đã duyệt"),
       ("cho_hoan_tien", "Đã nhận hàng - Chờ hoàn tiền"),
       ("hoan_tat", "Hoàn tất"),
       ("tu_choi", "Từ chối"),
   ]


   ma_yeu_cau_tra = models.CharField(
       max_length=10,
       primary_key=True,
       verbose_name="Mã yêu cầu trả hàng",
   )
   ma_don_hang = models.OneToOneField(
       DonHang,
       on_delete=models.CASCADE,
       db_column="MaDonHang",
       related_name="yeu_cau_tra_hang",
       verbose_name="Đơn hàng",
   )
   ma_thanh_toan = models.CharField(
       max_length=10,
       blank=True,
       default="",
   )
   ly_do_tra = models.CharField(
       max_length=255,
       verbose_name="Lý do trả hàng",
   )
   mo_ta_van_de = models.TextField(blank=True)
   ma_van_don_khach = models.CharField(
       max_length=100,
       blank=True,
   )


   phuong_thuc_hoan_tien = models.CharField(
       max_length=30,
       choices=PHUONG_THUC_HOAN_TIEN_CHOICES,
       default="tai_khoan_thanh_toan",
   )
   ngan_hang_hoan_tien = models.CharField(
       max_length=20,
       choices=NGAN_HANG_CHOICES,
       blank=True,
   )
   ten_chu_tai_khoan = models.CharField(
       max_length=100,
       blank=True,
   )
   so_tai_khoan = models.CharField(
       max_length=24,
       blank=True,
   )


   trang_thai_tra = models.CharField(
       max_length=50,
       choices=TRANG_THAI_TRA_CHOICES,
       default="cho_xu_ly",
       verbose_name="Trạng thái trả hàng",
   )
   ngay_tao = models.DateTimeField(
       auto_now_add=True,
       verbose_name="Ngày tạo yêu cầu",
   )
   ngay_xu_ly = models.DateTimeField(
       null=True,
       blank=True,
       verbose_name="Ngày xử lý",
   )
   ket_qua_xl = models.CharField(
       max_length=255,
       blank=True,
   )


   don_vi_van_chuyen_tra = models.CharField(
       max_length=100,
       blank=True,
   )
   ma_van_don_tra = models.CharField(
       max_length=100,
       blank=True,
   )


   class Meta:
       verbose_name = "Yêu cầu trả hàng"
       verbose_name_plural = "Yêu cầu trả hàng"


   def __str__(self):
       return self.ma_yeu_cau_tra




class ChiTietYeuCauTraHang(models.Model):
   yeu_cau = models.ForeignKey(
       YeuCauTraHang,
       on_delete=models.CASCADE,
       related_name="san_pham_tra",
   )
   chi_tiet_don_hang = models.ForeignKey(
       ChiTietDonHang,
       on_delete=models.PROTECT,
       related_name="yeu_cau_tra",
   )
   so_luong = models.PositiveIntegerField()


   class Meta:
       constraints = [
           models.UniqueConstraint(
               fields=("yeu_cau", "chi_tiet_don_hang"),
               name="uniq_san_pham_trong_yeu_cau_tra",
           )
       ]


   def __str__(self):
       return f"{self.yeu_cau_id}:{self.chi_tiet_don_hang_id}"




class BangChungYeuCauTraHang(models.Model):
   yeu_cau = models.ForeignKey(
       YeuCauTraHang,
       on_delete=models.CASCADE,
       related_name="minh_chung",
   )
   tep = models.FileField(
       upload_to="donhang/tra_hang/minh_chung/",
   )
   ten_tep = models.CharField(max_length=255)
   loai_tep = models.CharField(max_length=100, blank=True)
   ngay_tai_len = models.DateTimeField(auto_now_add=True)


   class Meta:
       ordering = ["ngay_tai_len"]


   def __str__(self):
       return self.ten_tep



