from django import forms
from django.contrib.auth import authenticate

from .models import (
    NguoiDung,
    HoSoKhachHang,
    SoDiaChi,
    YeuCauHoTro
)


# =====================================================
# FORM ĐĂNG KÝ
# =====================================================

class DangKyForm(forms.Form):

    TenDangNhap = forms.CharField(
        max_length=50,
        label="Tên đăng nhập",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Nhập tên đăng nhập"
        })
    )

    Email = forms.EmailField(
        max_length=100,
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Nhập email"
        })
    )

    HoVaTen = forms.CharField(
        max_length=100,
        label="Họ và tên",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Nhập họ và tên"
        })
    )

    SoDienThoai = forms.CharField(
        max_length=15,
        label="Số điện thoại",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Nhập số điện thoại"
        })
    )

    MatKhau = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Nhập mật khẩu"
        })
    )

    XacNhanMatKhau = forms.CharField(
        label="Xác nhận mật khẩu",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Nhập lại mật khẩu"
        })
    )

    def clean_TenDangNhap(self):
        TenDangNhap = self.cleaned_data["TenDangNhap"]

        if NguoiDung.objects.filter(
            TenDangNhap=TenDangNhap
        ).exists():
            raise forms.ValidationError(
                "Tên đăng nhập đã tồn tại."
            )

        return TenDangNhap

    def clean_Email(self):
        Email = self.cleaned_data["Email"]

        if NguoiDung.objects.filter(Email=Email).exists():
            raise forms.ValidationError(
                "Email đã được sử dụng."
            )

        return Email

    def clean_SoDienThoai(self):
        SoDienThoai = self.cleaned_data["SoDienThoai"]

        if not SoDienThoai.isdigit():
            raise forms.ValidationError(
                "Số điện thoại chỉ được chứa chữ số."
            )

        return SoDienThoai

    def clean(self):
        cleaned_data = super().clean()

        MatKhau = cleaned_data.get("MatKhau")
        XacNhanMatKhau = cleaned_data.get("XacNhanMatKhau")

        if MatKhau and XacNhanMatKhau:
            if MatKhau != XacNhanMatKhau:
                self.add_error(
                    "XacNhanMatKhau",
                    "Mật khẩu xác nhận không khớp."
                )

            if len(MatKhau) < 8:
                self.add_error(
                    "MatKhau",
                    "Mật khẩu phải có ít nhất 8 ký tự."
                )

        return cleaned_data


# =====================================================
# FORM ĐĂNG NHẬP
# =====================================================

class DangNhapForm(forms.Form):

    TenDangNhap = forms.CharField(
        label="Tên đăng nhập",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Nhập tên đăng nhập"
        })
    )

    MatKhau = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Nhập mật khẩu"
        })
    )


# =====================================================
# FORM CẬP NHẬT HỒ SƠ KHÁCH HÀNG
# =====================================================

class HoSoKhachHangForm(forms.ModelForm):

    Email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control"
        })
    )

    class Meta:
        model = HoSoKhachHang

        fields = [
            "HoVaTen",
            "SoDienThoai",
            "GioiTinh"
        ]

        widgets = {
            "HoVaTen": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "SoDienThoai": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "GioiTinh": forms.Select(attrs={
                "class": "form-control"
            }),
        }

    def __init__(self, *args, **kwargs):
        self.nguoi_dung = kwargs.pop("nguoi_dung", None)

        super().__init__(*args, **kwargs)

        if self.nguoi_dung:
            self.fields["Email"].initial = self.nguoi_dung.Email

    def clean_Email(self):
        Email = self.cleaned_data["Email"]

        trung_email = NguoiDung.objects.filter(
            Email=Email
        ).exclude(
            MaNguoiDung=self.nguoi_dung.MaNguoiDung
        ).exists()

        if trung_email:
            raise forms.ValidationError(
                "Email này đã được sử dụng."
            )

        return Email


# =====================================================
# FORM SỔ ĐỊA CHỈ
# =====================================================

class SoDiaChiForm(forms.ModelForm):

    class Meta:
        model = SoDiaChi

        fields = [
            "TenNguoiNhan",
            "SoDienThoai",
            "DiaChi",
            "MacDinh"
        ]

        widgets = {
            "TenNguoiNhan": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "SoDienThoai": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "DiaChi": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "MacDinh": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }


# =====================================================
# FORM GỬI YÊU CẦU HỖ TRỢ
# =====================================================

class YeuCauHoTroForm(forms.ModelForm):

    class Meta:
        model = YeuCauHoTro

        fields = [
            "TieuDe",
            "NoiDung"
        ]

        widgets = {
            "TieuDe": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nhập tiêu đề yêu cầu"
            }),

            "NoiDung": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Nhập nội dung cần hỗ trợ"
            }),
        }


# =====================================================
# FORM NHÂN VIÊN PHẢN HỒI YÊU CẦU HỖ TRỢ
# =====================================================

class PhanHoiHoTroForm(forms.ModelForm):

    class Meta:
        model = YeuCauHoTro

        fields = [
            "TrangThai",
            "PhanHoi"
        ]

        widgets = {
            "TrangThai": forms.Select(attrs={
                "class": "form-control"
            }),

            "PhanHoi": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4
            }),
        }