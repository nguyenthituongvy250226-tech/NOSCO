
from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta
import json

from KHACHHANG.models import HoSoKhachHang, NguoiDung, SoDiaChi

from django.db.models import Count, Q

from .forms import SuaDonHangForm, XuLyYeuCauTraHangForm, YeuCauTraHangForm
from .models import (
    ChiTietDonHang,
    BangChungYeuCauTraHang,
    DonHang,
    GiaoHang,
    ChiTietYeuCauTraHang,
    YeuCauTraHang,
)
from .services import (
    DuLieuDonHangKhongHopLe,
    cap_nhat_giao_hang,
    _ma,
    tinh_phi_van_chuyen,
    tao_don_hang,
    tao_yeu_cau_tra_hang,
    khach_huy_don_hang,
    cap_nhat_thong_tin_nhan,
    chot_don_cho_xac_nhan_qua_han,
    khach_xac_nhan_da_nhan,
    huy_yeu_cau_tra_hang as huy_yeu_cau_tra_hang_service,
    xu_ly_don_hang,
    xu_ly_yeu_cau_tra_hang,
)

MA_GHI_CHU_DON_MAU = "[ĐƠN HÀNG MẪU KIỂM THỬ]"


def _la_nhan_vien(request):
    return (
        request.user.is_authenticated
        and request.user.is_staff
    ) or getattr(getattr(request, "nguoi_dung", None), "VaiTro", None) == "NHAN_VIEN"


def staff_access_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_staff:
            return view_func(request, *args, **kwargs)

        user_id = request.session.get("khachhang_ma_nguoi_dung")
        if not user_id:
            login_url = reverse("KHACHHANG:dang_nhap")
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{login_url}?{query}")

        try:
            employee = NguoiDung.objects.get(
                MaNguoiDung=user_id,
                KichHoat=True,
                VaiTro="NHAN_VIEN",
            )
        except NguoiDung.DoesNotExist as exc:
            raise PermissionDenied from exc

        request.nguoi_dung = employee
        return view_func(request, *args, **kwargs)

    return wrapper


def _ma_khach_hang(request):
    """Account module sets this session key after customer sign-in."""
    return request.session.get("ma_khach_hang") or getattr(
        request.user, "ma_khach_hang", None
    )


def _ten_hien_thi_tai_khoan(request):
    user = request.user
    candidates = []
    if user.is_authenticated:
        candidates.append(getattr(user, "username", ""))
        get_full_name = getattr(user, "get_full_name", None)
        if callable(get_full_name):
            candidates.append(get_full_name())
        candidates.extend((
            getattr(user, "ho_ten", ""),
            getattr(user, "ten_khach_hang", ""),
        ))
    candidates.extend((
        request.session.get("ten_dang_nhap"),
        request.session.get("username"),
        request.session.get("ho_ten"),
        request.session.get("ten_khach_hang"),
    ))
    return next((str(value).strip() for value in candidates if value and str(value).strip()), "Khách hàng NOSCO")


def _don_cua_khach_hang(request, ma_don_hang):
    don = get_object_or_404(DonHang, ma_don_hang=ma_don_hang)
    if not _la_nhan_vien(request) and (
        not _ma_khach_hang(request)
        or don.ma_khach_hang != str(_ma_khach_hang(request))
    ):
        from django.http import Http404
        raise Http404
    return don


def _buoc_tien_do_tra_hang(yeu_cau):
    if not yeu_cau or yeu_cau.trang_thai_tra == "tu_choi":
        return []
    current = {"cho_xu_ly": 1, "da_duyet": 2, "hoan_tat": 3}.get(
        yeu_cau.trang_thai_tra, 0
    )
    labels = ["Đã gửi yêu cầu", "Đang xử lý", "Đã duyệt", "Hoàn tất"]
    return [
        {"ten": label, "hoan_tat": index < current, "hien_tai": index == current}
        for index, label in enumerate(labels)
    ]


