
import uuid
from decimal import Decimal
from typing import TypedDict

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
import secrets

from django.http import HttpResponse
from django.urls import reverse
from .models import GioHang, ChiTietGioHang, ChiaSeGioHang
from SANPHAM.models import BienTheSanPham
SO_BIEN_THE_TOI_DA = 10


class ThongTinBienThe(TypedDict):
    ten_san_pham: str
    mau_sac: str
    kich_thuoc: str
    don_gia: Decimal
    hinh_anh: str
    so_luong_ton: int

# Mã khách hàng cố định để demo
MA_KHACH_HANG_DEMO = "KHDEMO001"


# ==========================================
# HÀM TẠO MÃ TỰ ĐỘNG
# ==========================================

def tao_ma(model):
    """
    Tạo mã ngẫu nhiên gồm 10 ký tự,
    kiểm tra để tránh trùng khóa chính.
    """
    while True:
        ma = uuid.uuid4().hex[:10].upper()

        if not model.objects.filter(pk=ma).exists():
            return ma


# ==========================================
# LẤY GIỎ HÀNG DEMO
# ==========================================

def lay_gio_hang(request):
    """
    Lấy giỏ hàng của khách đang đăng nhập; dùng giỏ demo khi chưa có mã khách.
    """

    ma_khach_hang = request.session.get("ma_khach_hang") or MA_KHACH_HANG_DEMO
    gio_hang = GioHang.objects.filter(
        ma_khach_hang=ma_khach_hang
    ).first()

    if gio_hang is None:
        gio_hang = GioHang.objects.create(
            ma_gio_hang=tao_ma(GioHang),
            ma_khach_hang=ma_khach_hang,
            loai_gio_hang=False,
        )

    return gio_hang


# ==========================================
# LẤY CHI TIẾT GIỎ HÀNG
# ==========================================

def lay_chi_tiet_gio_hang(request, id):
    gio_hang = lay_gio_hang(request)

    return get_object_or_404(
        ChiTietGioHang,
        ma_chi_tiet_gio_hang=id,
        gio_hang=gio_hang,
    )


# ==========================================
# BỔ SUNG THÔNG TIN SẢN PHẨM ĐỂ HIỂN THỊ
# ==========================================

def lay_thong_tin_bien_the(ma_bien_the: str) -> ThongTinBienThe | None:
    bien_the = (
        BienTheSanPham.objects.using("sanpham")
        .select_related("san_pham")
        .prefetch_related("hinh_anh")
        .filter(pk=ma_bien_the, san_pham__trang_thai_ban="Đang bán")
        .first()
    )
    if bien_the is None:
        return None

    danh_sach_anh = list(bien_the.hinh_anh.all())
    anh = next((item for item in danh_sach_anh if item.anh_dai_dien), None)
    if anh is None and danh_sach_anh:
        anh = danh_sach_anh[0]

    return {
        "ten_san_pham": bien_the.san_pham.ten_san_pham,
        "mau_sac": bien_the.mau_sac,
        "kich_thuoc": bien_the.kich_thuoc,
        "don_gia": bien_the.gia_ban,
        "hinh_anh": anh.duong_dan_anh.url if anh and anh.duong_dan_anh else "",
        "so_luong_ton": bien_the.so_luong_ton,
    }


def bo_sung_thong_tin_san_pham(danh_sach):
    """
    Lấy thông tin biến thể từ cơ sở dữ liệu SANPHAM
    và gắn tạm vào đối tượng chi tiết giỏ hàng.
    Không lưu các thông tin này vào database.
    """

    ma_bien_thes = {item.ma_bien_the_sp for item in danh_sach}
    bien_thes = (
        BienTheSanPham.objects.using("sanpham")
        .filter(
            ma_bien_the__in=ma_bien_thes,
            san_pham__trang_thai_ban="Đang bán",
        )
        .select_related("san_pham")
        .prefetch_related("hinh_anh")
    )
    thong_tin: dict[str, ThongTinBienThe] = {}
    for bien_the in bien_thes:
        danh_sach_anh = list(bien_the.hinh_anh.all())
        anh = next((item for item in danh_sach_anh if item.anh_dai_dien), None)
        if anh is None and danh_sach_anh:
            anh = danh_sach_anh[0]
        thong_tin[bien_the.ma_bien_the] = {
            "ten_san_pham": bien_the.san_pham.ten_san_pham,
            "mau_sac": bien_the.mau_sac,
            "kich_thuoc": bien_the.kich_thuoc,
            "don_gia": bien_the.gia_ban,
            "hinh_anh": (
                anh.duong_dan_anh.url if anh and anh.duong_dan_anh else ""
            ),
            "so_luong_ton": bien_the.so_luong_ton,
        }

    for item in danh_sach:
        san_pham = thong_tin.get(item.ma_bien_the_sp)

        if san_pham is not None:
            item.ten_san_pham = san_pham["ten_san_pham"]
            item.mau_sac = san_pham["mau_sac"]
            item.kich_thuoc = san_pham["kich_thuoc"]
            item.don_gia = san_pham["don_gia"]
            item.hinh_anh = san_pham["hinh_anh"]
            item.so_luong_ton = san_pham["so_luong_ton"]
            item.thanh_tien = item.so_luong * item.don_gia
        else:
            item.ten_san_pham = "Sản phẩm không còn tồn tại"
            item.mau_sac = ""
            item.kich_thuoc = ""
            item.don_gia = Decimal("0")
            item.hinh_anh = ""
            item.so_luong_ton = 0
            item.thanh_tien = Decimal("0")

    return danh_sach


