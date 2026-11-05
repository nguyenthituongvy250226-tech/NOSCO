from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
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
# HÀM HỖ TRỢ KIỂM TRA QUYỀN
# =====================================================

def nhan_vien_required(view_func):
    """Chỉ cho phép nhân viên truy cập các chức năng quản lý."""

    @wraps(view_func)
    @login_required(login_url="KHACHHANG:dang_nhap")
    def wrapper(request, *args, **kwargs):
        if request.user.VaiTro != "NHAN_VIEN":
            messages.error(request, "Bạn không có quyền truy cập chức năng này.")
            return redirect("KHACHHANG:home")

        return view_func(request, *args, **kwargs)

    return wrapper


def lay_ho_so_khach_hang(user):
    """Lấy hồ sơ khách hàng gắn với tài khoản đang đăng nhập."""
    return get_object_or_404(
        HoSoKhachHang,
        MaNguoiDung=user
    )


# =====================================================
# 1. TRANG CHỦ
# =====================================================

def home(request):
    return render(request, "home.html")


# =====================================================
# 2. ĐĂNG KÝ
# =====================================================

def dang_ky(request):
    if request.method == "POST":
        form = DangKyForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    user = NguoiDung.objects.create_user(
                        TenDangNhap=form.cleaned_data["TenDangNhap"],
                        Email=form.cleaned_data["Email"],
                        password=form.cleaned_data["MatKhau"],
                        VaiTro="KHACH_HANG",
                    )

                    HoSoKhachHang.objects.create(
                        MaNguoiDung=user,
                        HoVaTen=form.cleaned_data["HoVaTen"],
                        SoDienThoai=form.cleaned_data["SoDienThoai"],
                    )

                messages.success(
                    request,
                    "Đăng ký tài khoản thành công. Vui lòng đăng nhập."
                )
                return redirect("KHACHHANG:dang_nhap")

            except Exception as e:
                messages.error(
                    request,
                    f"Đăng ký thất bại: {str(e)}"
                )
    else:
        form = DangKyForm()

    return render(
        request,
        "KHACHHANG/dang_ky.html",
        {"form": form}
    )


# =====================================================
# 3. ĐĂNG NHẬP
# =====================================================

def dang_nhap(request):
    if request.user.is_authenticated:
        return redirect("KHACHHANG:home")

    if request.method == "POST":
        form = DangNhapForm(request.POST)

        if form.is_valid():
            ten_dang_nhap = form.cleaned_data["TenDangNhap"]
            mat_khau = form.cleaned_data["MatKhau"]

            user = authenticate(
                request,
                username=ten_dang_nhap,
                password=mat_khau
            )

            if user is not None:
                if not user.KichHoat:
                    messages.error(
                        request,
                        "Tài khoản của bạn hiện đang bị khóa."
                    )
                else:
                    login(request, user)
                    messages.success(request, "Đăng nhập thành công.")

                    next_url = request.GET.get("next")
                    if next_url:
                        return redirect(next_url)

                    return redirect("KHACHHANG:home")
            else:
                messages.error(
                    request,
                    "Tên đăng nhập hoặc mật khẩu không chính xác."
                )
    else:
        form = DangNhapForm()

    return render(
        request,
        "KHACHHANG/dang_nhap.html",
        {"form": form}
    )


# =====================================================
# 4. ĐĂNG XUẤT
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
def dang_xuat(request):
    logout(request)
    messages.success(request, "Bạn đã đăng xuất thành công.")
    return redirect("KHACHHANG:dang_nhap")


# =====================================================
# 5. HỒ SƠ CÁ NHÂN
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
def ho_so_ca_nhan(request):
    ho_so = lay_ho_so_khach_hang(request.user)

    if request.method == "POST":
        form = HoSoKhachHangForm(
            request.POST,
            instance=ho_so,
            nguoi_dung=request.user
        )

        if form.is_valid():
            with transaction.atomic():
                form.save()

                request.user.Email = form.cleaned_data["Email"]
                request.user.save(update_fields=["Email"])

            messages.success(
                request,
                "Cập nhật hồ sơ cá nhân thành công."
            )
            return redirect("KHACHHANG:ho_so_ca_nhan")
    else:
        form = HoSoKhachHangForm(
            instance=ho_so,
            nguoi_dung=request.user
        )

    return render(
        request,
        "KHACHHANG/ho_so_ca_nhan.html",
        {
            "form": form,
            "ho_so": ho_so,
        }
    )


# =====================================================
# 6. SỔ ĐỊA CHỈ
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
def so_dia_chi(request):
    ho_so = lay_ho_so_khach_hang(request.user)

    danh_sach_dia_chi = SoDiaChi.objects.filter(
        MaKhachHang=ho_so
    ).order_by("-MacDinh", "TenNguoiNhan")

    return render(
        request,
        "KHACHHANG/so_dia_chi.html",
        {
            "ho_so": ho_so,
            "danh_sach_dia_chi": danh_sach_dia_chi,
        }
    )