def danh_sach_don_hang(request, trang_thai=None):
    from DONHANG.services import het_han_don_chua_thanh_toan

    het_han_don_chua_thanh_toan()
    chot_don_cho_xac_nhan_qua_han()
    don_hang_goc = DonHang.objects.all()
    dang_la_nhan_vien = _la_nhan_vien(request)
    if not dang_la_nhan_vien:
        customer_id = _ma_khach_hang(request)
        don_hang_goc = (
            don_hang_goc.filter(ma_khach_hang=customer_id)
            if customer_id
            else don_hang_goc.none()
        )

    trang_thai_slug = trang_thai
    if not trang_thai_slug:
        legacy_status = request.GET.get("trang_thai")
        legacy_status_map = {
            "all": "tat-ca",
            "cho_xac_nhan": "cho-xac-nhan",
            "cho_lay_hang": "cho-lay-hang",
            "cho_giao_hang": "cho-giao-hang",
            "cho_xac_nhan_nhan": "cho-giao-hang",
            "da_giao": "da-giao",
            "tra_hang": "tra-hang",
            "da_huy": "da-huy",
        }
        trang_thai_slug = legacy_status_map.get(legacy_status, "tat-ca")
    trang_thai = "all" if trang_thai_slug == "tat-ca" else trang_thai_slug
    if trang_thai_slug == "cho-xac-nhan-nhan":
        trang_thai_slug = "cho-giao-hang"
        trang_thai = trang_thai_slug
    tu_khoa = request.GET.get("q", "").strip()
    ngay_dat = request.GET.get("ngay_dat", "").strip()

    cac_trang_thai = [
        {"ma": "all", "slug": "tat-ca", "ten": "Tất cả"},
        {"ma": "cho_xac_nhan", "slug": "cho-xac-nhan", "ten": "Chờ xác nhận"},
        {"ma": "cho_lay_hang", "slug": "cho-lay-hang", "ten": "Chờ lấy hàng"},
        {"ma": "cho_giao_hang", "slug": "cho-giao-hang", "ten": "Chờ giao hàng"},
        {"ma": "da_giao", "slug": "da-giao", "ten": "Đã giao"},
        {"ma": "tra_hang", "slug": "tra-hang", "ten": "Trả hàng"},
        {"ma": "da_huy", "slug": "da-huy", "ten": "Đã hủy"},
    ]
    trang_thai_hop_le = {status["slug"]: status["ma"] for status in cac_trang_thai}
    if trang_thai_slug not in trang_thai_hop_le:
        from django.http import Http404
        raise Http404
    trang_thai = trang_thai_hop_le[trang_thai_slug]

    so_don_theo_trang_thai = dict(
        don_hang_goc.values("trang_thai_don")
        .annotate(tong_so=Count("ma_don_hang"))
        .values_list("trang_thai_don", "tong_so")
    )
    for status in cac_trang_thai:
        status["tong_so"] = (
            don_hang_goc.count()
            if status["ma"] == "all"
            else (
                so_don_theo_trang_thai.get("cho_giao_hang", 0)
                + so_don_theo_trang_thai.get("cho_xac_nhan_nhan", 0)
                if status["ma"] == "cho_giao_hang"
                else so_don_theo_trang_thai.get(status["ma"], 0)
            )
        )

    don_hang = don_hang_goc.select_related("giao_hang").prefetch_related(
        "chi_tiet", "thanh_toans"
    )
    # Lọc theo trạng thái
    if trang_thai == "cho_giao_hang":
        don_hang = don_hang.filter(
            Q(trang_thai_don="cho_giao_hang")
            | Q(trang_thai_don="cho_xac_nhan_nhan")
        )
    elif trang_thai != "all":
        don_hang = don_hang.filter(trang_thai_don=trang_thai)

    # Tìm theo mã đơn hàng hoặc mã biến thể sản phẩm
    if tu_khoa:
        don_hang = don_hang.filter(
            Q(ma_don_hang__icontains=tu_khoa)
            | Q(chi_tiet__ma_bien_the__icontains=tu_khoa)
        ).distinct()

    # Lọc theo ngày đặt
    if ngay_dat:
        don_hang = don_hang.filter(ngay_dat__date=ngay_dat)

    don_hang = list(don_hang)
    for don in don_hang:
        try:
            giao_hang = don.giao_hang
        except GiaoHang.DoesNotExist:
            giao_hang = None
        deadline = (
            giao_hang.ngay_giao_thanh_cong + timedelta(hours=24)
            if giao_hang and giao_hang.ngay_giao_thanh_cong else None
        )
        dang_cho_xac_nhan = bool(
            giao_hang
            and giao_hang.trang_thai == "da_giao"
            and deadline
            and timezone.now() <= deadline
            and not don.khach_da_xac_nhan_nhan
            and don.trang_thai_don in {
                "cho_giao_hang", "cho_xac_nhan_nhan", "da_giao"
            }
        )
        don.trang_thai_hien_thi = (
            "Chờ giao hàng"
            if dang_cho_xac_nhan or don.trang_thai_don == "cho_xac_nhan_nhan"
            else don.get_trang_thai_don_display()
        )
        thanh_toans = list(don.thanh_toans.all())
        don.thanh_toan_da_thanh_cong = any(
            payment.TrangThaiThanhToan == "DaThanhToan"
            for payment in thanh_toans
        )
        don.co_the_thanh_toan_lai = (
            don.trang_thai_don == "cho_xac_nhan"
            and not don.thanh_toan_da_thanh_cong
            and any(payment.PhuongThucThanhToan != "COD" for payment in thanh_toans)
        )

    context = {
        "don_hang": don_hang,
        "dang_la_nhan_vien": dang_la_nhan_vien,
        "ten_hien_thi": _ten_hien_thi_tai_khoan(request),
        "cac_trang_thai": cac_trang_thai,
        "trang_thai_hien_tai": trang_thai,
        "trang_thai_slug": trang_thai_slug,
        "so_don_theo_trang_thai": cac_trang_thai,
        "tu_khoa": tu_khoa,
        "ngay_dat": ngay_dat,
        "co_the_tao_don_mau": (
            settings.DEBUG
            and not dang_la_nhan_vien
            and bool(_ma_khach_hang(request))
            and not don_hang_goc.filter(
                ghi_chu__startswith=MA_GHI_CHU_DON_MAU
            ).exists()
        ),
    }

    return render(request, "donhang/danh_sach.html", context)


