
from django import forms
from .models import DanhGiaSanPham


class DanhGiaSanPhamForm(forms.ModelForm):
    class Meta:
        model = DanhGiaSanPham
        fields = ["so_sao", "noi_dung","hinh_anh"]

        widgets = {
            "so_sao": forms.RadioSelect(),
            "noi_dung": forms.Textarea(attrs={
                "rows": 5,
                "maxlength": 1000,
                "placeholder": "Hãy chia sẻ cảm nhận của bạn về sản phẩm..."
            }),
        }

        labels = {
            "so_sao": "Đánh giá của bạn",
            "noi_dung": "Nhận xét sản phẩm",
        }
