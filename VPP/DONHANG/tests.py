from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from KHACHHANG.models import HoSoKhachHang, NguoiDung, SoDiaChi

from .models import ChiTietDonHang, DonHang, GiaoHang, YeuCauTraHang


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
class ReturnRequestPageTests(TestCase):
    databases = "__all__"

    def setUp(self):
        self.user = NguoiDung.objects.create_user(
            TenDangNhap="return-customer",
            Email="return-customer@example.com",
            password="SecurePassword123",
            VaiTro="KHACH_HANG",
        )
        self.profile = HoSoKhachHang.objects.create(
            MaNguoiDung=self.user,
            HoVaTen="Khách trả hàng",
            SoDienThoai="0912345678",
        )
        self.order = DonHang.objects.create(
            ma_don_hang="DHRETURN01",
            ma_khach_hang=self.profile.MaHoSo,
            ma_dia_chi="ADDR000001",
            ngay_dat=timezone.now(),
            ten_nguoi_nhan="Khách trả hàng",
            sdt_nguoi_nhan="0912345678",
            dia_chi_nhan_hang="Hà Nội",
            trang_thai_don="cho_giao_hang",
            tong_tien_hang=100000,
            tong_tien=100000,
        )
        self.item = ChiTietDonHang.objects.create(
            ma_chi_tiet_dh="ITEM000001",
            ma_don_hang=self.order,
            trang_thai_giao="da_giao",
            ma_bien_the="BT001",
            so_luong=2,
            don_gia=50000,
            thanh_tien=100000,
        )
        GiaoHang.objects.create(
            ma_giao_hang="SHIPRETURN01",
            don_hang=self.order,
            trang_thai="da_giao",
            ngay_giao_thanh_cong=timezone.now(),
        )
        session = self.client.session
        session["khachhang_ma_nguoi_dung"] = self.user.MaNguoiDung
        session["ma_khach_hang"] = self.profile.MaHoSo
        session["ten_dang_nhap"] = self.user.TenDangNhap
        session["vai_tro"] = self.user.VaiTro
        session.save()

    @override_settings(DEBUG=True)
    def test_customer_can_create_idempotent_order_test_data(self):
        SoDiaChi.objects.create(
            MaKhachHang=self.profile,
            TenNguoiNhan="Khách trả hàng",
            SoDienThoai="0912345678",
            DiaChi="Đà Nẵng",
            MacDinh=True,
        )

        page = self.client.get(reverse("DONHANG:danh_sach"))
        self.assertContains(page, "Tạo đơn hàng mẫu để kiểm thử")

        response = self.client.post(reverse("DONHANG:tao_don_hang_mau"))
        self.assertRedirects(
            response,
            reverse("DONHANG:danh_sach"),
            fetch_redirect_response=False,
        )
        sample_orders = DonHang.objects.filter(
            ma_khach_hang=self.profile.MaHoSo,
            ghi_chu__startswith="[ĐƠN HÀNG MẪU KIỂM THỬ]",
        )
        self.assertEqual(sample_orders.count(), 7)
        self.assertEqual(
            set(sample_orders.values_list("trang_thai_don", flat=True)),
            {
                "cho_xac_nhan",
                "cho_lay_hang",
                "cho_giao_hang",
                "cho_xac_nhan_nhan",
                "da_giao",
                "da_huy",
                "tra_hang",
            },
        )
        self.assertEqual(
            sample_orders.filter(thanh_toans__PhuongThucThanhToan="COD").count(),
            7,
        )

        self.client.post(reverse("DONHANG:tao_don_hang_mau"))
        self.assertEqual(sample_orders.count(), 7)

    @override_settings(DEBUG=True)
    def test_customer_can_create_sample_orders_without_a_saved_address(self):
        response = self.client.post(reverse("DONHANG:tao_don_hang_mau"))
        self.assertRedirects(
            response,
            reverse("DONHANG:danh_sach"),
            fetch_redirect_response=False,
        )

        sample_orders = DonHang.objects.filter(
            ma_khach_hang=self.profile.MaHoSo,
            ghi_chu__startswith="[ĐƠN HÀNG MẪU KIỂM THỬ]",
        )
        self.assertEqual(sample_orders.count(), 7)
        self.assertTrue(
            sample_orders.filter(
                dia_chi_nhan_hang__contains="chỉ dùng kiểm thử"
            ).exists()
        )
        return_order = sample_orders.get(trang_thai_don="tra_hang")
        self.assertTrue(
            YeuCauTraHang.objects.filter(ma_don_hang=return_order).exists()
        )

        order_awaiting_customer = sample_orders.get(
            trang_thai_don="cho_xac_nhan_nhan"
        )
        return_form = self.client.get(
            reverse(
                "DONHANG:yeu_cau_tra_hang",
                args=[order_awaiting_customer.pk],
            )
        )
        self.assertEqual(return_form.status_code, 200)

    @override_settings(DEBUG=False)
    def test_order_test_data_endpoint_is_disabled_outside_debug(self):
        response = self.client.post(reverse("DONHANG:tao_don_hang_mau"))
        self.assertEqual(response.status_code, 404)

    @override_settings(DEBUG=True)
    def test_order_test_data_uses_current_shipping_fee(self):
        SoDiaChi.objects.create(
            MaKhachHang=self.profile,
            TenNguoiNhan="Khách trả hàng",
            SoDienThoai="0912345678",
            DiaChi="Hà Nội",
            MacDinh=True,
        )

        self.client.post(reverse("DONHANG:tao_don_hang_mau"))
        don = DonHang.objects.filter(
            ma_khach_hang=self.profile.MaHoSo,
            ghi_chu__startswith="[ĐƠN HÀNG MẪU KIỂM THỬ]",
        ).first()

        self.assertEqual(don.giao_hang.phi_van_chuyen, Decimal("30000"))
        self.assertEqual(don.tong_tien, Decimal("35000"))

    def test_return_form_has_bank_refund_fields_and_guide_page_has_three_steps(self):
        form_response = self.client.get(
            reverse("DONHANG:yeu_cau_tra_hang", args=[self.order.pk])
        )
        guide_response = self.client.get(
            reverse("DONHANG:huong_dan_tra_hang", args=[self.order.pk])
        )

        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, "Chọn sản phẩm muốn trả")
        self.assertContains(form_response, "Hình ảnh/video minh chứng")
        self.assertContains(form_response, "Tên chủ tài khoản")
        self.assertContains(form_response, "Số tài khoản")
        self.assertEqual(guide_response.status_code, 200)
        self.assertContains(guide_response, "Đóng gói sản phẩm")
        self.assertContains(guide_response, "Dán mã vận đơn")
        self.assertContains(guide_response, "Đợi đơn vị vận chuyển đến lấy hàng")

    def test_staff_order_actions_are_only_shown_on_order_detail(self):
        employee = NguoiDung.objects.create_user(
            TenDangNhap="order-staff-test",
            Email="order-staff-test@example.com",
            password="SecurePassword123",
            VaiTro="NHAN_VIEN",
        )
        session = self.client.session
        session["khachhang_ma_nguoi_dung"] = employee.MaNguoiDung
        session["ten_dang_nhap"] = employee.TenDangNhap
        session["vai_tro"] = employee.VaiTro
        session.save()

        self.order.trang_thai_don = "cho_xac_nhan"
        self.order.save(update_fields=["trang_thai_don"])

        order_list = self.client.get(
            reverse("DONHANG:nhan_vien_don_hang")
        )
        self.assertEqual(order_list.status_code, 200)
        self.assertNotContains(order_list, "Xác nhận đơn")
        self.assertNotContains(order_list, 'name="ly_do_that_bai"')

        order_detail = self.client.get(
            reverse("DONHANG:chi_tiet", args=[self.order.pk])
        )
        self.assertEqual(order_detail.status_code, 200)
        self.assertContains(order_detail, "Xác nhận đơn")

    def test_customer_pending_order_shows_edit_and_cancel_actions(self):
        self.order.trang_thai_don = "cho_xac_nhan"
        self.order.save(update_fields=["trang_thai_don"])

        response = self.client.get(
            reverse("DONHANG:chi_tiet", args=[self.order.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chỉnh sửa đơn hàng")
        self.assertContains(response, "Hủy đơn hàng")
        self.assertNotContains(response, 'class="customer-account-sidebar"')

    def test_customer_can_cancel_cod_order_before_carrier_handoff(self):
        self.order.trang_thai_don = "cho_lay_hang"
        self.order.save(update_fields=["trang_thai_don"])
        self.order.giao_hang.trang_thai = "cho_lay_hang"
        self.order.giao_hang.ngay_giao_thanh_cong = None
        self.order.giao_hang.save(
            update_fields=["trang_thai", "ngay_giao_thanh_cong"]
        )

        detail = self.client.get(
            reverse("DONHANG:chi_tiet", args=[self.order.pk])
        )
        self.assertContains(detail, "Theo dõi đơn hàng")
        self.assertContains(detail, 'href="#order-shipping"')
        self.assertContains(detail, "Hủy đơn hàng")

        response = self.client.post(
            reverse("DONHANG:huy", args=[self.order.pk])
        )

        self.assertRedirects(
            response,
            reverse("DONHANG:chi_tiet", args=[self.order.pk]),
            fetch_redirect_response=False,
        )
        self.order.refresh_from_db()
        self.order.giao_hang.refresh_from_db()
        self.assertEqual(self.order.trang_thai_don, "da_huy")
        self.assertEqual(self.order.giao_hang.trang_thai, "giao_that_bai")

    def test_delivery_waiting_for_customer_is_not_marked_complete(self):
        response = self.client.get(
            reverse("DONHANG:chi_tiet", args=[self.order.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["trang_thai_hien_thi"], "Chờ giao hàng")
        self.assertFalse(response.context["cac_buoc"][3]["hoan_tat"])
        self.assertTrue(response.context["cac_buoc"][2]["hien_tai"])
        self.assertContains(response, "Chờ giao hàng")
        self.assertContains(response, "24 giờ")
        self.assertContains(response, "không thể yêu cầu trả hàng")
        self.assertContains(response, "Trả hàng")
        self.assertContains(response, "Đã nhận")

    def test_delivery_is_completed_after_customer_window_expires(self):
        self.order.giao_hang.ngay_giao_thanh_cong = (
            timezone.now() - timedelta(hours=25)
        )
        self.order.giao_hang.save(update_fields=["ngay_giao_thanh_cong"])

        response = self.client.get(
            reverse("DONHANG:chi_tiet", args=[self.order.pk])
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.trang_thai_don, "da_giao")
        self.assertEqual(response.context["trang_thai_hien_thi"], "Đã giao")
        self.assertTrue(response.context["cac_buoc"][3]["hoan_tat"])
        self.assertFalse(response.context["cac_buoc"][3]["hien_tai"])
        self.assertEqual(response.context["tien_do"], 100)
        self.assertContains(response, "Thời hạn lựa chọn trả hàng đã kết thúc")
        self.assertNotContains(
            response,
            reverse("DONHANG:huong_dan_tra_hang", args=[self.order.pk]),
        )

    def test_delivery_waiting_confirmation_is_counted_under_shipping_status(self):
        self.order.trang_thai_don = "cho_xac_nhan_nhan"
        self.order.save(update_fields=["trang_thai_don"])

        response = self.client.get(
            reverse("DONHANG:trang_thai", args=["cho-giao-hang"])
        )

        self.assertEqual(response.status_code, 200)
        shipping_status = next(
            status for status in response.context["cac_trang_thai"]
            if status["ma"] == "cho_giao_hang"
        )
        self.assertEqual(shipping_status["tong_so"], 1)
        self.assertEqual(len(response.context["don_hang"]), 1)
        self.assertContains(response, "Chờ giao hàng")

    def test_return_request_saves_bank_refund_details_and_shows_confirmation(self):
        response = self.client.post(
            reverse("DONHANG:yeu_cau_tra_hang", args=[self.order.pk]),
            {
                "chi_tiet_ids": [self.item.pk],
                f"so_luong_{self.item.pk}": "1",
                "ly_do_tra": "San pham bi loi/hong",
                "mo_ta_van_de": "Sản phẩm bị lỗi.",
                "phuong_thuc_hoan_tien": "tai_khoan_thanh_toan",
                "ngan_hang_hoan_tien": "VCB",
                "ten_chu_tai_khoan": "Khách trả hàng",
                "so_tai_khoan": "001234567890",
            },
        )

        yeu_cau = YeuCauTraHang.objects.get(ma_don_hang=self.order)
        self.assertRedirects(
            response,
            reverse("DONHANG:theo_doi_yeu_cau_tra", args=[self.order.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(yeu_cau.ngan_hang_hoan_tien, "VCB")
        self.assertEqual(yeu_cau.ten_chu_tai_khoan, "Khách trả hàng")
        self.assertEqual(yeu_cau.so_tai_khoan, "001234567890")

        confirmation = self.client.get(
            reverse("DONHANG:theo_doi_yeu_cau_tra", args=[self.order.pk])
        )
        self.assertContains(confirmation, "Yêu cầu đã được gửi thành công")
        self.assertContains(confirmation, yeu_cau.ma_yeu_cau_tra)
        self.assertContains(confirmation, "Hủy yêu cầu")

        detail = self.client.get(
            reverse("DONHANG:chi_tiet", args=[self.order.pk])
        )
        self.assertEqual(detail.context["trang_thai_hien_thi"], "Trả hàng")
        self.assertContains(detail, "Yêu cầu trả hàng của bạn đang được xử lý")
        self.assertContains(detail, 'id="return-request-details"')

        yeu_cau.trang_thai_tra = "da_duyet"
        yeu_cau.save(update_fields=["trang_thai_tra"])
        guide = self.client.get(
            reverse("DONHANG:huong_dan_tra_hang", args=[self.order.pk])
        )
        self.assertContains(guide, yeu_cau.ma_yeu_cau_tra)
        self.assertContains(guide, self.order.ma_don_hang)
        self.assertContains(guide, yeu_cau.ma_van_don_tra)

    def test_customer_can_cancel_pending_return_request(self):
        self.order.trang_thai_don = "tra_hang"
        self.order.save(update_fields=["trang_thai_don"])
        request = YeuCauTraHang.objects.create(
            ma_yeu_cau_tra="RTRETURN01",
            ma_don_hang=self.order,
            ly_do_tra="Sản phẩm bị lỗi",
        )

        detail = self.client.get(reverse("DONHANG:chi_tiet", args=[self.order.pk]))
        self.assertNotContains(detail, "Trạng thái yêu cầu trả hàng")
        self.assertContains(detail, 'href="#return-request-details"')
        self.assertContains(detail, 'id="return-request-details"')

        tracking = self.client.get(
            reverse("DONHANG:theo_doi_yeu_cau_tra", args=[self.order.pk])
        )
        self.assertContains(tracking, "Trạng thái xử lý")
        self.assertContains(tracking, "Hủy yêu cầu")
        self.assertGreater(
            tracking.content.index(b'class="return-detail-actions"'),
            tracking.content.index(b'class="return-tracking-card"'),
        )

        response = self.client.post(
            reverse("DONHANG:huy_yeu_cau_tra_hang", args=[self.order.pk])
        )

        self.assertRedirects(
            response,
            reverse("DONHANG:chi_tiet", args=[self.order.pk]),
            fetch_redirect_response=False,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.trang_thai_don, "cho_giao_hang")
        self.assertFalse(
            YeuCauTraHang.objects.filter(pk=request.pk).exists()
        )

    def test_customer_cannot_cancel_approved_return_request(self):
        self.order.trang_thai_don = "tra_hang"
        self.order.save(update_fields=["trang_thai_don"])
        request = YeuCauTraHang.objects.create(
            ma_yeu_cau_tra="RTRETURN02",
            ma_don_hang=self.order,
            ly_do_tra="Sản phẩm bị lỗi",
            trang_thai_tra="da_duyet",
        )

        response = self.client.post(
            reverse("DONHANG:huy_yeu_cau_tra_hang", args=[self.order.pk])
        )

        self.assertRedirects(
            response,
            reverse("DONHANG:chi_tiet", args=[self.order.pk]),
            fetch_redirect_response=False,
        )
        self.assertTrue(YeuCauTraHang.objects.filter(pk=request.pk).exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.trang_thai_don, "tra_hang")