@require_POST
def tao_don_hang_mau(request):
    if not settings.DEBUG:
        raise Http404
    if _la_nhan_vien(request):
        raise PermissionDenied

    ma_khach_hang = _ma_khach_hang(request)
    nguoi_dung = getattr(request, "nguoi_dung", None)
    if not ma_khach_hang or nguoi_dung is None:
        return redirect("KHACHHANG:dang_nhap")

    ho_so = HoSoKhachHang.objects.filter(
        MaHoSo=ma_khach_hang,
        MaNguoiDung=nguoi_dung,
    ).first()
    if ho_so is None:
        messages.error(request, "Không tìm thấy hồ sơ khách hàng của bạn.")
        return redirect("KHACHHANG:ho_so_ca_nhan")

    dia_chi = SoDiaChi.objects.filter(
        MaKhachHang=ho_so,
    ).order_by("-MacDinh", "TenNguoiNhan").first()
    if dia_chi is None:
        thong_tin_nhan_hang = {
            "ma_dia_chi": "TESTADDR01",
            "ten_nguoi_nhan": ho_so.HoVaTen or nguoi_dung.TenDangNhap,
            "sdt_nguoi_nhan": ho_so.SoDienThoai or "0000000000",
            "dia_chi_nhan_hang": (
                "Đà Nẵng (địa chỉ giả lập, chỉ dùng kiểm thử)"
            ),
        }
    else:
        thong_tin_nhan_hang = {
            "ma_dia_chi": dia_chi.MaDiaChi,
            "ten_nguoi_nhan": dia_chi.TenNguoiNhan,
            "sdt_nguoi_nhan": dia_chi.SoDienThoai,
            "dia_chi_nhan_hang": dia_chi.DiaChi,
        }

    if DonHang.objects.filter(
        ma_khach_hang=ho_so.MaHoSo,
        ghi_chu__startswith=MA_GHI_CHU_DON_MAU,
    ).exists():
        messages.info(request, "Tài khoản đã có bộ đơn hàng mẫu để kiểm thử.")
        return redirect("DONHANG:danh_sach")

    cac_don_mau = [
        ("cho_xac_nhan", "Đơn mẫu — chờ xác nhận"),
        ("cho_lay_hang", "Đơn mẫu — chờ lấy hàng"),
        ("cho_giao_hang", "Đơn mẫu — đang vận chuyển"),
        ("cho_xac_nhan_nhan", "Đơn mẫu — giao thành công, chờ xác nhận"),
        ("da_giao", "Đơn mẫu — đã hoàn tất"),
        ("da_huy", "Đơn mẫu — đã hủy"),
        ("tra_hang", "Đơn mẫu — đang trả hàng"),
    ]

    try:
        with transaction.atomic():
            for trang_thai, mo_ta in cac_don_mau:
                don = tao_don_hang({
                    "ma_khach_hang": ho_so.MaHoSo,
                    **thong_tin_nhan_hang,
                    "ghi_chu": f"{MA_GHI_CHU_DON_MAU} {mo_ta}",
                    "phi_van_chuyen": str(
                        tinh_phi_van_chuyen(
                            thong_tin_nhan_hang["dia_chi_nhan_hang"]
                        )
                    ),
                    "items": [{
                        "ma_bien_the": "BT001",
                        "so_luong": 1,
                        "don_gia": "5000",
                    }],
                })
                from THANHTOAN.services import tao_thanh_toan_cho_don

                thanh_toan = tao_thanh_toan_cho_don(don, "COD")
                chi_tiet = don.chi_tiet.get()
                giao_hang = don.giao_hang

                if trang_thai == "cho_xac_nhan":
                    continue
                if trang_thai == "cho_lay_hang":
                    giao_hang.trang_thai = "cho_lay_hang"
                    chi_tiet.trang_thai_giao = "cho_lay_hang"
                elif trang_thai == "cho_giao_hang":
                    giao_hang.trang_thai = "dang_giao"
                    giao_hang.don_vi_van_chuyen = "NOSCO Express"
                    giao_hang.ma_van_don = f"TEST{don.pk}"
                    chi_tiet.trang_thai_giao = "cho_giao_hang"
                elif trang_thai == "cho_xac_nhan_nhan":
                    giao_hang.trang_thai = "da_giao"
                    giao_hang.don_vi_van_chuyen = "NOSCO Express"
                    giao_hang.ma_van_don = f"TEST{don.pk}"
                    giao_hang.ngay_giao_thanh_cong = timezone.now()
                    chi_tiet.trang_thai_giao = "da_giao"
                elif trang_thai == "da_giao":
                    don.khach_da_xac_nhan_nhan = True
                    don.save(update_fields=["khach_da_xac_nhan_nhan"])
                    giao_hang.trang_thai = "da_giao"
                    giao_hang.don_vi_van_chuyen = "NOSCO Express"
                    giao_hang.ma_van_don = f"TEST{don.pk}"
                    giao_hang.ngay_giao_thanh_cong = timezone.now() - timedelta(days=2)
                    chi_tiet.trang_thai_giao = "da_giao"
                elif trang_thai == "da_huy":
                    giao_hang.trang_thai = "giao_that_bai"
                    giao_hang.ly_do_that_bai = "Đơn mẫu kiểm thử"
                    chi_tiet.trang_thai_giao = "da_huy"
                elif trang_thai == "tra_hang":
                    don.trang_thai_don = "tra_hang"
                    don.save(update_fields=["trang_thai_don"])
                    giao_hang.trang_thai = "hoan_hang"
                    chi_tiet.trang_thai_giao = "da_giao"
                    yeu_cau_tra = YeuCauTraHang.objects.create(
                        ma_yeu_cau_tra=_ma("YT"),
                        ma_don_hang=don,
                        ma_thanh_toan=thanh_toan.MaThanhToan,
                        ly_do_tra="Sản phẩm mẫu cần kiểm tra",
                        mo_ta_van_de="Yêu cầu trả hàng mẫu để kiểm thử giao diện.",
                    )
                    ChiTietYeuCauTraHang.objects.create(
                        yeu_cau=yeu_cau_tra,
                        chi_tiet_don_hang=chi_tiet,
                        so_luong=1,
                    )

                giao_hang.save()
                chi_tiet.save()
                don.trang_thai_don = trang_thai
                don.save(update_fields=["trang_thai_don"])
    except DuLieuDonHangKhongHopLe as exc:
        messages.error(request, str(exc) or "Không thể tạo bộ đơn mẫu.")
        return redirect("DONHANG:danh_sach")

    messages.success(
        request,
        "Đã tạo 7 đơn hàng mẫu theo các trạng thái hiện có để bạn kiểm thử.",
    )
    return redirect("DONHANG:danh_sach")