# =====================================================
# 7. THÊM ĐỊA CHỈ
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
def them_dia_chi(request):
    ho_so = lay_ho_so_khach_hang(request.user)

    if request.method == "POST":
        form = SoDiaChiForm(request.POST)

        if form.is_valid():
            dia_chi = form.save(commit=False)
            dia_chi.MaKhachHang = ho_so

            with transaction.atomic():
                if dia_chi.MacDinh:
                    SoDiaChi.objects.filter(
                        MaKhachHang=ho_so
                    ).update(MacDinh=False)

                dia_chi.save()

            messages.success(request, "Thêm địa chỉ thành công.")
            return redirect("KHACHHANG:so_dia_chi")
    else:
        form = SoDiaChiForm()

    return render(
        request,
        "KHACHHANG/them_dia_chi.html",
        {"form": form}
    )


# =====================================================
# 8. SỬA ĐỊA CHỈ
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
def sua_dia_chi(request, ma_dia_chi):
    ho_so = lay_ho_so_khach_hang(request.user)

    dia_chi = get_object_or_404(
        SoDiaChi,
        MaDiaChi=ma_dia_chi,
        MaKhachHang=ho_so
    )

    if request.method == "POST":
        form = SoDiaChiForm(
            request.POST,
            instance=dia_chi
        )

        if form.is_valid():
            dia_chi_moi = form.save(commit=False)

            with transaction.atomic():
                if dia_chi_moi.MacDinh:
                    SoDiaChi.objects.filter(
                        MaKhachHang=ho_so
                    ).exclude(
                        MaDiaChi=dia_chi.MaDiaChi
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
        }
    )


# =====================================================
# 9. XÓA ĐỊA CHỈ
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
@require_POST
def xoa_dia_chi(request, ma_dia_chi):
    ho_so = lay_ho_so_khach_hang(request.user)

    dia_chi = get_object_or_404(
        SoDiaChi,
        MaDiaChi=ma_dia_chi,
        MaKhachHang=ho_so
    )

    dia_chi.delete()

    messages.success(request, "Xóa địa chỉ thành công.")
    return redirect("KHACHHANG:so_dia_chi")


# =====================================================
# 10. ĐẶT ĐỊA CHỈ MẶC ĐỊNH
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
@require_POST
def dat_dia_chi_mac_dinh(request, ma_dia_chi):
    ho_so = lay_ho_so_khach_hang(request.user)

    dia_chi = get_object_or_404(
        SoDiaChi,
        MaDiaChi=ma_dia_chi,
        MaKhachHang=ho_so
    )

    with transaction.atomic():
        SoDiaChi.objects.filter(
            MaKhachHang=ho_so
        ).update(MacDinh=False)

        dia_chi.MacDinh = True
        dia_chi.save(update_fields=["MacDinh"])

    messages.success(request, "Đã đặt địa chỉ mặc định.")
    return redirect("KHACHHANG:so_dia_chi")


# =====================================================
# 11. LỊCH SỬ TÍCH ĐIỂM
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
def lich_su_tich_diem(request):
    ho_so = lay_ho_so_khach_hang(request.user)

    danh_sach_lich_su = LichSuTichDiem.objects.filter(
        MaKhachHang=ho_so
    ).order_by("-NgayTao")

    return render(
        request,
        "KHACHHANG/lich_su_tich_diem.html",
        {
            "ho_so": ho_so,
            "danh_sach_lich_su": danh_sach_lich_su,
        }
    )


# =====================================================
# 12. DANH SÁCH THÔNG BÁO
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
def danh_sach_thong_bao(request):
    danh_sach_thong_bao = ThongBao.objects.filter(
        MaNguoiNhan=request.user
    ).order_by("-NgayTao")

    so_thong_bao_chua_doc = danh_sach_thong_bao.filter(
        DaDoc=False
    ).count()

    return render(
        request,
        "KHACHHANG/danh_sach_thong_bao.html",
        {
            "danh_sach_thong_bao": danh_sach_thong_bao,
            "so_thong_bao_chua_doc": so_thong_bao_chua_doc,
        }
    )


# =====================================================
# 13. ĐÁNH DẤU THÔNG BÁO ĐÃ ĐỌC
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
@require_POST
def danh_dau_da_doc(request, ma_thong_bao):
    thong_bao = get_object_or_404(
        ThongBao,
        MaThongBao=ma_thong_bao,
        MaNguoiNhan=request.user
    )

    if not thong_bao.DaDoc:
        thong_bao.DaDoc = True
        thong_bao.save(update_fields=["DaDoc"])

    messages.success(request, "Đã đánh dấu thông báo là đã đọc.")
    return redirect("KHACHHANG:danh_sach_thong_bao")


