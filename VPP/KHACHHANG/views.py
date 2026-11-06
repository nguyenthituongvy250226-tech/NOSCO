
from functools import wraps

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import (
    NguoiDung,
    HoSoKhachHang,
    SoDiaChi,
    LichSuTichDiem,
    ThongBao,
    YeuCauHoTro,
)

from .forms import (
    DangKyForm,
    DangNhapForm,
    HoSoKhachHangForm,
    SoDiaChiForm,
    YeuCauHoTroForm,
    PhanHoiHoTroForm,
)


# =====================================================
# 1. XÁC THỰC TÀI KHOẢN PA BẰNG SESSION RIÊNG
# =====================================================

SESSION_NGUOI_DUNG = "khachhang_ma_nguoi_dung"


def nguoi_dung_required(view_func):
    """Kiểm tra tài khoản PA đã đăng nhập và còn hoạt động."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        ma_nguoi_dung = request.session.get(SESSION_NGUOI_DUNG)

        if not ma_nguoi_dung:
            return redirect("KHACHHANG:dang_nhap")

        try:
            nguoi_dung = NguoiDung.objects.get(
                MaNguoiDung=ma_nguoi_dung,
                KichHoat=True,
            )
        except NguoiDung.DoesNotExist:
            request.session.pop(SESSION_NGUOI_DUNG, None)
            request.session.pop("ma_khach_hang", None)
            request.session.pop("ten_dang_nhap", None)
            request.session.pop("vai_tro", None)

            messages.error(
                request,
                "Tài khoản không tồn tại hoặc đã bị khóa.",
            )
            return redirect("KHACHHANG:dang_nhap")

        request.nguoi_dung = nguoi_dung
        return view_func(request, *args, **kwargs)

    return wrapper


def khach_hang_required(view_func):
    """Chỉ cho phép khách hàng truy cập."""

    @wraps(view_func)
    @nguoi_dung_required
    def wrapper(request, *args, **kwargs):
        if request.nguoi_dung.VaiTro != "KHACH_HANG":
            messages.error(
                request,
                "Chức năng này chỉ dành cho khách hàng.",
            )
            return redirect("KHACHHANG:home")

        return view_func(request, *args, **kwargs)

    return wrapper


def nhan_vien_required(view_func):
    """Chỉ cho phép nhân viên truy cập."""

    @wraps(view_func)
    @nguoi_dung_required
    def wrapper(request, *args, **kwargs):
        if request.nguoi_dung.VaiTro != "NHAN_VIEN":
            messages.error(
                request,
                "Bạn không có quyền truy cập chức năng này.",
            )
            return redirect("KHACHHANG:home")

        return view_func(request, *args, **kwargs)

    return wrapper


def lay_ho_so_khach_hang(nguoi_dung):
    """Lấy hồ sơ khách hàng theo tài khoản PA."""

    return get_object_or_404(
        HoSoKhachHang,
        MaNguoiDung=nguoi_dung,
    )


# =====================================================
# 2. TRANG CHỦ
# =====================================================

def home(request):
    return render(request, "home.html")


# =====================================================
# 3. ĐĂNG KÝ
# =====================================================

def dang_ky(request):
    if request.method == "POST":
        form = DangKyForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    nguoi_dung = NguoiDung.objects.create_user(
                        TenDangNhap=form.cleaned_data["TenDangNhap"],
                        Email=form.cleaned_data["Email"],
                        password=form.cleaned_data["MatKhau"],
                        VaiTro="KHACH_HANG",
                    )

                    HoSoKhachHang.objects.create(
                        MaNguoiDung=nguoi_dung,
                        HoVaTen=form.cleaned_data["HoVaTen"],
                        SoDienThoai=form.cleaned_data["SoDienThoai"],
                    )

                messages.success(
                    request,
                    "Đăng ký tài khoản thành công. Vui lòng đăng nhập.",
                )
                return redirect("KHACHHANG:dang_nhap")

            except Exception as e:
                messages.error(request, f"Đăng ký thất bại: {str(e)}")
    else:
        form = DangKyForm()

    return render(
        request,
        "KHACHHANG/dang_ky.html",
        {"form": form},
    )


# =====================================================
# 4. ĐĂNG NHẬP
# =====================================================

def dang_nhap(request):
    if request.session.get(SESSION_NGUOI_DUNG):
        try:
            NguoiDung.objects.get(
                MaNguoiDung=request.session[SESSION_NGUOI_DUNG],
                KichHoat=True,
            )
            return redirect("KHACHHANG:home")
        except NguoiDung.DoesNotExist:
            request.session.pop(SESSION_NGUOI_DUNG, None)

    if request.method == "POST":
        form = DangNhapForm(request.POST)

        if form.is_valid():
            ten_dang_nhap = form.cleaned_data["TenDangNhap"]
            mat_khau = form.cleaned_data["MatKhau"]

            try:
                nguoi_dung = NguoiDung.objects.get(
                    TenDangNhap=ten_dang_nhap,
                )
            except NguoiDung.DoesNotExist:
                nguoi_dung = None

            if nguoi_dung is None or not nguoi_dung.check_password(mat_khau):
                messages.error(
                    request,
                    "Tên đăng nhập hoặc mật khẩu không chính xác.",
                )

            elif not nguoi_dung.KichHoat:
                messages.error(
                    request,
                    "Tài khoản của bạn hiện đang bị khóa.",
                )

            else:
                ma_ho_so = ""

                if nguoi_dung.VaiTro == "KHACH_HANG":
                    try:
                        ho_so = HoSoKhachHang.objects.get(
                            MaNguoiDung=nguoi_dung,
                        )
                        ma_ho_so = ho_so.MaHoSo
                    except HoSoKhachHang.DoesNotExist:
                        messages.error(
                            request,
                            "Tài khoản chưa có hồ sơ khách hàng.",
                        )
                        return render(
                            request,
                            "KHACHHANG/dang_nhap.html",
                            {"form": form},
                        )

                request.session.cycle_key()

                request.session[SESSION_NGUOI_DUNG] = (
                    nguoi_dung.MaNguoiDung
                )

                # Mã hồ sơ khách hàng dùng chung với GIOHANG và DONHANG.
                request.session["ma_khach_hang"] = ma_ho_so

                request.session["ten_dang_nhap"] = (
                    nguoi_dung.TenDangNhap
                )
                request.session["vai_tro"] = nguoi_dung.VaiTro

                messages.success(request, "Đăng nhập thành công.")

                next_url = request.GET.get("next")

                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)

                return redirect("KHACHHANG:home")

    else:
        form = DangNhapForm()

    return render(
        request,
        "KHACHHANG/dang_nhap.html",
        {"form": form},
    )


# =====================================================
# 5. ĐĂNG XUẤT
# =====================================================

@nguoi_dung_required
def dang_xuat(request):
    request.session.pop(SESSION_NGUOI_DUNG, None)
    request.session.pop("ma_khach_hang", None)
    request.session.pop("ten_dang_nhap", None)
    request.session.pop("vai_tro", None)

    messages.success(request, "Bạn đã đăng xuất thành công.")

    return redirect("KHACHHANG:dang_nhap")


# =====================================================
# 6. HỒ SƠ CÁ NHÂN
# =====================================================

@khach_hang_required
def ho_so_ca_nhan(request):
    nguoi_dung = request.nguoi_dung
    ho_so = lay_ho_so_khach_hang(nguoi_dung)

    if request.method == "POST":
        form = HoSoKhachHangForm(
            request.POST,
            instance=ho_so,
            nguoi_dung=nguoi_dung,
        )

        if form.is_valid():
            with transaction.atomic():
                form.save()

                nguoi_dung.Email = form.cleaned_data["Email"]
                nguoi_dung.save(update_fields=["Email"])

            messages.success(
                request,
                "Cập nhật hồ sơ cá nhân thành công.",
            )
            return redirect("KHACHHANG:ho_so_ca_nhan")

    else:
        form = HoSoKhachHangForm(
            instance=ho_so,
            nguoi_dung=nguoi_dung,
        )

    return render(
        request,
        "KHACHHANG/ho_so_ca_nhan.html",
        {
            "form": form,
            "ho_so": ho_so,
        },
    )


# =====================================================
# 7. SỔ ĐỊA CHỈ
# =====================================================

@khach_hang_required
def so_dia_chi(request):
    ho_so = lay_ho_so_khach_hang(request.nguoi_dung)

    danh_sach_dia_chi = SoDiaChi.objects.filter(
        MaKhachHang=ho_so,
    ).order_by("-MacDinh", "TenNguoiNhan")

    return render(
        request,
        "KHACHHANG/so_dia_chi.html",
        {
            "ho_so": ho_so,
            "danh_sach_dia_chi": danh_sach_dia_chi,
        },
    )


# =====================================================
# 8. THÊM ĐỊA CHỈ
# =====================================================

@khach_hang_required
def them_dia_chi(request):
    ho_so = lay_ho_so_khach_hang(request.nguoi_dung)

    if request.method == "POST":
        form = SoDiaChiForm(request.POST)

        if form.is_valid():
            dia_chi = form.save(commit=False)
            dia_chi.MaKhachHang = ho_so

            with transaction.atomic():
                if dia_chi.MacDinh:
                    SoDiaChi.objects.filter(
                        MaKhachHang=ho_so,
                    ).update(MacDinh=False)

                dia_chi.save()

            messages.success(request, "Thêm địa chỉ thành công.")
            return redirect("KHACHHANG:so_dia_chi")

    else:
        form = SoDiaChiForm()

    return render(
        request,
        "KHACHHANG/them_dia_chi.html",
        {"form": form},
    )


# =====================================================
# 9. SỬA ĐỊA CHỈ
# =====================================================

@khach_hang_required
def sua_dia_chi(request, ma_dia_chi):
    ho_so = lay_ho_so_khach_hang(request.nguoi_dung)

    dia_chi = get_object_or_404(
        SoDiaChi,
        MaDiaChi=ma_dia_chi,
        MaKhachHang=ho_so,
    )

    if request.method == "POST":
        form = SoDiaChiForm(
            request.POST,
            instance=dia_chi,
        )

        if form.is_valid():
            dia_chi_moi = form.save(commit=False)

            with transaction.atomic():
                if dia_chi_moi.MacDinh:
                    SoDiaChi.objects.filter(
                        MaKhachHang=ho_so,
                    ).exclude(
                        MaDiaChi=dia_chi.MaDiaChi,
                    ).update(MacDinh=False)

                dia_chi_moi.save()

            messages.success(request, "Cập nhật địa chỉ thành công.")
            return redirect("KHACHHANG:so_dia_chi")

    else:
        form = SoDiaChiForm(instance=dia_chi)

    return render(
        request,
        "KHACHHANG/sua_dia_chi.html",
        {
            "form": form,
            "dia_chi": dia_chi,
        },
    )


# =====================================================
# 10. XÓA ĐỊA CHỈ
# =====================================================

@khach_hang_required
@require_POST
def xoa_dia_chi(request, ma_dia_chi):
    ho_so = lay_ho_so_khach_hang(request.nguoi_dung)

    dia_chi = get_object_or_404(
        SoDiaChi,
        MaDiaChi=ma_dia_chi,
        MaKhachHang=ho_so,
    )

    dia_chi.delete()

    messages.success(request, "Xóa địa chỉ thành công.")
    return redirect("KHACHHANG:so_dia_chi")


# =====================================================
# 11. ĐẶT ĐỊA CHỈ MẶC ĐỊNH
# =====================================================

@khach_hang_required
@require_POST
def dat_dia_chi_mac_dinh(request, ma_dia_chi):
    ho_so = lay_ho_so_khach_hang(request.nguoi_dung)

    dia_chi = get_object_or_404(
        SoDiaChi,
        MaDiaChi=ma_dia_chi,
        MaKhachHang=ho_so,
    )

    with transaction.atomic():
        SoDiaChi.objects.filter(
            MaKhachHang=ho_so,
        ).update(MacDinh=False)

        dia_chi.MacDinh = True
        dia_chi.save(update_fields=["MacDinh"])

    messages.success(request, "Đã đặt địa chỉ mặc định.")
    return redirect("KHACHHANG:so_dia_chi")


# =====================================================
# 12. LỊCH SỬ TÍCH ĐIỂM
# =====================================================

@khach_hang_required
def lich_su_tich_diem(request):
    ho_so = lay_ho_so_khach_hang(request.nguoi_dung)

    danh_sach_lich_su = LichSuTichDiem.objects.filter(
        MaKhachHang=ho_so,
    ).order_by("-NgayTao")

    return render(
        request,
        "KHACHHANG/lich_su_tich_diem.html",
        {
            "ho_so": ho_so,
            "danh_sach_lich_su": danh_sach_lich_su,
        },
    )


# =====================================================
# 13. DANH SÁCH THÔNG BÁO
# =====================================================

@nguoi_dung_required
def danh_sach_thong_bao(request):
    danh_sach_thong_bao = ThongBao.objects.filter(
        MaNguoiNhan=request.nguoi_dung,
    ).order_by("-NgayTao")

    so_thong_bao_chua_doc = danh_sach_thong_bao.filter(
        DaDoc=False,
    ).count()

    return render(
        request,
        "KHACHHANG/danh_sach_thong_bao.html",
        {
            "danh_sach_thong_bao": danh_sach_thong_bao,
            "so_thong_bao_chua_doc": so_thong_bao_chua_doc,
        },
    )


# =====================================================
# 14. ĐÁNH DẤU THÔNG BÁO ĐÃ ĐỌC
# =====================================================

@nguoi_dung_required
@require_POST
def danh_dau_da_doc(request, ma_thong_bao):
    thong_bao = get_object_or_404(
        ThongBao,
        MaThongBao=ma_thong_bao,
        MaNguoiNhan=request.nguoi_dung,
    )

    if not thong_bao.DaDoc:
        thong_bao.DaDoc = True
        thong_bao.save(update_fields=["DaDoc"])

    messages.success(request, "Đã đánh dấu thông báo là đã đọc.")
    return redirect("KHACHHANG:danh_sach_thong_bao")


# =====================================================
# 15. GỬI YÊU CẦU HỖ TRỢ
# =====================================================

@khach_hang_required
def gui_yeu_cau_ho_tro(request):
    ho_so = lay_ho_so_khach_hang(request.nguoi_dung)

    if request.method == "POST":
        form = YeuCauHoTroForm(request.POST)

        if form.is_valid():
            yeu_cau = form.save(commit=False)
            yeu_cau.MaKhachHang = ho_so
            yeu_cau.save()

            messages.success(
                request,
                "Gửi yêu cầu hỗ trợ thành công.",
            )
            return redirect("KHACHHANG:danh_sach_yeu_cau")

    else:
        form = YeuCauHoTroForm()

    return render(
        request,
        "KHACHHANG/gui_yeu_cau_ho_tro.html",
        {"form": form},
    )


# =====================================================
# 16. DANH SÁCH YÊU CẦU HỖ TRỢ CỦA KHÁCH HÀNG
# =====================================================

@khach_hang_required
def danh_sach_yeu_cau(request):
    ho_so = lay_ho_so_khach_hang(request.nguoi_dung)

    danh_sach_yeu_cau = YeuCauHoTro.objects.filter(
        MaKhachHang=ho_so,
    ).order_by("-NgayTao")

    return render(
        request,
        "KHACHHANG/danh_sach_yeu_cau.html",
        {
            "danh_sach_yeu_cau": danh_sach_yeu_cau,
        },
    )


# =====================================================
# 17. DANH SÁCH KHÁCH HÀNG - NHÂN VIÊN
# =====================================================

@nhan_vien_required
def danh_sach_khach_hang(request):
    danh_sach_khach_hang = HoSoKhachHang.objects.select_related(
        "MaNguoiDung",
    ).order_by("HoVaTen")

    tu_khoa = request.GET.get("q", "").strip()

    if tu_khoa:
        danh_sach_khach_hang = danh_sach_khach_hang.filter(
            Q(HoVaTen__icontains=tu_khoa)
            | Q(MaNguoiDung__TenDangNhap__icontains=tu_khoa)
        )

    return render(
        request,
        "KHACHHANG/danh_sach_khach_hang.html",
        {
            "danh_sach_khach_hang": danh_sach_khach_hang,
            "tu_khoa": tu_khoa,
        },
    )


# =====================================================
# 18. CHI TIẾT KHÁCH HÀNG - NHÂN VIÊN
# =====================================================

@nhan_vien_required
def chi_tiet_khach_hang(request, ma_ho_so):
    ho_so = get_object_or_404(
        HoSoKhachHang.objects.select_related("MaNguoiDung"),
        MaHoSo=ma_ho_so,
    )

    danh_sach_dia_chi = SoDiaChi.objects.filter(
        MaKhachHang=ho_so,
    )

    danh_sach_lich_su = LichSuTichDiem.objects.filter(
        MaKhachHang=ho_so,
    ).order_by("-NgayTao")

    danh_sach_yeu_cau = YeuCauHoTro.objects.filter(
        MaKhachHang=ho_so,
    ).order_by("-NgayTao")

    return render(
        request,
        "KHACHHANG/chi_tiet_khach_hang.html",
        {
            "ho_so": ho_so,
            "danh_sach_dia_chi": danh_sach_dia_chi,
            "danh_sach_lich_su": danh_sach_lich_su,
            "danh_sach_yeu_cau": danh_sach_yeu_cau,
        },
    )


# =====================================================
# 19. QUẢN LÝ YÊU CẦU HỖ TRỢ - NHÂN VIÊN
# =====================================================

@nhan_vien_required
def quan_ly_yeu_cau_ho_tro(request):
    danh_sach_yeu_cau = YeuCauHoTro.objects.select_related(
        "MaKhachHang",
        "NguoiXuLy",
    ).order_by("-NgayTao")

    trang_thai = request.GET.get("trang_thai", "").strip()

    if trang_thai:
        danh_sach_yeu_cau = danh_sach_yeu_cau.filter(
            TrangThai=trang_thai,
        )

    return render(
        request,
        "KHACHHANG/quan_ly_yeu_cau_ho_tro.html",
        {
            "danh_sach_yeu_cau": danh_sach_yeu_cau,
            "trang_thai_dang_chon": trang_thai,
            "trang_thai_choices": YeuCauHoTro.TRANG_THAI_CHOICES,
        },
    )


# =====================================================
# 20. XỬ LÝ YÊU CẦU HỖ TRỢ - NHÂN VIÊN
# =====================================================

@nhan_vien_required
def xu_ly_yeu_cau_ho_tro(request, ma_yeu_cau):
    yeu_cau = get_object_or_404(
        YeuCauHoTro.objects.select_related("MaKhachHang"),
        MaYeuCau=ma_yeu_cau,
    )

    if request.method == "POST":
        form = PhanHoiHoTroForm(
            request.POST,
            instance=yeu_cau,
        )

        if form.is_valid():
            yeu_cau = form.save(commit=False)
            yeu_cau.NguoiXuLy = request.nguoi_dung
            yeu_cau.save()

            messages.success(
                request,
                "Cập nhật yêu cầu hỗ trợ thành công.",
            )
            return redirect("KHACHHANG:quan_ly_yeu_cau_ho_tro")

    else:
        form = PhanHoiHoTroForm(instance=yeu_cau)

    return render(
        request,
        "KHACHHANG/xu_ly_yeu_cau_ho_tro.html",
        {
            "form": form,
            "yeu_cau": yeu_cau,
        },
    )