def thong_tin_tai_khoan(request):
    """Giữ URL tài khoản cũ và đưa người dùng tới hồ sơ do module khách hàng quản lý."""
    return redirect("KHACHHANG:ho_so_ca_nhan")


# Chi tiết đơn hàng

def chi_tiet_don_hang(request, ma_don_hang):
    don_hang = _don_cua_khach_hang(request, ma_don_hang)
    chot_don_cho_xac_nhan_qua_han(ma_don_hang=don_hang.pk)
    don_hang = get_object_or_404(
        DonHang.objects.prefetch_related("chi_tiet"),
        pk=don_hang.pk,
    )

    chi_tiet = don_hang.chi_tiet.all()

    try:
        yeu_cau_tra = don_hang.yeu_cau_tra_hang
    except YeuCauTraHang.DoesNotExist:
        yeu_cau_tra = None

    context = {
        "don_hang": don_hang,
        "chi_tiet": chi_tiet,
        "yeu_cau_tra": yeu_cau_tra,
        "buoc_tien_do_tra": _buoc_tien_do_tra_hang(yeu_cau_tra),
        "dang_la_nhan_vien": _la_nhan_vien(request),
    }
    try:
        context["giao_hang"] = don_hang.giao_hang
    except GiaoHang.DoesNotExist:
        context["giao_hang"] = None
    delivered_at = (
        context["giao_hang"].ngay_giao_thanh_cong
        if context["giao_hang"] else None
    )
    context["giao_hang_thanh_cong"] = bool(
        context["giao_hang"]
        and context["giao_hang"].trang_thai == "da_giao"
        and delivered_at
    )
    han_tra_hang = delivered_at + timedelta(hours=24) if delivered_at else None
    context["trong_thoi_han_tra_hang"] = bool(
        context["giao_hang_thanh_cong"]
        and not don_hang.khach_da_xac_nhan_nhan
        and han_tra_hang
        and timezone.now() <= han_tra_hang
        and don_hang.trang_thai_don in {
            "cho_giao_hang", "cho_xac_nhan_nhan", "da_giao", "tra_hang"
        }
    )
    dang_cho_xac_nhan = (
        context["trong_thoi_han_tra_hang"] and not yeu_cau_tra
    )
    context["trang_thai_hien_thi"] = (
        "Trả hàng"
        if yeu_cau_tra
        else (
            "Chờ giao hàng"
            if dang_cho_xac_nhan or don_hang.trang_thai_don == "cho_xac_nhan_nhan"
            else don_hang.get_trang_thai_don_display()
        )
    )
    context["han_tra_hang"] = han_tra_hang
    context["co_the_tra_hang"] = bool(
        don_hang.trang_thai_don in {"cho_giao_hang", "cho_xac_nhan_nhan", "da_giao"}
        and context["giao_hang_thanh_cong"]
        and not don_hang.khach_da_xac_nhan_nhan
        and han_tra_hang
        and timezone.now() <= han_tra_hang
    )
    context["dang_cho_khach_chon"] = bool(
        context["trong_thoi_han_tra_hang"] and not yeu_cau_tra
    )
    context["khach_co_the_sua_don"] = (
        not context["dang_la_nhan_vien"]
        and don_hang.trang_thai_don == "cho_xac_nhan"
    )
    context["khach_co_the_huy_don"] = False
    if not context["dang_la_nhan_vien"]:
        context["khach_co_the_huy_don"] = (
            don_hang.trang_thai_don == "cho_xac_nhan"
            or (
                don_hang.trang_thai_don == "cho_lay_hang"
                and context["giao_hang"]
                and context["giao_hang"].trang_thai == "cho_lay_hang"
            )
        )
        if (
            context["khach_co_the_huy_don"]
            and don_hang.trang_thai_don == "cho_lay_hang"
        ):
            from THANHTOAN.models import ThanhToan

            context["khach_co_the_huy_don"] = not ThanhToan.objects.filter(
                DonHang=don_hang,
                TrangThaiThanhToan="DaThanhToan",
            ).exclude(PhuongThucThanhToan="COD").exists()
    status_steps = ["Chờ xác nhận", "Chờ lấy hàng", "Đang giao", "Đã giao"]
    status_index = 2 if dang_cho_xac_nhan else {
        "cho_xac_nhan": 0,
        "cho_lay_hang": 1,
        "cho_giao_hang": 2,
        "cho_xac_nhan_nhan": 2,
        "da_giao": 3,
        "tra_hang": 3,
    }.get(don_hang.trang_thai_don, -1)
    don_da_hoan_tat = don_hang.trang_thai_don == "da_giao"
    context["cac_buoc"] = [
        {
            "ten": label,
            "hoan_tat": index < status_index or (
                don_da_hoan_tat and index == status_index
            ),
            "hien_tai": index == status_index and not don_da_hoan_tat,
        }
        for index, label in enumerate(status_steps)
    ]
    context["tien_do"] = (
        100 if don_da_hoan_tat else max(status_index, 0) * 28
    )

    return render(
        request,
        "donhang/chi_tiet_don_hang.html",
        context,
    )