# =====================================================
# 14. GỬI YÊU CẦU HỖ TRỢ
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
def gui_yeu_cau_ho_tro(request):
    ho_so = lay_ho_so_khach_hang(request.user)

    if request.method == "POST":
        form = YeuCauHoTroForm(request.POST)

        if form.is_valid():
            yeu_cau = form.save(commit=False)
            yeu_cau.MaKhachHang = ho_so
            yeu_cau.save()

            messages.success(
                request,
                "Gửi yêu cầu hỗ trợ thành công."
            )
            return redirect("KHACHHANG:danh_sach_yeu_cau")
    else:
        form = YeuCauHoTroForm()

    return render(
        request,
        "KHACHHANG/gui_yeu_cau_ho_tro.html",
        {"form": form}
    )


# =====================================================
# 15. DANH SÁCH YÊU CẦU HỖ TRỢ CỦA KHÁCH HÀNG
# =====================================================

@login_required(login_url="KHACHHANG:dang_nhap")
def danh_sach_yeu_cau(request):
    ho_so = lay_ho_so_khach_hang(request.user)

    danh_sach_yeu_cau = YeuCauHoTro.objects.filter(
        MaKhachHang=ho_so
    ).order_by("-NgayTao")

    return render(
        request,
        "KHACHHANG/danh_sach_yeu_cau.html",
        {
            "danh_sach_yeu_cau": danh_sach_yeu_cau,
        }
    )


# =====================================================
# 16. DANH SÁCH KHÁCH HÀNG - NHÂN VIÊN
# =====================================================

@nhan_vien_required
def danh_sach_khach_hang(request):
    danh_sach_khach_hang = HoSoKhachHang.objects.select_related(
        "MaNguoiDung"
    ).order_by("HoVaTen")

    tu_khoa = request.GET.get("q", "").strip()

    if tu_khoa:
        danh_sach_khach_hang = danh_sach_khach_hang.filter(
            HoVaTen__icontains=tu_khoa
        ) | HoSoKhachHang.objects.select_related(
            "MaNguoiDung"
        ).filter(
            MaNguoiDung__TenDangNhap__icontains=tu_khoa
        )

    return render(
        request,
        "KHACHHANG/danh_sach_khach_hang.html",
        {
            "danh_sach_khach_hang": danh_sach_khach_hang,
            "tu_khoa": tu_khoa,
        }
    )


# =====================================================
# 17. CHI TIẾT KHÁCH HÀNG - NHÂN VIÊN
# =====================================================

@nhan_vien_required
def chi_tiet_khach_hang(request, ma_ho_so):
    ho_so = get_object_or_404(
        HoSoKhachHang.objects.select_related("MaNguoiDung"),
        MaHoSo=ma_ho_so
    )

    danh_sach_dia_chi = SoDiaChi.objects.filter(
        MaKhachHang=ho_so
    )

    danh_sach_lich_su = LichSuTichDiem.objects.filter(
        MaKhachHang=ho_so
    ).order_by("-NgayTao")

    danh_sach_yeu_cau = YeuCauHoTro.objects.filter(
        MaKhachHang=ho_so
    ).order_by("-NgayTao")

    return render(
        request,
        "KHACHHANG/chi_tiet_khach_hang.html",
        {
            "ho_so": ho_so,
            "danh_sach_dia_chi": danh_sach_dia_chi,
            "danh_sach_lich_su": danh_sach_lich_su,
            "danh_sach_yeu_cau": danh_sach_yeu_cau,
        }
    )


# =====================================================
# 18. QUẢN LÝ YÊU CẦU HỖ TRỢ - NHÂN VIÊN
# =====================================================

@nhan_vien_required
def quan_ly_yeu_cau_ho_tro(request):
    danh_sach_yeu_cau = YeuCauHoTro.objects.select_related(
        "MaKhachHang",
        "NguoiXuLy"
    ).order_by("-NgayTao")

    trang_thai = request.GET.get("trang_thai", "").strip()

    if trang_thai:
        danh_sach_yeu_cau = danh_sach_yeu_cau.filter(
            TrangThai=trang_thai
        )

    return render(
        request,
        "KHACHHANG/quan_ly_yeu_cau_ho_tro.html",
        {
            "danh_sach_yeu_cau": danh_sach_yeu_cau,
            "trang_thai_dang_chon": trang_thai,
            "trang_thai_choices": YeuCauHoTro.TRANG_THAI_CHOICES,
        }
    )


# =====================================================
# 19. XỬ LÝ YÊU CẦU HỖ TRỢ - NHÂN VIÊN
# =====================================================

@nhan_vien_required
def xu_ly_yeu_cau_ho_tro(request, ma_yeu_cau):
    yeu_cau = get_object_or_404(
        YeuCauHoTro.objects.select_related("MaKhachHang"),
        MaYeuCau=ma_yeu_cau
    )

    if request.method == "POST":
        form = PhanHoiHoTroForm(
            request.POST,
            instance=yeu_cau
        )

        if form.is_valid():
            yeu_cau = form.save(commit=False)
            yeu_cau.NguoiXuLy = request.user
            yeu_cau.save()

            messages.success(
                request,
                "Cập nhật yêu cầu hỗ trợ thành công."
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
        }
    )