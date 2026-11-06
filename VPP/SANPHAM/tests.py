from django.test import TestCase, override_settings
from django.urls import reverse

from KHACHHANG.models import NguoiDung

from .models import DanhGiaSanPham, DanhMucSanPham, SanPham, ThuongHieu


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class ProductReviewTests(TestCase):
    databases = "__all__"

    def setUp(self):
        self.user = NguoiDung.objects.create_user(
            TenDangNhap="review-customer",
            Email="review-customer@example.com",
            password="review-password",
            VaiTro="KHACH_HANG",
        )
        self.category = DanhMucSanPham.objects.create(
            ma_danh_muc="REVCAT01",
            ten_danh_muc="Văn phòng phẩm",
        )
        self.brand = ThuongHieu.objects.create(
            ma_thuong_hieu="REVBRAND1",
            ten_thuong_hieu="NOSCO",
        )
        self.product = SanPham.objects.create(
            ma_san_pham="REVPROD001",
            danh_muc=self.category,
            thuong_hieu=self.brand,
            ten_san_pham="Sổ tay",
            trang_thai_ban="Đang bán",
        )
        self._login_as(self.user)

    def _login_as(self, user):
        session = self.client.session
        session["khachhang_ma_nguoi_dung"] = user.MaNguoiDung
        session["ma_khach_hang"] = ""
        session["ten_dang_nhap"] = user.TenDangNhap
        session["vai_tro"] = user.VaiTro
        session.save()

    def test_customer_can_create_edit_and_delete_own_review(self):
        url = reverse(
            "sanpham:chi_tiet_san_pham",
            args=[self.product.ma_san_pham],
        )
        created = self.client.post(url, {
            "hanh_dong": "luu_danh_gia",
            "so_sao": "5",
            "noi_dung": "Sản phẩm tốt",
        })

        self.assertRedirects(created, url, fetch_redirect_response=False)
        review = DanhGiaSanPham.objects.get(san_pham=self.product)
        self.assertEqual(review.nguoi_danh_gia, self.user.MaNguoiDung)
        self.assertContains(self.client.get(url), "review-customer")
        edit_page = self.client.get(f"{url}?sua_danh_gia={review.pk}")
        self.assertContains(edit_page, "Cập nhật đánh giá")
        self.assertContains(edit_page, f'href="{url}#reviews"')

        edited = self.client.post(url, {
            "hanh_dong": "luu_danh_gia",
            "review_id": review.pk,
            "so_sao": "4",
            "noi_dung": "Đã cập nhật",
        })
        self.assertRedirects(edited, url, fetch_redirect_response=False)
        review.refresh_from_db()
        self.assertEqual(review.so_sao, 4)
        self.assertEqual(review.noi_dung, "Đã cập nhật")

        deleted = self.client.post(url, {
            "hanh_dong": "xoa_danh_gia",
            "review_id": review.pk,
        })
        self.assertRedirects(deleted, url, fetch_redirect_response=False)
        self.assertFalse(DanhGiaSanPham.objects.filter(pk=review.pk).exists())

    def test_customer_cannot_edit_or_delete_another_customers_review(self):
        review = DanhGiaSanPham.objects.create(
            san_pham=self.product,
            nguoi_danh_gia=self.user.MaNguoiDung,
            so_sao=5,
            noi_dung="Đánh giá của người khác",
        )
        another_user = NguoiDung.objects.create_user(
            TenDangNhap="review-customer-2",
            Email="review-customer-2@example.com",
            password="review-password",
            VaiTro="KHACH_HANG",
        )
        self._login_as(another_user)
        url = reverse(
            "sanpham:chi_tiet_san_pham",
            args=[self.product.ma_san_pham],
        )

        edit = self.client.post(url, {
            "hanh_dong": "luu_danh_gia",
            "review_id": review.pk,
            "so_sao": "1",
            "noi_dung": "Sửa trái phép",
        })
        self.assertEqual(edit.status_code, 404)

        delete = self.client.post(url, {
            "hanh_dong": "xoa_danh_gia",
            "review_id": review.pk,
        })
        self.assertEqual(delete.status_code, 404)
        review.refresh_from_db()
        self.assertEqual(review.noi_dung, "Đánh giá của người khác")