# API quản trị yêu cầu tài khoản nhân viên. App nội bộ gọi services trực tiếp.


def _don_hang_json(don):
    return {
        "ma_don_hang": don.ma_don_hang,
        "ma_khach_hang": don.ma_khach_hang,
        "ma_dia_chi": don.ma_dia_chi,
        "ma_voucher": don.ma_voucher,
        "ngay_dat": don.ngay_dat.isoformat(),
        "ten_nguoi_nhan": don.ten_nguoi_nhan,
        "sdt_nguoi_nhan": don.sdt_nguoi_nhan,
        "dia_chi_nhan_hang": don.dia_chi_nhan_hang,
        "ghi_chu": don.ghi_chu,
        "trang_thai_don": don.trang_thai_don,
        "tong_tien_hang": str(don.tong_tien_hang),
        "so_tien_giam": str(don.so_tien_giam),
        "tong_tien": str(don.tong_tien),
        "items": [{
            "ma_chi_tiet_dh": ct.ma_chi_tiet_dh,
            "ma_bien_the": ct.ma_bien_the,
            "so_luong": ct.so_luong,
            "don_gia": str(ct.don_gia),
            "thanh_tien": str(ct.thanh_tien),
            "trang_thai_giao": ct.trang_thai_giao,
        } for ct in don.chi_tiet.all()],
    }