# ==========================================
# XEM GIỎ HÀNG
# ==========================================

def xem_gio_hang(request):
    gio_hang = lay_gio_hang(request)

    danh_sach = list(
        gio_hang.chi_tiet.all().order_by("ma_chi_tiet_gio_hang")
    )

    danh_sach = bo_sung_thong_tin_san_pham(danh_sach)

    # Tổng số lượng sản phẩm trong giỏ
    tong_so_luong = sum(item.so_luong for item in danh_sach)
    # Số lượng của các sản phẩm được chọn

    so_luong_chon = sum(
        item.so_luong for item in danh_sach if item.trang_thai_chon
    )
    # Tổng tiền các sản phẩm được chọn
    tam_tinh = sum(
        (
            item.thanh_tien
            for item in danh_sach
            if item.trang_thai_chon
        ),
        Decimal("0"),
    )

    context = {
        "gio_hang": gio_hang,
        "danh_sach": danh_sach,
        "tam_tinh": tam_tinh,
        "tong_so_luong": tong_so_luong,
        "so_luong_chon": so_luong_chon,
        "tat_ca_duoc_chon": bool(danh_sach) and all(
            item.trang_thai_chon for item in danh_sach
        ),
    }

    return render(request, "GIOHANG/gio_hang.html", context)


# ==========================================
# THÊM SẢN PHẨM VÀO GIỎ HÀNG
# ==========================================

@require_POST
def them_vao_gio(request):
    ma_bien_the = (
        request.POST.get("ma_bien_the")
        or request.POST.get("ma_bien_the_sp")
        or request.POST.get("bien_the")
        or ""
    ).strip()

    try:
        so_luong = int(request.POST.get("so_luong", 1))
    except (ValueError, TypeError):
        messages.error(request, "Số lượng không hợp lệ.")
        return redirect("xem_gio_hang")

    if so_luong < 1 or so_luong > 999:
        messages.error(request, "Số lượng phải từ 1 đến 999.")
        return redirect("xem_gio_hang")

    san_pham = lay_thong_tin_bien_the(ma_bien_the)

    if san_pham is None:
        messages.error(request, "Không tìm thấy sản phẩm.")
        return redirect("xem_gio_hang")

    gio_hang = lay_gio_hang(request)

    chi_tiet = ChiTietGioHang.objects.filter(
        gio_hang=gio_hang,
        ma_bien_the_sp=ma_bien_the,
    ).first()

    so_luong_hien_tai = chi_tiet.so_luong if chi_tiet else 0

    if so_luong_hien_tai + so_luong > san_pham["so_luong_ton"]:
        messages.error(request, "Số lượng vượt quá tồn kho.")
        return redirect("xem_gio_hang")

    if chi_tiet:
        chi_tiet.so_luong += so_luong
        chi_tiet.save(update_fields=["so_luong"])
    else:
        ChiTietGioHang.objects.create(
            ma_chi_tiet_gio_hang=tao_ma(ChiTietGioHang),
            gio_hang=gio_hang,
            ma_bien_the_sp=ma_bien_the,
            so_luong=so_luong,
            trang_thai_chon=True,
        )
    if chi_tiet is None and gio_hang.chi_tiet.count() >= SO_BIEN_THE_TOI_DA:
        messages.error(
            request,
            f"Giỏ hàng chỉ chứa tối đa {SO_BIEN_THE_TOI_DA} sản phẩm khác nhau.",
        )
        return redirect("xem_gio_hang")
    messages.success(request, "Đã thêm sản phẩm vào giỏ hàng.")
    return redirect("xem_gio_hang")


# ==========================================
# CẬP NHẬT SỐ LƯỢNG
# ==========================================

@require_POST
def cap_nhat_so_luong(request, id):
    chi_tiet = lay_chi_tiet_gio_hang(request, id)

    try:
        so_luong = int(request.POST.get("so_luong", 1))
    except (ValueError, TypeError):
        messages.error(request, "Số lượng không hợp lệ.")
        return redirect("xem_gio_hang")

    san_pham = lay_thong_tin_bien_the(chi_tiet.ma_bien_the_sp)

    if so_luong < 1 or so_luong > 999:
        messages.error(request, "Số lượng phải từ 1 đến 999.")

    elif san_pham is None:
        messages.error(request, "Không tìm thấy thông tin sản phẩm.")

    elif so_luong > san_pham["so_luong_ton"]:
        messages.error(request, "Số lượng vượt quá tồn kho.")

    else:
        chi_tiet.so_luong = so_luong
        chi_tiet.save(update_fields=["so_luong"])
        messages.success(request, "Đã cập nhật số lượng.")

    return redirect("xem_gio_hang")


