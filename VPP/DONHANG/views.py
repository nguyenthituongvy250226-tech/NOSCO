
from django.shortcuts import render
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta
import json

from .forms import SuaDonHangForm, XuLyYeuCauTraHangForm, YeuCauTraHangForm
from .models import (
    ChiTietDonHang,
    BangChungYeuCauTraHang,
    DonHang,
    GiaoHang,
    YeuCauTraHang,
)
from .services import (
    DuLieuDonHangKhongHopLe,
    cap_nhat_giao_hang,
    tao_don_hang,
    tao_yeu_cau_tra_hang,
    khach_huy_don_hang,
    cap_nhat_thong_tin_nhan,
    chot_don_cho_xac_nhan_qua_han,
    khach_xac_nhan_da_nhan,
    xu_ly_don_hang,
    xu_ly_yeu_cau_tra_hang,
)


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
    if not request.user.is_staff and (
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


def danh_sach_don_hang(request):
    chot_don_cho_xac_nhan_qua_han()
    don_hang = DonHang.objects.prefetch_related("chi_tiet").all()
    if not request.user.is_staff:
        customer_id = _ma_khach_hang(request)
        don_hang = don_hang.filter(ma_khach_hang=customer_id) if customer_id else don_hang.none()

    trang_thai = request.GET.get("trang_thai", "all")
    tu_khoa = request.GET.get("q", "").strip()
    ngay_dat = request.GET.get("ngay_dat", "").strip()

    # Lọc theo trạng thái
    if trang_thai != "all":
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

    dang_la_nhan_vien = request.user.is_staff
    cac_trang_thai = [
        {"ma": "all", "ten": "Tất cả"},
        {"ma": "cho_xac_nhan", "ten": "Chờ xác nhận"},
        {"ma": "cho_lay_hang", "ten": "Chờ lấy hàng"},
        {"ma": "cho_giao_hang", "ten": "Chờ giao hàng"},
        {"ma": "da_giao", "ten": "Đã giao"},
        {"ma": "tra_hang", "ten": "Yêu cầu trả hàng" if dang_la_nhan_vien else "Trả hàng / Hoàn tiền"},
        {"ma": "da_huy", "ten": "Đã hủy"},
    ]

    context = {
        "don_hang": don_hang,
        "ten_hien_thi": _ten_hien_thi_tai_khoan(request),
        "cac_trang_thai": cac_trang_thai,
        "trang_thai_hien_tai": trang_thai,
        "tu_khoa": tu_khoa,
        "ngay_dat": ngay_dat,
    }

    return render(request, "donhang/danh_sach.html", context)


def thong_tin_tai_khoan(request):
    """Trang tổng quan tài khoản; thông tin hồ sơ chi tiết do module tài khoản quản lý."""
    user = request.user
    ten_hien_thi = _ten_hien_thi_tai_khoan(request)
    return render(request, "donhang/thong_tin_tai_khoan.html", {
        "ten_hien_thi": ten_hien_thi,
        "ma_khach_hang": _ma_khach_hang(request),
        "email_tai_khoan": getattr(user, "email", "") if user.is_authenticated else "",
    })


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
    context["han_tra_hang"] = han_tra_hang
    context["co_the_tra_hang"] = bool(
        don_hang.trang_thai_don in {"cho_giao_hang", "cho_xac_nhan_nhan", "da_giao"}
        and context["giao_hang_thanh_cong"]
        and not don_hang.khach_da_xac_nhan_nhan
        and han_tra_hang
        and timezone.now() <= han_tra_hang
    )
    context["dang_cho_khach_chon"] = bool(
        context["co_the_tra_hang"]
        and not don_hang.khach_da_xac_nhan_nhan
        and not yeu_cau_tra
    )
    status_steps = ["Chờ xác nhận", "Chờ lấy hàng", "Đang giao", "Đã giao"]
    status_index = {
        "cho_xac_nhan": 0,
        "cho_lay_hang": 1,
        "cho_giao_hang": 2,
        "cho_xac_nhan_nhan": 3,
        "da_giao": 3,
        "tra_hang": 3,
    }.get(don_hang.trang_thai_don, -1)
    context["cac_buoc"] = [
        {"ten": label, "hoan_tat": index < status_index, "hien_tai": index == status_index}
        for index, label in enumerate(status_steps)
    ]
    context["tien_do"] = max(status_index, 0) * 28 if status_index >= 0 else 0

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


@staff_member_required
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


@staff_member_required
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


@staff_member_required
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
    try:
        giao = don.giao_hang
    except GiaoHang.DoesNotExist:
        giao = None
    deadline = giao.ngay_giao_thanh_cong + timedelta(hours=24) if giao and giao.ngay_giao_thanh_cong else None
    if (don.trang_thai_don not in {"cho_giao_hang", "cho_xac_nhan_nhan", "da_giao"}
            or not giao or giao.trang_thai != "da_giao"
            or don.khach_da_xac_nhan_nhan or not deadline or timezone.now() > deadline):
        messages.error(request, "Đơn hàng không còn đủ điều kiện yêu cầu trả hàng.")
        return redirect("DONHANG:chi_tiet", ma_don_hang=don.pk)
    return render(request, "donhang/huong_dan_tra_hang.html", {
        "don_hang": don, "return_deadline": deadline,
    })


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


@staff_member_required
def xu_ly_danh_sach_don_hang(request):
    return danh_sach_don_hang(request)


@staff_member_required
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


@staff_member_required
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


@staff_member_required
def danh_sach_yeu_cau_tra_hang(request):
    requests = YeuCauTraHang.objects.select_related("ma_don_hang").prefetch_related(
        "san_pham_tra__chi_tiet_don_hang"
    ).order_by("ngay_tao")
    return render(request, "donhang/nhan_vien_tra_hang.html", {"yeu_cau_list": requests})


@staff_member_required
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
