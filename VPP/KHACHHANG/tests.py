from django.test import TestCase, override_settings
from django.urls import reverse
from urllib.parse import parse_qs, urlparse
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from .models import HoSoKhachHang, NguoiDung, ThongBao
from GIOHANG.models import ChiTietGioHang, GioHang


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
class CustomerAccountPageTests(TestCase):
    databases = "__all__"

    def setUp(self):
        self.user = NguoiDung.objects.create_user(
            TenDangNhap="account-test",
            Email="account-test@example.com",
            password="SecurePassword123",
            VaiTro="KHACH_HANG",
        )
        HoSoKhachHang.objects.create(
            MaNguoiDung=self.user,
            HoVaTen="Khách hàng kiểm thử",
            SoDienThoai="0912345678",
        )

    def test_customer_login_opens_personal_account_page(self):
        response = self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )

        self.assertRedirects(
            response,
            reverse("KHACHHANG:ho_so_ca_nhan"),
            fetch_redirect_response=False,
        )

        response = self.client.get(reverse("KHACHHANG:ho_so_ca_nhan"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thông tin cá nhân")
        self.assertContains(response, "Khách hàng kiểm thử")
        self.assertContains(response, "account-test@example.com")
        self.assertContains(response, "Cập nhật thông tin cá nhân")

    def test_login_does_not_repeat_the_previous_logout_message(self):
        login_url = reverse("KHACHHANG:dang_nhap")
        credentials = {
            "TenDangNhap": "account-test",
            "MatKhau": "SecurePassword123",
        }
        self.client.post(login_url, credentials)
        self.client.get(reverse("KHACHHANG:dang_xuat"))

        response = self.client.post(login_url, credentials, follow=True)

        self.assertContains(response, "Đăng nhập thành công.")
        self.assertNotContains(response, "Bạn đã đăng xuất thành công.")

    def test_customer_can_upload_profile_photo(self):
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color="blue").save(image_buffer, format="PNG")

        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse("KHACHHANG:ho_so_ca_nhan"),
                {
                    "action": "upload_avatar",
                    "AnhDaiDien": SimpleUploadedFile(
                        "avatar.png",
                        image_buffer.getvalue(),
                        content_type="image/png",
                    ),
                },
            )

            self.assertRedirects(
                response,
                reverse("KHACHHANG:ho_so_ca_nhan"),
                fetch_redirect_response=False,
            )
            self.assertTrue(HoSoKhachHang.objects.get(pk=self.user.ho_so_khach_hang.pk).AnhDaiDien)

    def test_cart_page_does_not_render_removed_breadcrumb(self):
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )

        response = self.client.get(reverse("xem_gio_hang"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Trang chủ &gt; Giỏ hàng")

    def test_customer_login_returns_to_requested_page(self):
        response = self.client.post(
            f'{reverse("KHACHHANG:dang_nhap")}?next={reverse("xem_gio_hang")}',
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )

        self.assertRedirects(
            response,
            reverse("xem_gio_hang"),
            fetch_redirect_response=False,
        )

    def test_legacy_account_url_opens_customer_profile(self):
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )

        response = self.client.get(reverse("thong_tin_tai_khoan"))

        self.assertRedirects(
            response,
            reverse("KHACHHANG:ho_so_ca_nhan"),
            fetch_redirect_response=False,
        )

    def test_customer_can_log_out_and_returns_to_login(self):
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )

        response = self.client.get(reverse("KHACHHANG:dang_xuat"))

        self.assertRedirects(
            response,
            reverse("KHACHHANG:dang_nhap"),
            fetch_redirect_response=False,
        )
        self.assertNotIn("khachhang_ma_nguoi_dung", self.client.session)

        response = self.client.get(reverse("KHACHHANG:dang_nhap"))
        self.assertEqual(response.status_code, 200)

    def test_guest_can_browse_public_header_pages(self):
        public_routes = (
            "home",
            "ve_chung_toi",
            "danh_sach_bai_viet",
            "sanpham:danh_sach_san_pham",
            "sanpham:danh_sach_thuong_hieu",
            "sanpham:danh_sach_bai_viet",
            "khuyenmai:danh_sach_khuyen_mai",
        )

        for route_name in public_routes:
            with self.subTest(page=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_guest_is_redirected_to_login_for_account_and_shopping_pages(self):
        private_routes = (
            ("KHACHHANG:ho_so_ca_nhan", ()),
            ("DONHANG:danh_sach", ()),
            ("xem_gio_hang", ()),
            ("checkout", ()),
            ("sanpham:san_pham_yeu_thich", ()),
            ("sanpham:chi_tiet_san_pham", ("TEST-PRODUCT",)),
        )

        for route_name, args in private_routes:
            with self.subTest(page=route_name):
                protected_url = reverse(route_name, args=args or None)
                response = self.client.get(protected_url)
                self.assertEqual(response.status_code, 302)
                parsed_url = urlparse(response.url)
                self.assertEqual(
                    parsed_url.path,
                    reverse("KHACHHANG:dang_nhap"),
                )
                self.assertEqual(
                    parse_qs(parsed_url.query).get("next"),
                    [protected_url],
                )

    def test_logo_is_home_link_and_home_nav_item_is_removed(self):
        response = self.client.get(reverse("home"))

        self.assertContains(
            response,
            f'href="{reverse("home")}" aria-label="NOSCO - Trang chủ"',
        )
        self.assertNotContains(response, 'class="nav-home"')

    def test_account_menu_pages_render_after_login(self):
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )

        pages = (
            ("KHACHHANG:ho_so_ca_nhan", "Thông tin cá nhân"),
            ("KHACHHANG:so_dia_chi", "Sổ địa chỉ"),
            ("sanpham:san_pham_yeu_thich", "Sản phẩm yêu thích"),
            ("KHACHHANG:voucher_cua_toi", "Voucher của tôi"),
            ("KHACHHANG:lich_su_tich_diem", "Điểm tích lũy"),
            ("KHACHHANG:danh_sach_thong_bao", "Thông báo"),
            ("KHACHHANG:danh_sach_yeu_cau", "Hỗ trợ khách hàng"),
            ("DONHANG:danh_sach", "Đơn hàng của tôi"),
        )

        for route_name, heading in pages:
            with self.subTest(page=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, heading)
                self.assertContains(response, reverse("KHACHHANG:voucher_cua_toi"))

        self.assertContains(
            self.client.get(reverse("KHACHHANG:ho_so_ca_nhan")),
            reverse("KHACHHANG:dang_xuat"),
        )

    def test_support_is_in_site_header_and_customer_account_sidebar(self):
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )

        response = self.client.get(reverse("KHACHHANG:ho_so_ca_nhan"))

        self.assertContains(
            response,
            f'href="{reverse("KHACHHANG:danh_sach_yeu_cau")}"',
        )
        html = response.content.decode()
        account_nav = html.split(
            '<nav class="customer-account-nav"',
            maxsplit=1,
        )[1].split("</nav>", maxsplit=1)[0]
        self.assertIn("Hỗ trợ khách hàng", account_nav)
        self.assertContains(response, "Thông báo</span>")

    def test_header_shows_notification_preview_and_cart_quantity_badges(self):
        ThongBao.objects.create(
            MaNguoiNhan=self.user,
            TieuDe="Cập nhật đơn hàng",
            NoiDung="Đơn hàng đang được chuẩn bị.",
            LoaiThongBao="DON_HANG",
        )
        cart = GioHang.objects.create(
            ma_gio_hang="GHHEADER01",
            ma_khach_hang=self.user.ho_so_khach_hang.MaHoSo,
        )
        ChiTietGioHang.objects.create(
            ma_chi_tiet_gio_hang="CTHEADER01",
            gio_hang=cart,
            ma_bien_the_sp="BT001",
            so_luong=3,
        )
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )

        response = self.client.get(reverse("KHACHHANG:ho_so_ca_nhan"))

        self.assertContains(response, "Cập nhật đơn hàng")
        self.assertContains(response, 'aria-label="1 thông báo chưa đọc"')
        self.assertContains(response, 'aria-label="3 sản phẩm trong giỏ"')
        self.assertContains(response, 'href="/gio-hang/"')

    def test_notifications_can_be_filtered_into_customer_facing_categories(self):
        ThongBao.objects.create(
            MaNguoiNhan=self.user,
            TieuDe="Đơn hàng đang giao",
            NoiDung="Đơn hàng đã được bàn giao.",
            LoaiThongBao="DON_HANG",
        )
        ThongBao.objects.create(
            MaNguoiNhan=self.user,
            TieuDe="Voucher mới",
            NoiDung="Bạn có voucher mới.",
            LoaiThongBao="KHUYEN_MAI",
        )
        ThongBao.objects.create(
            MaNguoiNhan=self.user,
            TieuDe="Tin nhắn hỗ trợ",
            NoiDung="NOSCO đã phản hồi yêu cầu của bạn.",
            LoaiThongBao="HO_TRO",
        )
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )

        pages = (
            ("don-hang", "Đơn hàng đang giao", "Voucher mới"),
            ("khuyen-mai", "Voucher mới", "Đơn hàng đang giao"),
            ("cap-nhat", "Tin nhắn hỗ trợ", "Voucher mới"),
        )
        for category, expected, excluded in pages:
            with self.subTest(category=category):
                response = self.client.get(
                    reverse("KHACHHANG:danh_sach_thong_bao"),
                    {"nhom": category},
                )
                self.assertEqual(response.status_code, 200)
                titles = {
                    item.TieuDe
                    for item in response.context["danh_sach_thong_bao"]
                }
                self.assertIn(expected, titles)
                self.assertNotIn(excluded, titles)
                self.assertContains(response, "Khuyến mãi / Voucher")
                self.assertContains(response, "Cập nhật / Tin nhắn")

    def test_employee_keeps_store_navigation_and_sees_staff_account_actions(self):
        employee = NguoiDung.objects.create_user(
            TenDangNhap="employee-test",
            Email="employee-test@example.com",
            password="SecurePassword123",
            VaiTro="NHAN_VIEN",
        )
        ThongBao.objects.create(
            MaNguoiNhan=employee,
            TieuDe="Cập nhật hệ thống",
            NoiDung="Có thông báo mới dành cho nhân viên.",
            LoaiThongBao="TAI_KHOAN",
        )
        response = self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": employee.TenDangNhap,
                "MatKhau": "SecurePassword123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quản lý đơn hàng")
        self.assertContains(response, "Khu vực nhân viên")
        self.assertContains(response, 'aria-label="Mở menu tài khoản nhân viên"')
        self.assertContains(response, 'id="accountDropdown"')
        self.assertContains(response, "Thông báo")
        self.assertContains(response, "1 thông báo chưa đọc")
        self.assertContains(response, "Cập nhật hệ thống")
        self.assertContains(response, 'class="orders-layout"')
        self.assertContains(response, 'class="order-status-counts"')
        self.assertContains(response, "Danh mục sản phẩm")
        self.assertContains(response, "Về chúng tôi")
        self.assertContains(response, "Bài viết")
        self.assertContains(response, "Thương hiệu")
        self.assertContains(response, "Khuyến mãi")
        self.assertContains(response, "Trả hàng / hoàn tiền")
        self.assertContains(response, "Danh sách khách hàng")
        self.assertContains(response, "Yêu cầu hỗ trợ")
        self.assertNotContains(response, 'action-text"><span>Khách hàng</span>')
        self.assertNotContains(response, "Tài Khoản Của Tôi")
        self.assertNotContains(response, "Đơn Mua")
        self.assertNotContains(response, "Điều hướng nhân viên")
        self.assertNotContains(response, "class=\"cart-trigger\"")
        self.assertNotContains(response, "Yêu thích")

    def test_customer_order_page_uses_the_same_single_status_bar(self):
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )

        response = self.client.get(reverse("DONHANG:danh_sach"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="order-status-counts"')
        self.assertContains(response, "Trả hàng")
        self.assertNotContains(response, "Chờ xác nhận đã nhận")
        self.assertNotContains(response, 'class="orders-tabs"')
        self.assertEqual(
            [status["ten"] for status in response.context["cac_trang_thai"]],
            [
                "Tất cả",
                "Chờ xác nhận",
                "Chờ lấy hàng",
                "Chờ giao hàng",
                "Đã giao",
                "Trả hàng",
                "Đã hủy",
            ],
        )

    def test_staff_status_urls_are_short_and_show_order_counts(self):
        employee = NguoiDung.objects.create_user(
            TenDangNhap="employee-status-test",
            Email="employee-status-test@example.com",
            password="SecurePassword123",
            VaiTro="NHAN_VIEN",
        )
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": employee.TenDangNhap,
                "MatKhau": "SecurePassword123",
            },
        )

        response = self.client.get(
            reverse("DONHANG:trang_thai", kwargs={"trang_thai": "cho-xac-nhan"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/don-hang/trang-thai/cho-xac-nhan/"')
        self.assertContains(response, "Chờ xác nhận")
        for status in response.context["so_don_theo_trang_thai"]:
            self.assertEqual(status["tong_so"], 0)
        html = response.content.decode()
        self.assertIn('class="order-status-counts"', html)
        self.assertNotIn('class="orders-tabs"', html)

    def test_staff_management_pages_keep_the_account_shell(self):
        employee = NguoiDung.objects.create_user(
            TenDangNhap="employee-pages-test",
            Email="employee-pages-test@example.com",
            password="SecurePassword123",
            VaiTro="NHAN_VIEN",
        )
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": employee.TenDangNhap,
                "MatKhau": "SecurePassword123",
            },
        )

        pages = (
            reverse("KHACHHANG:danh_sach_khach_hang"),
            reverse("KHACHHANG:quan_ly_yeu_cau_ho_tro"),
            reverse("DONHANG:nhan_vien_tra_hang"),
        )
        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="customer-account-sidebar"')
                self.assertContains(response, "Quản lý đơn hàng")
                self.assertContains(response, "Yêu cầu hỗ trợ")

    def test_customer_cannot_open_employee_order_management(self):
        self.client.post(
            reverse("KHACHHANG:dang_nhap"),
            {
                "TenDangNhap": "account-test",
                "MatKhau": "SecurePassword123",
            },
        )
        self.client.raise_request_exception = False

        response = self.client.get(reverse("DONHANG:nhan_vien_don_hang"))

        self.assertEqual(response.status_code, 403)