# ==========================================
# TĂNG SỐ LƯỢNG
# ==========================================

@require_POST
def tang_so_luong(request, id):
    chi_tiet = lay_chi_tiet_gio_hang(request, id)

    san_pham = lay_thong_tin_bien_the(chi_tiet.ma_bien_the_sp)

    if chi_tiet.so_luong >= 999:
        messages.error(request, "Số lượng không được vượt quá 999.")

    elif san_pham is None:
        messages.error(request, "Không tìm thấy thông tin sản phẩm.")

    elif chi_tiet.so_luong >= san_pham["so_luong_ton"]:
        messages.error(request, "Sản phẩm đã đạt số lượng tồn kho.")

    else:
        chi_tiet.so_luong += 1
        chi_tiet.save(update_fields=["so_luong"])
        messages.success(request, "Đã tăng số lượng sản phẩm.")

    return redirect("xem_gio_hang")


# ==========================================
# GIẢM SỐ LƯỢNG
# ==========================================

@require_POST
def giam_so_luong(request, id):
    chi_tiet = lay_chi_tiet_gio_hang(request, id)

    if chi_tiet.so_luong > 1:
        chi_tiet.so_luong -= 1
        chi_tiet.save(update_fields=["so_luong"])
        messages.success(request, "Đã giảm số lượng sản phẩm.")
    else:
        messages.error(request, "Số lượng tối thiểu là 1.")

    return redirect("xem_gio_hang")


# ==========================================
# XÓA SẢN PHẨM KHỎI GIỎ HÀNG
# ==========================================

@require_POST
def xoa_san_pham(request, id):
    chi_tiet = lay_chi_tiet_gio_hang(request, id)
    chi_tiet.delete()

    messages.success(request, "Đã xóa sản phẩm khỏi giỏ hàng.")
    return redirect("xem_gio_hang")


# ==========================================
# CHỌN / BỎ CHỌN MỘT SẢN PHẨM
# ==========================================

@require_POST
def chon_san_pham(request, id):
    chi_tiet = lay_chi_tiet_gio_hang(request, id)

    chi_tiet.trang_thai_chon = not chi_tiet.trang_thai_chon
    chi_tiet.save(update_fields=["trang_thai_chon"])

    return redirect("xem_gio_hang")


# ==========================================
# CHỌN / BỎ CHỌN TẤT CẢ SẢN PHẨM
# ==========================================

@require_POST
def chon_tat_ca(request):
    gio_hang = lay_gio_hang(request)

    gia_tri = request.POST.get("chon_tat_ca") == "true"

    gio_hang.chi_tiet.update(
        trang_thai_chon=gia_tri
    )

    return redirect("xem_gio_hang")
@require_POST
def xoa_da_chon(request):
    gio_hang = lay_gio_hang(request)
    so_dong, _ = gio_hang.chi_tiet.filter(trang_thai_chon=True).delete()

    if so_dong:
        messages.success(request, f"Đã xóa {so_dong} sản phẩm khỏi giỏ hàng.")
    else:
        messages.warning(request, "Bạn chưa chọn sản phẩm nào để xóa.")

    return redirect("xem_gio_hang")
# ==========================================
# CHIA SẺ GIỎ HÀNG
# ==========================================

@require_POST
def tao_chia_se(request):
    gio_hang = lay_gio_hang(request)
    danh_sach = list(gio_hang.chi_tiet.all())

    if not danh_sach:
        messages.warning(request, "Giỏ hàng đang trống, chưa có gì để chia sẻ.")
        return redirect("xem_gio_hang")

    chia_se = ChiaSeGioHang.objects.create(
        ma_chia_se=secrets.token_urlsafe(9),
        ma_khach_hang=gio_hang.ma_khach_hang,
        noi_dung=[
            {"ma_bien_the": i.ma_bien_the_sp, "so_luong": i.so_luong}
            for i in danh_sach
        ],
    )

    return redirect("trang_chia_se", ma=chia_se.ma_chia_se)


def trang_chia_se(request, ma):
    chia_se = get_object_or_404(
        ChiaSeGioHang,
        ma_chia_se=ma,
        ma_khach_hang=(
            request.session.get("ma_khach_hang") or MA_KHACH_HANG_DEMO
        ),
    )

    duong_dan = request.build_absolute_uri(
        reverse("nhan_gio_hang", args=[ma])
    )

    return render(request, "GIOHANG/chia_se.html", {
        "duong_dan": duong_dan,
        "so_san_pham": len(chia_se.noi_dung),
    })


def nhan_gio_hang(request, ma):
    # Tạm thời: bước 2 sẽ làm trang xem và nạp vào giỏ
    chia_se = get_object_or_404(ChiaSeGioHang, ma_chia_se=ma)
    return HttpResponse(
        f"Link hợp lệ, gồm {len(chia_se.noi_dung)} sản phẩm. Bước 2 sẽ làm tiếp."
    )