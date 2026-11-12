from django import forms


from .models import DonHang




class SuaDonHangForm(forms.ModelForm):
   class Meta:
       model = DonHang
       fields = ("ten_nguoi_nhan", "sdt_nguoi_nhan", "dia_chi_nhan_hang", "ghi_chu")
       widgets = {
           "ten_nguoi_nhan": forms.TextInput(attrs={"class": "form-control"}),
           "sdt_nguoi_nhan": forms.TextInput(attrs={"class": "form-control"}),
           "dia_chi_nhan_hang": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
           "ghi_chu": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
       }




class MultipleFileInput(forms.ClearableFileInput):
   allow_multiple_selected = True




class MultipleFileField(forms.FileField):
   widget = MultipleFileInput


   def clean(self, data, initial=None):
       clean_one = super().clean
       if isinstance(data, (list, tuple)):
           return [clean_one(file, initial) for file in data if file]
       cleaned = clean_one(data, initial)
       return [cleaned] if cleaned else []




class YeuCauTraHangForm(forms.Form):
   LY_DO_CHOICES = (
       ("San pham bi loi/hong", "Sản phẩm bị lỗi/hư hỏng"),
       ("Giao sai san pham", "Giao sai sản phẩm"),
       ("Khong dung mo ta", "Sản phẩm không đúng mô tả"),
       ("Thieu san pham", "Thiếu sản phẩm"),
       ("Khong con nhu cau", "Không còn nhu cầu"),
       ("Ly do khac", "Lý do khác"),
   )
   PHUONG_THUC_CHOICES = (
       ("tai_khoan_thanh_toan", "Hoàn tiền về tài khoản ngân hàng"),
   )
   NGAN_HANG_CHOICES = (
       ("", "Chọn ngân hàng"),
       ("VCB", "Vietcombank"),
       ("BIDV", "BIDV"),
       ("CTG", "VietinBank"),
       ("TCB", "Techcombank"),
       ("MB", "MB Bank"),
       ("ACB", "ACB"),
       ("VPB", "VPBank"),
       ("TPB", "TPBank"),
       ("OTHER", "Ngân hàng khác"),
   )


   ly_do_tra = forms.ChoiceField(label="Lý do trả hàng", choices=LY_DO_CHOICES)
   mo_ta_van_de = forms.CharField(
       max_length=1000,
       label="Mô tả vấn đề",
       widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Mô tả chi tiết vấn đề của sản phẩm..."}),
   )
   ma_van_don_khach = forms.CharField(
       max_length=100,
       required=False,
       label="Mã vận đơn",
       widget=forms.TextInput(attrs={"placeholder": "Nhập mã vận đơn nếu có"}),
   )
   phuong_thuc_hoan_tien = forms.ChoiceField(
       label="Phương thức hoàn tiền",
       choices=PHUONG_THUC_CHOICES,
       widget=forms.HiddenInput(),
       initial="tai_khoan_thanh_toan",
       required=False,
   )
   ngan_hang_hoan_tien = forms.ChoiceField(
       label="Ngân hàng",
       choices=NGAN_HANG_CHOICES,
       required=False,
   )
   ten_chu_tai_khoan = forms.CharField(
       label="Tên chủ tài khoản",
       max_length=100,
       required=False,
       widget=forms.TextInput(attrs={"autocomplete": "name"}),
   )
   so_tai_khoan = forms.RegexField(
       label="Số tài khoản",
       regex=r"^[0-9]{6,24}$",
       max_length=24,
       required=False,
       error_messages={"invalid": "Số tài khoản chỉ gồm 6–24 chữ số."},
       widget=forms.TextInput(attrs={
           "inputmode": "numeric",
           "autocomplete": "off",
           "placeholder": "Nhập số tài khoản ngân hàng",
       }),
   )


   tep_minh_chung = MultipleFileField(
       required=False,
       label="Hình ảnh/video minh chứng",
       widget=MultipleFileInput(attrs={"accept": "image/*,video/*"}),
   )
   chi_tiet_ids = forms.MultipleChoiceField(
       label="Sản phẩm muốn trả",
       widget=forms.CheckboxSelectMultiple,
       choices=(),
   )


   def __init__(self, *args, don_hang, phuong_thuc_thanh_toan, **kwargs):
       super().__init__(*args, **kwargs)
       self.don_hang = don_hang
       self.phuong_thuc_thanh_toan = phuong_thuc_thanh_toan


       self.fields["chi_tiet_ids"].choices = [
           (str(item.pk), f"{item.ma_bien_the} — số lượng đã mua: {item.so_luong}")
           for item in don_hang.chi_tiet.all()
       ]


       self.fields["phuong_thuc_hoan_tien"].widget = forms.HiddenInput()
       self.initial["phuong_thuc_hoan_tien"] = "tai_khoan_thanh_toan"


   def clean_chi_tiet_ids(self):
       ids = self.cleaned_data["chi_tiet_ids"]
       valid_ids = set(
           str(pk) for pk in self.don_hang.chi_tiet.values_list("pk", flat=True)
       )
       if not ids:
           raise forms.ValidationError("Hãy chọn ít nhất một sản phẩm muốn trả.")
       if not set(ids).issubset(valid_ids):
           raise forms.ValidationError("Sản phẩm được chọn không thuộc đơn hàng này.")
       return ids


   def clean(self):
       cleaned = super().clean()


       if self.phuong_thuc_thanh_toan in ("COD", "VNPAY"):
           required_fields = {
               "ngan_hang_hoan_tien": "Vui lòng chọn ngân hàng nhận tiền.",
               "ten_chu_tai_khoan": "Vui lòng nhập tên chủ tài khoản.",
               "so_tai_khoan": "Vui lòng nhập số tài khoản.",
           }


           for field, error in required_fields.items():
               if not cleaned.get(field):
                   self.add_error(field, error)


       return cleaned


   def clean_tep_minh_chung(self):
       files = self.cleaned_data["tep_minh_chung"]
       if len(files) > 5:
           raise forms.ValidationError("Bạn chỉ có thể tải tối đa 5 tệp minh chứng.")
       allowed_types = {
           "image/jpeg", "image/png", "image/webp", "image/gif",
           "video/mp4", "video/quicktime", "video/webm",
       }
       for file in files:
           if file.size > 10 * 1024 * 1024:
               raise forms.ValidationError("Mỗi tệp minh chứng không được vượt quá 10 MB.")
           if file.content_type not in allowed_types:
               raise forms.ValidationError("Tệp minh chứng chỉ hỗ trợ ảnh JPG, PNG, WEBP, GIF hoặc video MP4, MOV, WEBM.")
       return files




