from decimal import Decimal
from types import SimpleNamespace

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from GIOHANG.views import (
    lay_gio_hang,
    bo_sung_thong_tin_san_pham,
)

from SANPHAM.models import BienTheSanPham
from KHACHHANG.models import HoSoKhachHang, SoDiaChi

# ==========================================
# CẤU HÌNH PHÍ VẬN CHUYỂN
# ==========================================

PHI_VAN_CHUYEN_TIEU_CHUAN = Decimal("30000")
KHU_VUC_MIEN_PHI = "Đà Nẵng"

# Lưu thông tin mua ngay trong session
SESSION_MUA_NGAY = "checkout_mua_ngay"


# ==========================================
# LẤY ẢNH ĐẠI DIỆN CỦA BIẾN THỂ
# ==========================================

def lay_anh_bien_the(bien_the):
    anh = (
        bien_the.hinh_anh.filter(anh_dai_dien=True).first()
        or bien_the.hinh_anh.order_by("thu_tu_hien_thi").first()
    )

    if anh and anh.duong_dan_anh:
        return anh.duong_dan_anh.url

    return ""


# ==========================================
# TẠO DỮ LIỆU SẢN PHẨM MUA NGAY
# ==========================================

def tao_san_pham_mua_ngay(ma_bien_the, so_luong):
    bien_the = get_object_or_404(
        BienTheSanPham.objects.select_related("san_pham"),
        ma_bien_the=ma_bien_the,
    )

    san_pham = bien_the.san_pham

    # Kiểm tra trạng thái kinh doanh
    if san_pham.trang_thai_ban != "Đang bán":
        raise ValueError("Sản phẩm hiện không được kinh doanh.")

    # Kiểm tra giá và tồn kho
    if bien_the.gia_ban is None or bien_the.gia_ban <= 0:
        raise ValueError("Giá bán của sản phẩm không hợp lệ.")

    if bien_the.so_luong_ton <= 0:
        raise ValueError("Sản phẩm hiện đã hết hàng.")

    if so_luong > bien_the.so_luong_ton:
        raise ValueError(
            f"Sản phẩm chỉ còn {bien_the.so_luong_ton} sản phẩm trong kho."
        )

    don_gia = Decimal(str(bien_the.gia_ban))
    thanh_tien = don_gia * so_luong

    # Tạo đối tượng tạm thời, KHÔNG lưu vào database
    item = SimpleNamespace(
        ma_bien_the_sp=bien_the.ma_bien_the,
        so_luong=so_luong,
        ten_san_pham=san_pham.ten_san_pham,
        mau_sac=bien_the.mau_sac,
        kich_thuoc=bien_the.kich_thuoc,
        don_gia=don_gia,
        so_luong_ton=bien_the.so_luong_ton,
        hinh_anh=lay_anh_bien_the(bien_the),
        thanh_tien=thanh_tien,
    )

    return item


# ==========================================
# TRANG THANH TOÁN
# ==========================================

