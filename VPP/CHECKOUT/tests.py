from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import hashlib
import hmac
from urllib.parse import urlencode

from DONHANG.models import ChiTietDonHang, DonHang, GiaoHang
from GIOHANG.models import ChiTietGioHang, GioHang
from KHACHHANG.models import HoSoKhachHang, NguoiDung, SoDiaChi
from THANHTOAN.models import ThanhToan
from THANHTOAN.views import cap_nhat_giao_dich_vnpay
from DONHANG.services import (
    DuLieuDonHangKhongHopLe,
    het_han_don_chua_thanh_toan,
    xu_ly_don_hang,
)
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
class CheckoutOrderTests(TestCase):
    databases = "__all__"

    @classmethod
    def setUpTestData(cls):
        category = DanhMucSanPham.objects.using("sanpham").create(
            ma_danh_muc="DMCHECK",
            ten_danh_muc="Danh mục thử checkout",
        )
        brand = ThuongHieu.objects.using("sanpham").create(
            ma_thuong_hieu="THCHECK",
            ten_thuong_hieu="NOSCO",
        )
        product = SanPham.objects.using("sanpham").create(
            ma_san_pham="SPCHECK",
            danh_muc=category,
            thuong_hieu=brand,
            ten_san_pham="Sản phẩm thử checkout",
            trang_thai_ban="Đang bán",
        )
        BienTheSanPham.objects.using("sanpham").create(
            ma_bien_the="BT001",
            san_pham=product,
            mau_sac="Xanh",
            kich_thuoc="0.5mm",
            gia_ban=5000,
            so_luong_ton=100,
        )

    def test_checkout_creates_order_through_shared_order_service(self):
        user = NguoiDung.objects.create_user(
            TenDangNhap="checkout-test",
            Email="checkout-test@example.com",
            password="SecurePassword123",
            VaiTro="KHACH_HANG",
        )
        profile = HoSoKhachHang.objects.create(
            MaNguoiDung=user,
            HoVaTen="Khách checkout",
            SoDienThoai="0912345678",
        )
        address = SoDiaChi.objects.create(
            MaKhachHang=profile,
            TenNguoiNhan="Khách checkout",
            SoDienThoai="0912345678",
            DiaChi="123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng",
            MacDinh=True,
        )
        cart = GioHang.objects.create(
            ma_gio_hang="GH00000001",
            ma_khach_hang=profile.MaHoSo,
        )
        ChiTietGioHang.objects.create(
            ma_chi_tiet_gio_hang="CTGH000001",
            gio_hang=cart,
            ma_bien_the_sp="BT001",
            so_luong=2,
            trang_thai_chon=True,
        )

        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "checkout-test",
                "MatKhau": "SecurePassword123",
            },
        )
        checkout_page = self.client.get(reverse("checkout"))
        self.assertContains(checkout_page, "123 Nguyễn Văn Linh")

        response = self.client.post(reverse("checkout"), {"ghi_chu": "Giao giờ hành chính"})

        self.assertRedirects(
            response,
            reverse("DONHANG:danh_sach"),
            fetch_redirect_response=False,
        )
        order = DonHang.objects.get(ma_khach_hang=profile.MaHoSo)
        self.assertEqual(order.ma_dia_chi, address.MaDiaChi)
        self.assertEqual(order.tong_tien, 10000)
        self.assertEqual(
            GiaoHang.objects.get(don_hang=order).phi_van_chuyen,
            0,
        )
        self.assertEqual(
            ThanhToan.objects.get(DonHang=order).PhuongThucThanhToan,
            "COD",
        )
        self.assertEqual(
            ChiTietDonHang.objects.filter(ma_don_hang=order).count(),
            1,
        )
        self.assertFalse(cart.chi_tiet.exists())

    def test_checkout_requires_saved_address_and_keeps_cart_items(self):
        user = NguoiDung.objects.create_user(
            "checkout-no-address",
            "checkout-no-address@example.com",
            "SecurePassword123",
            VaiTro="KHACH_HANG",
        )
        profile = HoSoKhachHang.objects.create(
            MaNguoiDung=user,
            HoVaTen="Khách chưa có địa chỉ",
            SoDienThoai="0912345678",
        )
        cart = GioHang.objects.create(
            ma_gio_hang="GHNOADDR01",
            ma_khach_hang=profile.MaHoSo,
        )
        ChiTietGioHang.objects.create(
            ma_chi_tiet_gio_hang="CTNOADDR01",
            gio_hang=cart,
            ma_bien_the_sp="BT001",
            so_luong=1,
            trang_thai_chon=True,
        )
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "checkout-no-address",
                "MatKhau": "SecurePassword123",
            },
        )

        response = self.client.post(reverse("checkout"), {"phuong_thuc_thanh_toan": "COD"})

        self.assertRedirects(response, reverse("KHACHHANG:so_dia_chi"))
        self.assertFalse(DonHang.objects.filter(ma_khach_hang=profile.MaHoSo).exists())
        self.assertTrue(cart.chi_tiet.exists())

    def _tao_gio_hang_khach_hang(self, dia_chi):
        user = NguoiDung.objects.create_user(
            "checkout-vnpay",
            "checkout-vnpay@example.com",
            "SecurePassword123",
            VaiTro="KHACH_HANG",
        )
        profile = HoSoKhachHang.objects.create(
            MaNguoiDung=user,
            HoVaTen="Khách checkout VNPay",
            SoDienThoai="0912345678",
        )
        address = SoDiaChi.objects.create(
            MaKhachHang=profile,
            TenNguoiNhan="Khách checkout VNPay",
            SoDienThoai="0912345678",
            DiaChi=dia_chi,
            MacDinh=True,
        )
        cart = GioHang.objects.create(
            ma_gio_hang="GH00000003",
            ma_khach_hang=profile.MaHoSo,
        )
        ChiTietGioHang.objects.create(
            ma_chi_tiet_gio_hang="CTGH000003",
            gio_hang=cart,
            ma_bien_the_sp="BT001",
            so_luong=1,
            trang_thai_chon=True,
        )
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "checkout-vnpay",
                "MatKhau": "SecurePassword123",
            },
        )
        return profile, cart

    def test_vnpay_order_uses_shipping_fee_and_redirects_to_gateway(self):
        profile, cart = self._tao_gio_hang_khach_hang(
            "12 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh"
        )
        with override_settings(
            VNPAY_TMN_CODE="TESTCODE",
            VNPAY_HASH_SECRET="test-secret",
        ):
            response = self.client.post(
                reverse("checkout"),
                {"phuong_thuc_thanh_toan": "VNPAY"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn("sandbox.vnpayment.vn", response["Location"])
        order = DonHang.objects.get(ma_khach_hang=profile.MaHoSo)
        self.assertEqual(order.tong_tien, 35000)
        self.assertEqual(
            GiaoHang.objects.get(don_hang=order).phi_van_chuyen,
            30000,
        )
        self.assertEqual(
            ThanhToan.objects.get(DonHang=order).TrangThaiThanhToan,
            "ChoThanhToan",
        )
        self.assertFalse(cart.chi_tiet.exists())
        orders_page = self.client.get(reverse("DONHANG:danh_sach"))
        self.assertContains(orders_page, order.ma_don_hang)
        self.assertContains(orders_page, "Thanh toán lại")
        self.assertContains(orders_page, "trong vòng 24 giờ")

    def test_unpaid_vnpay_order_is_cancelled_after_24_hours(self):
        profile, _ = self._tao_gio_hang_khach_hang(
            "12 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh"
        )
        with override_settings(
            VNPAY_TMN_CODE="TESTCODE",
            VNPAY_HASH_SECRET="test-secret",
        ):
            self.client.post(
                reverse("checkout"),
                {"phuong_thuc_thanh_toan": "VNPAY"},
            )
        order = DonHang.objects.get(ma_khach_hang=profile.MaHoSo)
        DonHang.objects.filter(pk=order.pk).update(
            ngay_dat=timezone.now() - timedelta(hours=24, seconds=1)
        )

        self.assertEqual(het_han_don_chua_thanh_toan(), 1)

        order.refresh_from_db()
        self.assertEqual(order.trang_thai_don, "da_huy")
        self.assertEqual(
            ThanhToan.objects.get(DonHang=order).TrangThaiThanhToan,
            "ChoThanhToan",
        )

    def test_cod_order_is_not_cancelled_by_unpaid_payment_expiry(self):
        profile, _ = self._tao_gio_hang_khach_hang(
            "12 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh"
        )
        self.client.post(
            reverse("checkout"),
            {"phuong_thuc_thanh_toan": "COD"},
        )
        order = DonHang.objects.get(ma_khach_hang=profile.MaHoSo)
        DonHang.objects.filter(pk=order.pk).update(
            ngay_dat=timezone.now() - timedelta(hours=25)
        )

        self.assertEqual(het_han_don_chua_thanh_toan(), 0)

        order.refresh_from_db()
        self.assertEqual(order.trang_thai_don, "cho_xac_nhan")

    def test_staff_cannot_confirm_unpaid_vnpay_order(self):
        profile, _ = self._tao_gio_hang_khach_hang(
            "123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng"
        )
        with override_settings(
            VNPAY_TMN_CODE="TESTCODE",
            VNPAY_HASH_SECRET="test-secret",
        ):
            self.client.post(
                reverse("checkout"),
                {"phuong_thuc_thanh_toan": "VNPAY"},
            )
        order = DonHang.objects.get(ma_khach_hang=profile.MaHoSo)

        with self.assertRaises(DuLieuDonHangKhongHopLe):
            xu_ly_don_hang(order, hanh_dong="xac_nhan")

    def test_valid_vnpay_result_marks_order_payment_as_paid(self):
        profile, _ = self._tao_gio_hang_khach_hang(
            "123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng"
        )
        with override_settings(
            VNPAY_TMN_CODE="TESTCODE",
            VNPAY_HASH_SECRET="test-secret",
        ):
            self.client.post(
                reverse("checkout"),
                {"phuong_thuc_thanh_toan": "VNPAY"},
            )
            order = DonHang.objects.get(ma_khach_hang=profile.MaHoSo)
            payment = ThanhToan.objects.get(DonHang=order)
            params = {
                "vnp_TxnRef": payment.MaGiaoDich,
                "vnp_Amount": str(int(payment.SoTienThanhToan * 100)),
                "vnp_ResponseCode": "00",
                "vnp_TransactionStatus": "00",
            }
            params["vnp_SecureHash"] = hmac.new(
                b"test-secret",
                urlencode(sorted(params.items())).encode("utf-8"),
                hashlib.sha512,
            ).hexdigest()

            _, message, response_code, thanh_cong = cap_nhat_giao_dich_vnpay(
                params
            )

        payment.refresh_from_db()
        self.assertEqual(response_code, "00")
        self.assertEqual(message, "Confirm Success")
        self.assertTrue(thanh_cong)
        self.assertEqual(payment.TrangThaiThanhToan, "DaThanhToan")