class XuLyYeuCauTraHangForm(forms.Form):
   hanh_dong = forms.ChoiceField(label="Kết quả")
   ket_qua_xl = forms.CharField(
       max_length=255,
       required=False,
       label="Ghi chú/kết quả xử lý",
       widget=forms.Textarea(attrs={"rows": 3}),
   )
   don_vi_van_chuyen_tra = forms.CharField(max_length=100, required=False, label="Đơn vị vận chuyển trả")
   ma_van_don_tra = forms.CharField(
       max_length=100, required=False, label="Mã vận đơn trả", disabled=True
   )


   def __init__(self, *args, yeu_cau, **kwargs):
       super().__init__(*args, **kwargs)
       self.yeu_cau = yeu_cau
       self.fields["ma_van_don_tra"].initial = f"MVD{yeu_cau.ma_yeu_cau_tra[2:]}"
       if yeu_cau.trang_thai_tra == "cho_xu_ly":
           self.fields["hanh_dong"].choices = (
               ("da_duyet", "Duyệt yêu cầu"),
               ("tu_choi", "Từ chối yêu cầu"),
           )
       elif yeu_cau.trang_thai_tra == "da_duyet":
           self.fields["hanh_dong"].choices = (("hoan_tat", "Đánh dấu hoàn tất"),)
       else:
           self.fields["hanh_dong"].choices = ()


   def clean(self):
       cleaned = super().clean()
       if cleaned.get("hanh_dong") == "da_duyet":
           if not cleaned.get("don_vi_van_chuyen_tra"):
               self.add_error("don_vi_van_chuyen_tra", "Cần cung cấp đơn vị vận chuyển trả.")
       if self.yeu_cau.trang_thai_tra == "da_duyet" and cleaned.get("hanh_dong") != "hoan_tat":
           self.add_error("hanh_dong", "Yêu cầu đã duyệt chỉ có thể được đánh dấu hoàn tất.")
       return cleaned



