

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone


from .models import ThanhToan




class ThoiGianThanhToanFilter(admin.SimpleListFilter):
   title = "Thời gian thanh toán"
   parameter_name = "thoi_gian_thanh_toan"


   def lookups(self, request, model_admin):
       return (
           ("today", "Hôm nay"),
           ("7days", "7 ngày gần nhất"),
           ("30days", "30 ngày gần nhất"),
           ("this_month", "Tháng này"),
           ("last_month", "Tháng trước"),
       )


   def queryset(self, request, queryset):
       hien_tai = timezone.localtime(timezone.now())


       hom_nay = hien_tai.replace(
           hour=0,
           minute=0,
           second=0,
           microsecond=0,
       )


       lua_chon = self.value()


       if lua_chon == "today":
           return queryset.filter(
               NgayThanhToan__gte=hom_nay,
               NgayThanhToan__lt=hom_nay + timezone.timedelta(days=1),
           )


       elif lua_chon == "7days":
           return queryset.filter(
               NgayThanhToan__gte=hien_tai - timezone.timedelta(days=7),
               NgayThanhToan__lte=hien_tai,
           )


       elif lua_chon == "30days":
           return queryset.filter(
               NgayThanhToan__gte=hien_tai - timezone.timedelta(days=30),
               NgayThanhToan__lte=hien_tai,
           )


       elif lua_chon == "this_month":
           dau_thang = hom_nay.replace(day=1)


           return queryset.filter(
               NgayThanhToan__gte=dau_thang,
               NgayThanhToan__lte=hien_tai,
           )


       elif lua_chon == "last_month":
           dau_thang_nay = hom_nay.replace(day=1)


           if dau_thang_nay.month == 1:
               dau_thang_truoc = dau_thang_nay.replace(
                   year=dau_thang_nay.year - 1,
                   month=12,
               )
           else:
               dau_thang_truoc = dau_thang_nay.replace(
                   month=dau_thang_nay.month - 1,
               )


           return queryset.filter(
               NgayThanhToan__gte=dau_thang_truoc,
               NgayThanhToan__lt=dau_thang_nay,
           )


       return queryset




@admin.register(ThanhToan)
class ThanhToanAdmin(admin.ModelAdmin):


   list_display = (
       'hien_thi_ma_don_hang',
       'NgayThanhToan',
       'MaThanhToan',
       'hien_thi_phuong_thuc',
       'hien_thi_so_tien',
       'hien_thi_trang_thai',
       'hien_thi_loai_giao_dich',
       'MaGiaoDich',
   )


   list_filter = (
       'PhuongThucThanhToan',
       'TrangThaiThanhToan',
       'LoaiGiaoDich',
       ThoiGianThanhToanFilter,
   )


   search_fields = ('MaThanhToan', 'MaGiaoDich')
   ordering = ('-NgayThanhToan',)
   list_per_page = 20
   @admin.display(description='Phương thức thanh toán')
   def hien_thi_phuong_thuc(self, obj):
       return obj.get_PhuongThucThanhToan_display()


   @admin.display(description='Số tiền thanh toán', ordering='SoTienThanhToan')
   def hien_thi_so_tien(self, obj):
       return f"{obj.SoTienThanhToan:,.0f} VNĐ"


   @admin.display(description='Mã đơn hàng', ordering='DonHang')
   def hien_thi_ma_don_hang(self, obj):
       return obj.DonHang_id or "-"


   @admin.display(description='Trạng thái thanh toán')
   def hien_thi_trang_thai(self, obj):
       mau_sac = {
           'ChoThanhToan': '#D97706',
           'DaThanhToan': '#15803D',
           'ThatBai': '#DC2626',
           'DaHoanTien': '#2563EB',
       }


       mau = mau_sac.get(obj.TrangThaiThanhToan, '#64748B')


       return format_html(
           '<span style="color: {}; font-weight: 600;">{}</span>',
           mau,
           obj.get_TrangThaiThanhToan_display()
       )


   @admin.display(description='Loại giao dịch')
   def hien_thi_loai_giao_dich(self, obj):
       return obj.get_LoaiGiaoDich_display()


   fieldsets = (
       ('Thông tin thanh toán', {
           'fields': (
               'MaThanhToan',
               'PhuongThucThanhToan',
               'SoTienThanhToan',
               'TrangThaiThanhToan',
               'DonHang',
               'NgayThanhToan',
           )
       }),
       ('Thông tin giao dịch', {
           'fields': (
               'LoaiGiaoDich',
               'MaGiaoDich',
           )
       }),
   )


   readonly_fields = (
       'MaThanhToan',
       'PhuongThucThanhToan',
       'SoTienThanhToan',
       'LoaiGiaoDich',
       'MaGiaoDich',
       'DonHang',
       'NgayThanhToan',
   )


   def has_add_permission(self, request):
       return False


   def has_delete_permission(self, request, obj=None):
       return False