@staff_access_required
@require_POST
def tao_don_hang_api(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        if not isinstance(data, dict):
            raise DuLieuDonHangKhongHopLe("JSON phải là một object.")
        don = tao_don_hang(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "JSON không hợp lệ."}, status=400)
    except DuLieuDonHangKhongHopLe as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(_don_hang_json(don), status=201)


@staff_access_required
@require_POST
def cap_nhat_giao_hang_api(request, ma_don_hang):
    don = get_object_or_404(DonHang, ma_don_hang=ma_don_hang)
    try:
        data = json.loads(request.body.decode("utf-8"))
        if not isinstance(data, dict):
            raise DuLieuDonHangKhongHopLe("JSON phải là một object.")
        giao = cap_nhat_giao_hang(
            don,
            trang_thai=data.get("trang_thai", ""),
            don_vi_van_chuyen=data.get("don_vi_van_chuyen"),
            ma_van_don=data.get("ma_van_don"),
            ly_do_that_bai=data.get("ly_do_that_bai"),
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "JSON không hợp lệ."}, status=400)
    except DuLieuDonHangKhongHopLe as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    don.refresh_from_db()
    return JsonResponse({
        "ma_don_hang": don.ma_don_hang,
        "trang_thai_don": don.trang_thai_don,
        "giao_hang": {
            "ma_giao_hang": giao.ma_giao_hang,
            "trang_thai": giao.trang_thai,
            "don_vi_van_chuyen": giao.don_vi_van_chuyen,
            "ma_van_don": giao.ma_van_don,
            "phi_van_chuyen": str(giao.phi_van_chuyen),
            "ly_do_that_bai": giao.ly_do_that_bai,
        },
    })


@staff_access_required
def tra_cuu_don_hang_api(request, ma_don_hang):
    don = get_object_or_404(
        DonHang.objects.prefetch_related("chi_tiet"), ma_don_hang=ma_don_hang
    )
    payload = _don_hang_json(don)
    try:
        giao = don.giao_hang
        payload["giao_hang"] = {
            "ma_giao_hang": giao.ma_giao_hang,
            "trang_thai": giao.trang_thai,
            "don_vi_van_chuyen": giao.don_vi_van_chuyen,
            "ma_van_don": giao.ma_van_don,
            "phi_van_chuyen": str(giao.phi_van_chuyen),
            "ly_do_that_bai": giao.ly_do_that_bai,
        }
    except GiaoHang.DoesNotExist:
        payload["giao_hang"] = None
    return JsonResponse(payload)


def sua_don_hang(request, ma_don_hang):
    don = _don_cua_khach_hang(request, ma_don_hang)
    if don.trang_thai_don != "cho_xac_nhan":
        messages.error(request, "Chỉ sửa được đơn đang chờ xác nhận.")
        return redirect("DONHANG:chi_tiet", ma_don_hang=don.pk)
    form = SuaDonHangForm(request.POST or None, instance=don)
    if request.method == "POST" and form.is_valid():
        try:
            cap_nhat_thong_tin_nhan(don, **form.cleaned_data)
        except DuLieuDonHangKhongHopLe as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Thông tin nhận hàng đã được cập nhật.")
            return redirect("DONHANG:chi_tiet", ma_don_hang=don.pk)
    return render(request, "donhang/sua_don.html", {"form": form, "don_hang": don})


@require_POST
def huy_don_hang(request, ma_don_hang):
    don = _don_cua_khach_hang(request, ma_don_hang)
    try:
        khach_huy_don_hang(don)
    except DuLieuDonHangKhongHopLe as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Đơn hàng đã được hủy.")
    return redirect("DONHANG:chi_tiet", ma_don_hang=don.pk)


