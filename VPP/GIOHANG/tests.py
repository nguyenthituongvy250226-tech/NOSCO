from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ChiTietGioHang, GioHang
from KHACHHANG.models import HoSoKhachHang, NguoiDung
from SANPHAM.models import BienTheSanPham, DanhMucSanPham, SanPham, ThuongHieu


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
class CartPageTests(TestCase):
    databases = "__all__"

    @classmethod
    def setUpTestData(cls):
        category = DanhMucSanPham.objects.using("sanpham").create(
            ma_danh_muc="DMCART",
            ten_danh_muc="Danh mục thử giỏ hàng",
        )
        brand = ThuongHieu.objects.using("sanpham").create(
            ma_thuong_hieu="THCART",
            ten_thuong_hieu="NOSCO",
        )
        product = SanPham.objects.using("sanpham").create(
            ma_san_pham="SPCART",
            danh_muc=category,
            thuong_hieu=brand,
            ten_san_pham="Sản phẩm thử giỏ hàng",
            trang_thai_ban="Đang bán",
        )
        BienTheSanPham.objects.using("sanpham").create(
            ma_bien_the="BT001",
            san_pham=product,
            mau_sac="Xanh",
            kich_thuoc="0.5mm",
            gia_ban=5000,
            so_luong_ton=10,
        )

    def test_continue_shopping_links_to_home_route(self):
        user = NguoiDung.objects.create_user(
            TenDangNhap="cart-test",
            Email="cart-test@example.com",
            password="SecurePassword123",
        )
        profile = HoSoKhachHang.objects.create(
            MaNguoiDung=user,
            HoVaTen="Khách giỏ hàng",
            SoDienThoai="0912345678",
        )
        cart = GioHang.objects.create(
            ma_gio_hang="GH00000002",
            ma_khach_hang=profile.MaHoSo,
        )
        ChiTietGioHang.objects.create(
            ma_chi_tiet_gio_hang="CTGH000002",
            gio_hang=cart,
            ma_bien_the_sp="BT001",
            so_luong=1,
            trang_thai_chon=True,
        )
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "cart-test",
                "MatKhau": "SecurePassword123",
            },
        )
        response = self.client.get(reverse("xem_gio_hang"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("home")}" class="continue-shopping"',
        )

    def test_customer_can_add_catalog_product_to_cart(self):
        user = NguoiDung.objects.create_user(
            TenDangNhap="cart-add-test",
            Email="cart-add-test@example.com",
            password="SecurePassword123",
        )
        profile = HoSoKhachHang.objects.create(
            MaNguoiDung=user,
            HoVaTen="Khách thử giỏ hàng",
            SoDienThoai="0912345678",
        )
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {"TenDangNhap": "cart-add-test", "MatKhau": "SecurePassword123"},
        )

        detail = self.client.get(
            reverse("sanpham:chi_tiet_san_pham", args=["SPCART"])
        )
        self.assertContains(detail, "Thêm vào giỏ hàng")

        response = self.client.post(
            reverse("them_vao_gio"),
            {"bien_the": "BT001", "so_luong": "2"},
        )

        self.assertRedirects(response, reverse("xem_gio_hang"))
        cart = GioHang.objects.get(ma_khach_hang=profile.MaHoSo)
        line = cart.chi_tiet.get(ma_bien_the_sp="BT001")
        self.assertEqual(line.so_luong, 2)
        self.assertTrue(line.trang_thai_chon)
        self.assertContains(self.client.get(reverse("xem_gio_hang")), "Sản phẩm thử giỏ hàng")