@require_http_methods(["GET", "POST"])
def checkout(request):

    gio_hang = None
    danh_sach = []
    che_do_thanh_toan = "gio_hang"
    # ======================================
    # LẤY SỔ ĐỊA CHỈ CỦA KHÁCH HÀNG
    # ======================================

    ma_nguoi_dung = request.session.get("khachhang_ma_nguoi_dung")

    ho_so = None
    danh_sach_dia_chi = SoDiaChi.objects.none()
    dia_chi_obj = None

    if ma_nguoi_dung:
        ho_so = HoSoKhachHang.objects.filter(
            MaNguoiDung_id=ma_nguoi_dung
        ).first()

        if ho_so:
            danh_sach_dia_chi = SoDiaChi.objects.filter(
                MaKhachHang=ho_so
            ).order_by("-MacDinh", "TenNguoiNhan")

    # ======================================
    # XỬ LÝ KHI CHỌN ĐỊA CHỈ TRONG CHECKOUT
    # ======================================

    if (
            request.method == "POST"
            and request.POST.get("hanh_dong") == "chon_dia_chi"
    ):
        ma_dia_chi = request.POST.get("ma_dia_chi", "")

        dia_chi_chon = danh_sach_dia_chi.filter(
            MaDiaChi=ma_dia_chi
        ).first()

        if dia_chi_chon:
            request.session["checkout_ma_dia_chi"] = (
                dia_chi_chon.MaDiaChi
            )
            messages.success(request, "Đã cập nhật địa chỉ nhận hàng.")
        else:
            messages.error(request, "Địa chỉ không hợp lệ.")

        return redirect("CHECKOUT:checkout")

    # ======================================
    # LẤY ĐỊA CHỈ ĐANG ĐƯỢC CHỌN
    # ======================================

    ma_dia_chi_session = request.session.get(
        "checkout_ma_dia_chi"
    )

    if ma_dia_chi_session:
        dia_chi_obj = danh_sach_dia_chi.filter(
            MaDiaChi=ma_dia_chi_session
        ).first()

    # Nếu chưa chọn hoặc địa chỉ cũ không còn tồn tại
    if not dia_chi_obj:
        dia_chi_obj = (
                danh_sach_dia_chi.filter(MacDinh=True).first()
                or danh_sach_dia_chi.first()
        )

    if dia_chi_obj:
        request.session["checkout_ma_dia_chi"] = (
            dia_chi_obj.MaDiaChi
        )

        dia_chi = {
            "ma_dia_chi": dia_chi_obj.MaDiaChi,
            "ho_ten": dia_chi_obj.TenNguoiNhan,
            "so_dien_thoai": dia_chi_obj.SoDienThoai,
            "dia_chi": dia_chi_obj.DiaChi,
            "mac_dinh": dia_chi_obj.MacDinh,
        }
    else:
        dia_chi = None
    # ======================================
    # 1. XÁC ĐỊNH LUỒNG THANH TOÁN
    # ======================================

    # Trường hợp nhấn Mua ngay từ trang chi tiết
    if request.method == "POST" and request.POST.get("ma_bien_the"):

        ma_bien_the = request.POST.get("ma_bien_the", "").strip()

        try:
            so_luong = int(request.POST.get("so_luong", "1"))

            if so_luong < 1:
                raise ValueError

            item = tao_san_pham_mua_ngay(
                ma_bien_the,
                so_luong,
            )

        except (ValueError, TypeError):
            messages.error(
                request,
                "Số lượng sản phẩm không hợp lệ."
            )
            return redirect("sanpham:danh_sach_san_pham")

        except Exception as error:
            from django.http import Http404

            if isinstance(error, Http404):
                messages.error(
                    request,
                    "Không tìm thấy biến thể sản phẩm."
                )
            else:
                messages.error(request, str(error))

            return redirect("sanpham:danh_sach_san_pham")

        # Lưu thông tin mua ngay để checkout không bị mất
        # khi người dùng gửi form Đặt hàng.
        request.session[SESSION_MUA_NGAY] = {
            "ma_bien_the": str(ma_bien_the),
            "so_luong": so_luong,
        }

        che_do_thanh_toan = "mua_ngay"
        danh_sach = [item]

    # Trường hợp đang ở checkout và gửi form Đặt hàng
    elif (
        request.POST.get("che_do_thanh_toan") == "mua_ngay"
        or (
            request.method == "GET"
            and SESSION_MUA_NGAY in request.session
        )
    ):

        thong_tin_mua_ngay = request.session.get(SESSION_MUA_NGAY)

        if not thong_tin_mua_ngay:
            messages.warning(
                request,
                "Thông tin mua ngay không còn tồn tại. Vui lòng chọn lại sản phẩm."
            )
            return redirect("sanpham:danh_sach_san_pham")

        try:
            item = tao_san_pham_mua_ngay(
                thong_tin_mua_ngay["ma_bien_the"],
                int(thong_tin_mua_ngay["so_luong"]),
            )

        except Exception as error:
            messages.error(request, str(error))
            return redirect("sanpham:danh_sach_san_pham")

        che_do_thanh_toan = "mua_ngay"
        danh_sach = [item]

    # Trường hợp thanh toán từ giỏ hàng
    else:

        # Xóa thông tin mua ngay cũ nếu người dùng chọn
        # thanh toán theo giỏ hàng.
        if request.method == "POST":
            request.session.pop(SESSION_MUA_NGAY, None)

        gio_hang = lay_gio_hang(request)

        danh_sach = list(
            gio_hang.chi_tiet.filter(
                trang_thai_chon=True
            ).order_by("ma_chi_tiet_gio_hang")
        )

        if not danh_sach:
            messages.warning(
                request,
                "Bạn chưa chọn sản phẩm nào để thanh toán."
            )
            return redirect("GIOHANG:xem_gio_hang")

        danh_sach = bo_sung_thong_tin_san_pham(danh_sach)

        san_pham_khong_hop_le = [
            item for item in danh_sach
            if item.don_gia <= 0
            or item.so_luong_ton < item.so_luong
        ]

        if san_pham_khong_hop_le:
            messages.error(
                request,
                "Một số sản phẩm đã hết hàng hoặc không còn hợp lệ. "
                "Vui lòng kiểm tra lại giỏ hàng."
            )
            return redirect("GIOHANG:xem_gio_hang")

    # ======================================
    # 2. TÍNH TIỀN
    # ======================================

    tam_tinh = sum(
        (
            Decimal(str(item.thanh_tien))
            for item in danh_sach
        ),
        Decimal("0")
    )

    # ======================================
    # 3. THÔNG TIN NHẬN HÀNG TẠM THỜI
    # ======================================

    # ==========================================
    # 4. PHÍ VẬN CHUYỂN
    # ==========================================

    mien_phi = (
            dia_chi is not None
            and KHU_VUC_MIEN_PHI.casefold()
            in dia_chi["dia_chi"].casefold()
    )

    phi_van_chuyen = (
        Decimal("0")
        if mien_phi
        else PHI_VAN_CHUYEN_TIEU_CHUAN
    )

    tong_tien = tam_tinh + phi_van_chuyen
    # ======================================

    # ======================================

    # ======================================
    # 5. XỬ LÝ FORM ĐẶT HÀNG
    # ======================================

    # Không xử lý đặt hàng ở lần POST đầu tiên
    # khi khách nhấn Mua ngay từ trang sản phẩm.
    if request.method == "POST" and not request.POST.get("ma_bien_the"):

        ghi_chu = request.POST.get("ghi_chu", "").strip()

        khung_gio = request.POST.get(
            "khung_gio",
            "hanh_chinh"
        )

        van_chuyen = request.POST.get(
            "van_chuyen",
            "tieu_chuan"
        )

        phuong_thuc_thanh_toan = request.POST.get(
            "phuong_thuc_thanh_toan",
            ""
        )

        khung_gio_hop_le = [
            "hanh_chinh",
            "sang",
            "chieu",
        ]

        phuong_thuc_hop_le = [
            "vnpay",
            "cod",
        ]

        if khung_gio not in khung_gio_hop_le:
            messages.error(
                request,
                "Khung giờ giao hàng không hợp lệ."
            )
            return redirect("CHECKOUT:checkout")

        if van_chuyen != "tieu_chuan":
            messages.error(
                request,
                "Phương thức vận chuyển không hợp lệ."
            )
            return redirect("CHECKOUT:checkout")

        if phuong_thuc_thanh_toan not in phuong_thuc_hop_le:
            messages.error(
                request,
                "Vui lòng chọn phương thức thanh toán."
            )
            return redirect("CHECKOUT:checkout")

        # Hiện tại đã nhận và kiểm tra được phương thức thanh toán.
        # Phần tạo đơn hàng và tích hợp VNPay sẽ xử lý ở bước tiếp theo.



    # ======================================
    # 6. DỮ LIỆU TRUYỀN SANG TEMPLATE
    # ======================================

    context = {
        "gio_hang": gio_hang,
        "danh_sach": danh_sach,
        "dia_chi": dia_chi,
        "danh_sach_dia_chi": danh_sach_dia_chi,

        "tam_tinh": tam_tinh,
        "phi_van_chuyen": phi_van_chuyen,
        "tong_tien": tong_tien,

        "mien_phi": mien_phi,
        "che_do_thanh_toan": che_do_thanh_toan,
    }

    return render(
        request,
        "CHECKOUT/checkout.html",
        context
    )
def xem_trang_thanh_cong(request):
    return render(
        request,
        "CHECKOUT/dat_hang_thanh_cong.html"
    )