def huong_dan_tra_hang(request, ma_don_hang):
    don = _don_cua_khach_hang(request, ma_don_hang)
    chot_don_cho_xac_nhan_qua_han(ma_don_hang=don.pk)
    don.refresh_from_db()
    yeu_cau_tra = YeuCauTraHang.objects.filter(ma_don_hang=don).first()
    try:
        giao = don.giao_hang
    except GiaoHang.DoesNotExist:
        giao = None
    deadline = giao.ngay_giao_thanh_cong + timedelta(hours=24) if giao and giao.ngay_giao_thanh_cong else None
    if not yeu_cau_tra and (
        don.trang_thai_don not in {"cho_giao_hang", "cho_xac_nhan_nhan", "da_giao"}
        or not giao
        or giao.trang_thai != "da_giao"
        or don.khach_da_xac_nhan_nhan
        or not deadline
        or timezone.now() > deadline
    ):
        messages.error(request, "Đơn hàng không còn đủ điều kiện yêu cầu trả hàng.")
        return redirect("DONHANG:chi_tiet", ma_don_hang=don.pk)
    return render(request, "donhang/huong_dan_tra_hang.html", {
        "don_hang": don,
        "return_deadline": deadline,
        "yeu_cau_tra": yeu_cau_tra,
    })


def huong_dan_tra_hang_chung(request):
    return render(request, "donhang/huong_dan_tra_hang_chung.html")


@require_POST
def xac_nhan_da_nhan(request, ma_don_hang):
    don = _don_cua_khach_hang(request, ma_don_hang)
    chot_don_cho_xac_nhan_qua_han(ma_don_hang=don.pk)
    try:
        khach_xac_nhan_da_nhan(don)
    except DuLieuDonHangKhongHopLe as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Bạn đã xác nhận nhận hàng. Đơn hàng đã hoàn tất.")
    return redirect("DONHANG:chi_tiet", ma_don_hang=don.pk)


def yeu_cau_tra_hang(request, ma_don_hang):
    don = _don_cua_khach_hang(request, ma_don_hang)
    chot_don_cho_xac_nhan_qua_han(ma_don_hang=don.pk)
    try:
        giao = don.giao_hang
    except GiaoHang.DoesNotExist:
        giao = None
    delivered_at = giao.ngay_giao_thanh_cong if giao else None
    deadline = delivered_at + timedelta(hours=24) if delivered_at else None
    if (
        don.trang_thai_don not in {"cho_giao_hang", "cho_xac_nhan_nhan", "da_giao"}
        or not giao
        or giao.trang_thai != "da_giao"
        or don.khach_da_xac_nhan_nhan
        or not delivered_at
        or timezone.now() > deadline
    ):
        messages.error(request, "Đơn hàng không còn đủ điều kiện yêu cầu trả hàng.")
        return redirect("DONHANG:chi_tiet", ma_don_hang=don.pk)
    form = YeuCauTraHangForm(request.POST or None, request.FILES or None, don_hang=don)
    if request.method == "POST" and form.is_valid():
        quantities = {}
        for item_id in form.cleaned_data["chi_tiet_ids"]:
            quantities[item_id] = request.POST.get(f"so_luong_{item_id}", "1")
        try:
            yeu_cau = tao_yeu_cau_tra_hang(
                don,
                ly_do_tra=form.cleaned_data["ly_do_tra"],
                mo_ta_van_de=form.cleaned_data["mo_ta_van_de"],
                ma_van_don_khach=form.cleaned_data["ma_van_don_khach"],
                phuong_thuc_hoan_tien=form.cleaned_data["phuong_thuc_hoan_tien"],
                ngan_hang_hoan_tien=form.cleaned_data["ngan_hang_hoan_tien"],
                ten_chu_tai_khoan=form.cleaned_data["ten_chu_tai_khoan"],
                so_tai_khoan=form.cleaned_data["so_tai_khoan"],
                san_pham=quantities,
                tep_minh_chung=form.cleaned_data["tep_minh_chung"],
            )
        except DuLieuDonHangKhongHopLe as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Yêu cầu trả hàng đã được gửi để nhân viên xử lý.")
            return redirect("DONHANG:theo_doi_yeu_cau_tra", ma_don_hang=don.pk)
    return render(request, "donhang/yeu_cau_tra_hang.html", {
        "form": form,
        "don_hang": don,
        "return_deadline": deadline,
        "selected_item_ids": form["chi_tiet_ids"].value() or [],
    })


def theo_doi_yeu_cau_tra(request, ma_don_hang):
    don = _don_cua_khach_hang(request, ma_don_hang)
    yeu_cau = get_object_or_404(
        YeuCauTraHang.objects.select_related("ma_don_hang").prefetch_related(
            "san_pham_tra__chi_tiet_don_hang"
        ),
        ma_don_hang=don,
    )
    return render(request, "donhang/theo_doi_yeu_cau_tra.html", {
        "don_hang": don,
        "yeu_cau_tra": yeu_cau,
        "buoc_tien_do_tra": _buoc_tien_do_tra_hang(yeu_cau),
    })


@require_POST
def huy_yeu_cau_tra_hang(request, ma_don_hang):
    don = _don_cua_khach_hang(request, ma_don_hang)
    try:
        huy_yeu_cau_tra_hang_service(don)
    except DuLieuDonHangKhongHopLe as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Yêu cầu trả hàng đã được hủy.")
    return redirect("DONHANG:chi_tiet", ma_don_hang=don.pk)


def xem_minh_chung_tra_hang(request, evidence_id):
    evidence = get_object_or_404(
        BangChungYeuCauTraHang.objects.select_related("yeu_cau__ma_don_hang"),
        pk=evidence_id,
    )
    _don_cua_khach_hang(request, evidence.yeu_cau.ma_don_hang_id)
    response = FileResponse(
        evidence.tep.open("rb"),
        content_type=evidence.loai_tep or "application/octet-stream",
        as_attachment=False,
        filename=evidence.ten_tep,
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@staff_access_required
def xu_ly_danh_sach_don_hang(request):
    return danh_sach_don_hang(request)


@staff_access_required
@require_POST
def nhan_vien_xu_ly_don_hang(request, ma_don_hang):
    don = get_object_or_404(DonHang, pk=ma_don_hang)
    try:
        xu_ly_don_hang(don, hanh_dong=request.POST.get("hanh_dong", ""))
    except DuLieuDonHangKhongHopLe as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Đã cập nhật đơn hàng.")
    return redirect("DONHANG:nhan_vien_don_hang")


@staff_access_required
@require_POST
def nhan_vien_cap_nhat_giao_hang(request, ma_don_hang):
    don = get_object_or_404(DonHang, pk=ma_don_hang)
    try:
        cap_nhat_giao_hang(
            don,
            trang_thai=request.POST.get("trang_thai", ""),
            don_vi_van_chuyen=request.POST.get("don_vi_van_chuyen"),
            ma_van_don=request.POST.get("ma_van_don"),
            ly_do_that_bai=request.POST.get("ly_do_that_bai"),
        )
    except DuLieuDonHangKhongHopLe as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Đã cập nhật thông tin giao hàng.")
    return redirect("DONHANG:chi_tiet", ma_don_hang=don.pk)


@staff_access_required
def danh_sach_yeu_cau_tra_hang(request):
    requests = YeuCauTraHang.objects.select_related("ma_don_hang").prefetch_related(
        "san_pham_tra__chi_tiet_don_hang"
    ).order_by("ngay_tao")
    return render(request, "donhang/nhan_vien_tra_hang.html", {"yeu_cau_list": requests})


@staff_access_required
def nhan_vien_xu_ly_tra_hang(request, ma_yeu_cau_tra):
    yeu_cau = get_object_or_404(
        YeuCauTraHang.objects.select_related("ma_don_hang").prefetch_related(
            "san_pham_tra__chi_tiet_don_hang"
        ),
        pk=ma_yeu_cau_tra,
    )
    form = (
        XuLyYeuCauTraHangForm(request.POST or None, yeu_cau=yeu_cau)
        if yeu_cau.trang_thai_tra in {"cho_xu_ly", "da_duyet"}
        else None
    )
    if request.method == "POST" and form and form.is_valid():
        try:
            xu_ly_yeu_cau_tra_hang(
                yeu_cau,
                hanh_dong=form.cleaned_data["hanh_dong"],
                ket_qua=form.cleaned_data["ket_qua_xl"],
                don_vi_van_chuyen_tra=form.cleaned_data["don_vi_van_chuyen_tra"],
                ma_van_don_tra=form.cleaned_data["ma_van_don_tra"],
            )
        except DuLieuDonHangKhongHopLe as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Đã lưu kết quả xử lý yêu cầu.")
            return redirect("DONHANG:nhan_vien_tra_hang")
    return render(request, "donhang/nhan_vien_xu_ly_tra_hang.html", {
        "form": form,
        "yeu_cau": yeu_cau,
        "buoc_tien_do_tra": _buoc_tien_do_tra_hang(yeu_cau),
    })
