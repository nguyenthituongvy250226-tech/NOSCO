
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Min, Q, Avg, Count
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .models import (
    SanPham,
    DanhMucSanPham,
    ThuongHieu,
    BaiViet,
    SanPhamQuaTang,
    DanhGiaSanPham,
    SanPhamYeuThich,
    BienTheSanPham,
)

from .forms import DanhGiaSanPhamForm

from KHUYENMAI.models import ChiTietKhuyenMai

from KHACHHANG.views import khach_hang_required
from KHACHHANG.models import HoSoKhachHang

from DONHANG.models import ChiTietDonHang


# =========================================================
# 1. HÀM ĐỊNH DẠNG GIÁ
# =========================================================

def dinh_dang_gia(gia):
    if gia is None:
        return None

    return f"{gia:,.0f}".replace(",", ".")


# =========================================================
# 2. LẤY DANH SÁCH KHUYẾN MÃI ĐANG CÓ HIỆU LỰC
# =========================================================

def lay_khuyen_mai_theo_san_pham(danh_sach_ma_sp):
    """
    Lấy khuyến mãi đang áp dụng cho các sản phẩm.

    Điều kiện:
    - Chi tiết khuyến mãi đang bật.
    - Chương trình đã bắt đầu.
    - Chương trình chưa kết thúc.

    Nếu một sản phẩm có nhiều khuyến mãi,
    ưu tiên giá khuyến mãi thấp nhất.
    """

    if not danh_sach_ma_sp:
        return {}

    thoi_diem_hien_tai = timezone.now()

    cac_chi_tiet_km = ChiTietKhuyenMai.objects.filter(
        MaSanPham__in=[str(ma) for ma in danh_sach_ma_sp],
        TrangThai=True,
        MaKhuyenMai__NgayBatDau__lte=thoi_diem_hien_tai,
        MaKhuyenMai__NgayKetThuc__gte=thoi_diem_hien_tai,
    ).values(
        "MaSanPham",
        "GiaKhuyenMai",
        "PhanTramGiam",
    )

    khuyen_mai_theo_sp = {}

    for km in cac_chi_tiet_km:
        ma_sp = str(km["MaSanPham"])

        km_cu = khuyen_mai_theo_sp.get(ma_sp)

        if (
            km_cu is None
            or km["GiaKhuyenMai"] < km_cu["gia_khuyen_mai"]
        ):
            khuyen_mai_theo_sp[ma_sp] = {
                "gia_khuyen_mai": km["GiaKhuyenMai"],
                "phan_tram_giam": km["PhanTramGiam"],
            }

    return khuyen_mai_theo_sp


# =========================================================
# 3. TẠO THÔNG TIN GIÁ VÀ KHUYẾN MÃI CHO SẢN PHẨM
# =========================================================

def tao_thong_tin_gia(san_pham, gia_goc, khuyen_mai_theo_sp):
    """
    Chuẩn bị dữ liệu giá để truyền sang template.

    Nếu có khuyến mãi hợp lệ:
    - Hiển thị giá gốc.
    - Hiển thị giá khuyến mãi.
    - Hiển thị phần trăm giảm.

    Nếu không có:
    - Chỉ hiển thị giá bán bình thường.
    """

    thong_tin_km = khuyen_mai_theo_sp.get(
        str(san_pham.ma_san_pham)
    )

    gia_khuyen_mai = None
    phan_tram_giam = None
    co_khuyen_mai = False

    if thong_tin_km and gia_goc is not None:
        gia_de_xuat = thong_tin_km["gia_khuyen_mai"]

        # Chỉ áp dụng nếu giá khuyến mãi thấp hơn giá gốc
        if gia_de_xuat < gia_goc:
            gia_khuyen_mai = gia_de_xuat
            phan_tram_giam = thong_tin_km["phan_tram_giam"]
            co_khuyen_mai = True

    gia_hien_thi = (
        gia_khuyen_mai
        if co_khuyen_mai
        else gia_goc
    )

    return {
        "san_pham": san_pham,
        "gia_thap_nhat": gia_goc,

        "co_khuyen_mai": co_khuyen_mai,
        "phan_tram_giam": phan_tram_giam,
        "gia_khuyen_mai": gia_khuyen_mai,

        "gia_goc_hien_thi": (
            dinh_dang_gia(gia_goc)
            if co_khuyen_mai else None
        ),

        "gia_khuyen_mai_hien_thi": (
            dinh_dang_gia(gia_khuyen_mai)
            if co_khuyen_mai else None
        ),

        "gia_hien_thi": dinh_dang_gia(gia_hien_thi),
    }


# =========================================================
# 4. DANH SÁCH SẢN PHẨM
# =========================================================

def danh_sach_san_pham(request):

    # 1. Nhận điều kiện tìm kiếm và lọc từ URL
    tu_khoa = request.GET.get("q", "").strip()
    ma_danh_muc = request.GET.get("danh_muc", "").strip()
    nhom = request.GET.get("nhom", "").strip()
    ma_thuong_hieu = request.GET.get("thuong_hieu", "").strip()
    gia_tu_text = request.GET.get("gia_tu", "").strip()
    gia_den_text = request.GET.get("gia_den", "").strip()
    sap_xep = request.GET.get("sap_xep", "ten_a_z")

    # 2. Lấy danh sách sản phẩm yêu thích
    ma_khach_hang = request.session.get("ma_khach_hang")

    if ma_khach_hang:
        danh_sach_yeu_thich = list(
            SanPhamYeuThich.objects.filter(
                ma_khach_hang=ma_khach_hang
            ).values_list(
                "san_pham__ma_san_pham",
                flat=True
            )
        )
    else:
        danh_sach_yeu_thich = []

    # 3. Lấy sản phẩm đang bán và tính giá thấp nhất
    san_pham_queryset = (
        SanPham.objects
        .filter(trang_thai_ban="Đang bán")
        .select_related("danh_muc", "thuong_hieu")
        .prefetch_related("bien_the__hinh_anh")
        .annotate(gia_thap_nhat=Min("bien_the__gia_ban"))
    )

    # 4. Lọc theo thương hiệu
    thuong_hieu_id = request.GET.get("thuong_hieu")

    if thuong_hieu_id and thuong_hieu_id.isdigit():
        san_pham_queryset = san_pham_queryset.filter(
            thuong_hieu_id=int(thuong_hieu_id)
        )

    # 5. Tìm kiếm theo tên, thương hiệu và danh mục
    if tu_khoa:
        san_pham_queryset = san_pham_queryset.filter(
            Q(ten_san_pham__icontains=tu_khoa)
            | Q(thuong_hieu__ten_thuong_hieu__icontains=tu_khoa)
            | Q(danh_muc__ten_danh_muc__icontains=tu_khoa)
        ).distinct()

    # 6. Lọc theo nhóm và danh mục
    cac_nhom_danh_muc = {
        "hoc_tap": ["DM001", "DM002"],
        "lam_viec": ["DM003", "DM004"],
        "sang_tao": ["DM003", "DM004"],
    }

    if nhom in cac_nhom_danh_muc:
        san_pham_queryset = san_pham_queryset.filter(
            danh_muc_id__in=cac_nhom_danh_muc[nhom]
        )

    elif ma_danh_muc:
        san_pham_queryset = san_pham_queryset.filter(
            danh_muc_id=ma_danh_muc
        )

    if ma_thuong_hieu:
        san_pham_queryset = san_pham_queryset.filter(
            thuong_hieu_id=ma_thuong_hieu
        )

    # 7. Kiểm tra giá nhập vào
    def doc_gia(gia_text):
        if not gia_text:
            return None

        try:
            gia = Decimal(gia_text)

            if gia < 0:
                return None

            return gia

        except (InvalidOperation, ValueError):
            return None

    gia_tu = doc_gia(gia_tu_text)
    gia_den = doc_gia(gia_den_text)

    # 8. Lọc theo giá thấp nhất
    if gia_tu is not None:
        san_pham_queryset = san_pham_queryset.filter(
            gia_thap_nhat__gte=gia_tu
        )

    if gia_den is not None:
        san_pham_queryset = san_pham_queryset.filter(
            gia_thap_nhat__lte=gia_den
        )

    # 9. Sắp xếp sản phẩm
    if sap_xep == "gia_tang":
        san_pham_queryset = san_pham_queryset.order_by(
            "gia_thap_nhat",
            "ten_san_pham"
        )

    elif sap_xep == "gia_giam":
        san_pham_queryset = san_pham_queryset.order_by(
            "-gia_thap_nhat",
            "ten_san_pham"
        )

    elif sap_xep == "moi_nhat":
        san_pham_queryset = san_pham_queryset.order_by(
            "-ngay_tao",
            "ten_san_pham"
        )

    else:
        sap_xep = "ten_a_z"

        san_pham_queryset = san_pham_queryset.order_by(
            "ten_san_pham"
        )

    # 10. Lấy danh sách sản phẩm sau khi lọc
    cac_san_pham = list(san_pham_queryset)

    # Lấy thông tin khuyến mãi của các sản phẩm
    khuyen_mai_theo_sp = lay_khuyen_mai_theo_san_pham(
        [sp.ma_san_pham for sp in cac_san_pham]
    )

    # 11. Chuẩn bị ảnh và giá cho từng sản phẩm
    danh_sach_san_pham = []

    for san_pham in cac_san_pham:

        cac_bien_the = list(san_pham.bien_the.all())

        cac_anh = [
            anh
            for bien_the in cac_bien_the
            for anh in bien_the.hinh_anh.all()
            if anh.duong_dan_anh
        ]

        anh_dai_dien = next(
            (anh for anh in cac_anh if anh.anh_dai_dien),
            cac_anh[0] if cac_anh else None,
        )

        thong_tin_gia = tao_thong_tin_gia(
            san_pham,
            san_pham.gia_thap_nhat,
            khuyen_mai_theo_sp
        )

        thong_tin_gia["anh_dai_dien"] = anh_dai_dien

        danh_sach_san_pham.append(thong_tin_gia)

    # 12. Khởi tạo danh sách sản phẩm gợi ý
    san_pham_goi_y = []

    if not danh_sach_san_pham:

        goi_y_queryset = (
            SanPham.objects
            .filter(trang_thai_ban="Đang bán")
            .select_related("danh_muc", "thuong_hieu")
            .prefetch_related("bien_the__hinh_anh")
            .annotate(gia_thap_nhat=Min("bien_the__gia_ban"))
            .order_by("-ngay_tao", "ten_san_pham")[:4]
        )

        cac_san_pham_goi_y = list(goi_y_queryset)

        khuyen_mai_goi_y = lay_khuyen_mai_theo_san_pham(
            [sp.ma_san_pham for sp in cac_san_pham_goi_y]
        )

        for san_pham in cac_san_pham_goi_y:

            cac_anh = [
                anh
                for bien_the in san_pham.bien_the.all()
                for anh in bien_the.hinh_anh.all()
                if anh.duong_dan_anh
            ]

            anh_dai_dien = next(
                (anh for anh in cac_anh if anh.anh_dai_dien),
                cac_anh[0] if cac_anh else None,
            )

            thong_tin_gia = tao_thong_tin_gia(
                san_pham,
                san_pham.gia_thap_nhat,
                khuyen_mai_goi_y
            )

            thong_tin_gia["anh_dai_dien"] = anh_dai_dien
            # Kiểm tra sản phẩm còn ít nhất một biến thể có hàng hay không
            thong_tin_gia["con_hang"] = any(
                bien_the.so_luong_ton > 0
                for bien_the in cac_bien_the
            )

            san_pham_goi_y.append(thong_tin_gia)

    # 13. Trả dữ liệu về giao diện
    return render(
        request,
        "SANPHAM/giao_dien_thu.html",
        {
            "danh_sach_san_pham": danh_sach_san_pham,
            "danh_muc_list": DanhMucSanPham.objects.all(),
            "thuong_hieu_list": ThuongHieu.objects.all(),
            "tu_khoa": tu_khoa,
            "danh_muc_dang_chon": ma_danh_muc,
            "thuong_hieu_dang_chon": ma_thuong_hieu,
            "gia_tu": gia_tu_text,
            "gia_den": gia_den_text,
            "sap_xep": sap_xep,
            "san_pham_goi_y": san_pham_goi_y,
            "danh_sach_yeu_thich": danh_sach_yeu_thich,
        },
    )


# =========================================================
# 5. TRANG CHỦ
# =========================================================

def home(request):

    # 1. Lấy sản phẩm đang bán
    san_pham_queryset = (
        SanPham.objects
        .filter(trang_thai_ban="Đang bán")
        .select_related("danh_muc", "thuong_hieu")
        .prefetch_related("bien_the__hinh_anh")
        .annotate(gia_thap_nhat=Min("bien_the__gia_ban"))
        .order_by("-ngay_tao", "ten_san_pham")
    )

    # 2. Chuẩn bị dữ liệu sản phẩm
    danh_sach_the = []

    cac_san_pham = list(san_pham_queryset)

    # Lấy thông tin khuyến mãi của các sản phẩm
    khuyen_mai_theo_sp = lay_khuyen_mai_theo_san_pham(
        [sp.ma_san_pham for sp in cac_san_pham]
    )

    for san_pham in cac_san_pham:

        cac_bien_the = list(san_pham.bien_the.all())

        cac_anh = [
            anh
            for bien_the in cac_bien_the
            for anh in bien_the.hinh_anh.all()
            if anh.duong_dan_anh
        ]

        anh_dai_dien = next(
            (anh for anh in cac_anh if anh.anh_dai_dien),
            cac_anh[0] if cac_anh else None
        )

        # Chuẩn bị giá và thông tin khuyến mãi
        thong_tin_gia = tao_thong_tin_gia(
            san_pham,
            san_pham.gia_thap_nhat,
            khuyen_mai_theo_sp
        )

        thong_tin_gia["anh_dai_dien"] = anh_dai_dien

        thong_tin_gia["con_hang"] = any(
            bien_the.so_luong_ton > 0
            for bien_the in cac_bien_the
        )

        danh_sach_the.append(thong_tin_gia)

    # 3. Lấy sản phẩm trong bộ sưu tập quà tặng
    danh_sach_theo_ma = {
        str(the["san_pham"].ma_san_pham): the
        for the in danh_sach_the
    }

    san_pham_qua_tang = []

    cac_san_pham_qua_tang = (
        SanPhamQuaTang.objects
        .filter(san_pham__trang_thai_ban="Đang bán")
        .select_related("san_pham")
        .order_by("vi_tri")
    )

    for muc in cac_san_pham_qua_tang:

        the = danh_sach_theo_ma.get(
            str(muc.san_pham_id)
        )

        if the:
            san_pham_qua_tang.append(the)

    # 4. Nhóm sản phẩm nổi bật
    san_pham_noi_bat = danh_sach_the[:4]

    # 5. Lấy danh mục có sản phẩm đang bán
    danh_muc_noi_bat = (
        DanhMucSanPham.objects
        .filter(san_pham__trang_thai_ban="Đang bán")
        .distinct()
        .order_by("ten_danh_muc")[:4]
    )

    # Lấy danh sách thương hiệu
    danh_sach_thuong_hieu = (
        ThuongHieu.objects.all()
        .order_by("ten_thuong_hieu")
    )

    # 6. Lấy lịch sử xem sản phẩm
    lich_su_xem = request.session.get(
        "lich_su_xem_san_pham", []
    )

    lich_su_xem = [
        str(ma) for ma in lich_su_xem
    ]

    # 7. Lấy mã sản phẩm nổi bật
    ma_san_pham_noi_bat = {
        str(the["san_pham"].ma_san_pham)
        for the in san_pham_noi_bat
    }

    # 8. Ưu tiên sản phẩm cùng danh mục với sản phẩm vừa xem
    cac_san_pham_goi_y = danh_sach_the.copy()

    ly_do_goi_y = "Khám phá sản phẩm dành cho bạn"

    if lich_su_xem:

        san_pham_vua_xem = next(
            (
                the for the in danh_sach_the
                if str(the["san_pham"].ma_san_pham)
                == lich_su_xem[0]
            ),
            None
        )

        if san_pham_vua_xem:

            ma_danh_muc = (
                san_pham_vua_xem["san_pham"].danh_muc_id
            )

            san_pham_cung_danh_muc = [
                the for the in danh_sach_the
                if the["san_pham"].danh_muc_id == ma_danh_muc
                and str(the["san_pham"].ma_san_pham)
                not in lich_su_xem
            ]

            if san_pham_cung_danh_muc:
                cac_san_pham_goi_y = san_pham_cung_danh_muc

                ly_do_goi_y = (
                    "Vì bạn quan tâm đến danh mục này"
                )

    # 9. Loại sản phẩm đã xem và sản phẩm nổi bật
    cac_san_pham_goi_y = [
        the for the in cac_san_pham_goi_y
        if str(the["san_pham"].ma_san_pham)
        not in lich_su_xem
        and str(the["san_pham"].ma_san_pham)
        not in ma_san_pham_noi_bat
    ]

    # 10. Chọn tối đa 4 sản phẩm gợi ý
    goi_y_hom_nay = cac_san_pham_goi_y[:4]

    # Nếu không đủ, lấy sản phẩm khác bổ sung
    if len(goi_y_hom_nay) < 4:

        ma_da_chon = {
            str(the["san_pham"].ma_san_pham)
            for the in goi_y_hom_nay
        }

        san_pham_bo_sung = [
            the for the in danh_sach_the
            if str(the["san_pham"].ma_san_pham)
            not in lich_su_xem
            and str(the["san_pham"].ma_san_pham)
            not in ma_san_pham_noi_bat
            and str(the["san_pham"].ma_san_pham)
            not in ma_da_chon
        ]

        goi_y_hom_nay.extend(
            san_pham_bo_sung[:4 - len(goi_y_hom_nay)]
        )

    # 11. Lý do mặc định khi không có lịch sử xem
    if not lich_su_xem:
        ly_do_goi_y = "Khám phá sản phẩm dành cho bạn"

    # 12. Các sản phẩm dùng để xây dựng nhóm gợi ý
    san_pham_chu_de = [
        the for the in danh_sach_the
        if str(the["san_pham"].ma_san_pham)
        not in ma_san_pham_noi_bat
    ]

    # 13. Nhóm Dành cho bạn
    cac_nhom_goi_y = [
        {
            "ma_nhom": "ca_nhan",
            "san_pham": goi_y_hom_nay,
        }
    ]

    # 14. Nhóm Học tập hiệu quả
    hoc_tap = [
        the for the in san_pham_chu_de
        if the["san_pham"].danh_muc_id
        in ["DM001", "DM002", "DM004"]
    ][:3]

    # 15. Nhóm Góc làm việc
    goc_lam_viec = [
        the for the in san_pham_chu_de
        if the["san_pham"].danh_muc_id
        in ["DM001", "DM003", "DM004"]
    ][:6]

    # 16. Nhóm Sáng tạo mỗi ngày
    sang_tao = [
        the for the in san_pham_chu_de
        if the["san_pham"].danh_muc_id
        in ["DM002", "DM003", "DM004"]
    ][:5]

    # Thêm các nhóm chủ đề
    cac_nhom_goi_y.extend([
        {
            "ma_nhom": "hoc_tap",
            "san_pham": hoc_tap,
        },
        {
            "ma_nhom": "goc_lam_viec",
            "san_pham": goc_lam_viec,
        },
        {
            "ma_nhom": "sang_tao",
            "san_pham": sang_tao,
        },
    ])

    # 17. Gộp các nhóm thành danh sách hiển thị
    danh_sach_goi_y = []

    for nhom in cac_nhom_goi_y:
        for the in nhom["san_pham"]:
            danh_sach_goi_y.append({
                "nhom_goi_y": nhom["ma_nhom"],
                "the": the,
            })

    # 18. Lấy danh sách sản phẩm yêu thích
    ma_khach_hang = request.session.get("ma_khach_hang")

    danh_sach_yeu_thich = list(
        SanPhamYeuThich.objects.filter(
            ma_khach_hang=ma_khach_hang
        ).values_list(
            "san_pham_id",
            flat=True
        )
    ) if ma_khach_hang else []

    # 19. Trả dữ liệu về giao diện
    return render(request, "home.html", {
        "san_pham_noi_bat": san_pham_noi_bat,
        "goi_y_hom_nay": danh_sach_goi_y,
        "danh_muc_noi_bat": danh_muc_noi_bat,
        "danh_sach_thuong_hieu": danh_sach_thuong_hieu,
        "ly_do_goi_y": ly_do_goi_y,
        "san_pham_qua_tang": san_pham_qua_tang,
        "danh_sach_yeu_thich": danh_sach_yeu_thich,
    })


# =========================================================
# 6. BASE
# =========================================================

def base(request):
    return render(request, "base.html")


# =========================================================
# 7. CHI TIẾT SẢN PHẨM
# =========================================================


def chi_tiet_san_pham(request, ma_san_pham):

    # Lấy sản phẩm đang bán
    san_pham = get_object_or_404(
        SanPham.objects
        .filter(trang_thai_ban="Đang bán")
        .select_related("danh_muc", "thuong_hieu")
        .prefetch_related("bien_the__hinh_anh"),
        ma_san_pham=ma_san_pham,
    )

    # Lưu sản phẩm vừa xem vào session
    lich_su_xem = request.session.get("lich_su_xem_san_pham", [])
    ma_san_pham = str(san_pham.ma_san_pham)

    lich_su_xem = [
        ma for ma in lich_su_xem
        if str(ma) != ma_san_pham
    ]

    lich_su_xem.insert(0, ma_san_pham)
    request.session["lich_su_xem_san_pham"] = lich_su_xem[:10]

    # Lấy danh sách biến thể
    bien_the_list = list(san_pham.bien_the.all())

    # Gom hình ảnh của các biến thể
    danh_sach_anh = []

    for bien_the in bien_the_list:
        cac_anh = sorted(
            list(bien_the.hinh_anh.all()),
            key=lambda anh: anh.thu_tu_hien_thi,
        )

        for hinh_anh in cac_anh:
            if hinh_anh.duong_dan_anh:
                danh_sach_anh.append({
                    "bien_the": bien_the,
                    "hinh_anh": hinh_anh,
                })

    # Ưu tiên ảnh đại diện
    anh_dai_dien = next(
        (
            item["hinh_anh"]
            for item in danh_sach_anh
            if item["hinh_anh"].anh_dai_dien
        ),
        None,
    )

    if anh_dai_dien is None and danh_sach_anh:
        anh_dai_dien = danh_sach_anh[0]["hinh_anh"]

    # Xác định biến thể mặc định
    bien_the_mac_dinh = next(
        (
            item["bien_the"]
            for item in danh_sach_anh
            if item["hinh_anh"] == anh_dai_dien
        ),
        None,
    )

    if bien_the_mac_dinh is None and bien_the_list:
        bien_the_mac_dinh = bien_the_list[0]

    # Tính giá thấp nhất của các biến thể
    cac_gia = [
        bt.gia_ban
        for bt in bien_the_list
        if bt.gia_ban is not None
    ]

    gia_thap_nhat = min(cac_gia) if cac_gia else None

    # Lấy thông tin khuyến mãi từ database default
    ngay_hien_tai = timezone.localdate()

    chi_tiet_km = (
        ChiTietKhuyenMai.objects.using("default")
        .filter(
            MaSanPham=str(san_pham.ma_san_pham),
            TrangThai=True,
            MaKhuyenMai__NgayBatDau__lte=ngay_hien_tai,
            MaKhuyenMai__NgayKetThuc__gte=ngay_hien_tai,
        )
        .order_by("-MaKhuyenMai__NgayBatDau")
        .first()
    )

    # Kiểm tra khuyến mãi có giá trị hợp lệ
    co_khuyen_mai = (
        chi_tiet_km is not None
        and chi_tiet_km.GiaKhuyenMai is not None
    )

    phan_tram_giam = (
        chi_tiet_km.PhanTramGiam
        if co_khuyen_mai else None
    )

    gia_khuyen_mai_co_dinh = (
        chi_tiet_km.GiaKhuyenMai
        if co_khuyen_mai else None
    )

    # Lấy sản phẩm cùng danh mục
    san_pham_cung_danh_muc = list(
        SanPham.objects
        .filter(
            trang_thai_ban="Đang bán",
            danh_muc=san_pham.danh_muc,
        )
        .exclude(ma_san_pham=san_pham.ma_san_pham)
        .select_related("danh_muc", "thuong_hieu")
        .prefetch_related("bien_the__hinh_anh")
        .order_by("?")[:4]
    )

    san_pham_goi_y = san_pham_cung_danh_muc

    # Nếu chưa đủ 4 sản phẩm, bổ sung từ danh mục khác
    if len(san_pham_goi_y) < 4:
        ma_da_co = [
            sp.ma_san_pham for sp in san_pham_goi_y
        ]
        ma_da_co.append(san_pham.ma_san_pham)

        san_pham_bo_sung = list(
            SanPham.objects
            .filter(trang_thai_ban="Đang bán")
            .exclude(ma_san_pham__in=ma_da_co)
            .select_related("danh_muc", "thuong_hieu")
            .prefetch_related("bien_the__hinh_anh")
            .order_by("?")[:4 - len(san_pham_goi_y)]
        )

        san_pham_goi_y.extend(san_pham_bo_sung)

    # Chuẩn bị ảnh và giá cho sản phẩm gợi ý
    danh_sach_goi_y = []

    for sp in san_pham_goi_y:
        cac_bien_the = list(sp.bien_the.all())

        cac_anh = [
            anh
            for bt in cac_bien_the
            for anh in bt.hinh_anh.all()
            if anh.duong_dan_anh
        ]

        anh_sp = next(
            (anh for anh in cac_anh if anh.anh_dai_dien),
            cac_anh[0] if cac_anh else None,
        )

        cac_gia_goi_y = [
            bt.gia_ban
            for bt in cac_bien_the
            if bt.gia_ban is not None
        ]

        danh_sach_goi_y.append({
            "san_pham": sp,
            "anh_dai_dien": anh_sp,
            "gia_thap_nhat": (
                min(cac_gia_goi_y)
                if cac_gia_goi_y else None
            ),
        })

    # Lấy mã khách hàng đang đăng nhập
    ma_khach_hang = request.session.get("ma_khach_hang")

    # Xử lý khi khách gửi đánh giá
    if request.method == "POST":

        if not ma_khach_hang:
            messages.warning(
                request,
                "Vui lòng đăng nhập tài khoản khách hàng để đánh giá sản phẩm."
            )
            return redirect("KHACHHANG:dang_nhap")

        # Lấy mã biến thể thuộc sản phẩm
        ma_cac_bien_the = list(
            BienTheSanPham.objects.using("sanpham")
            .filter(san_pham=san_pham)
            .values_list("ma_bien_the", flat=True)
        )

        # Kiểm tra khách đã mua và nhận sản phẩm chưa
        da_mua = ChiTietDonHang.objects.using("default").filter(
            ma_don_hang__ma_khach_hang=ma_khach_hang,
            ma_don_hang__trang_thai_don="da_giao",
            trang_thai_giao="da_giao",
            ma_bien_the__in=ma_cac_bien_the,
        ).exists()

        if not da_mua:
            messages.warning(
                request,
                "Bạn cần mua và nhận sản phẩm thành công trước khi đánh giá."
            )
            return redirect(
                "sanpham:chi_tiet_san_pham",
                ma_san_pham=ma_san_pham
            )

        form = DanhGiaSanPhamForm(request.POST)

        if form.is_valid():
            danh_gia = form.save(commit=False)
            danh_gia.san_pham = san_pham
            danh_gia.ma_khach_hang = ma_khach_hang
            danh_gia.save()

            messages.success(
                request,
                "Đánh giá của bạn đã được gửi thành công!"
            )

            return redirect(
                "sanpham:chi_tiet_san_pham",
                ma_san_pham=ma_san_pham
            )

    else:
        form = DanhGiaSanPhamForm()

    # Lấy đánh giá công khai
    danh_sach_danh_gia = san_pham.danh_gia.all()

    # Tính tổng lượt đánh giá và điểm trung bình
    thong_ke_danh_gia = danh_sach_danh_gia.aggregate(
        tong_luot=Count("id"),
        diem_trung_binh=Avg("so_sao")
    )

    tong_luot_danh_gia = thong_ke_danh_gia["tong_luot"] or 0
    diem_trung_binh = thong_ke_danh_gia["diem_trung_binh"] or 0

    # Thống kê số lượt đánh giá theo từng mức sao
    thong_ke_so_sao = {}

    for sao in range(1, 6):
        thong_ke_so_sao[sao] = danh_sach_danh_gia.filter(
            so_sao=sao
        ).count()

    thong_ke_so_sao_list = []

    for sao in range(5, 0, -1):
        so_luong = thong_ke_so_sao[sao]

        ty_le = (
            so_luong / tong_luot_danh_gia * 100
            if tong_luot_danh_gia else 0
        )

        thong_ke_so_sao_list.append({
            "sao": sao,
            "so_luong": so_luong,
            "ty_le": round(ty_le),
        })

    # Lấy tên khách hàng để hiển thị đánh giá
    danh_sach_danh_gia = list(danh_sach_danh_gia)

    ma_khach_hang_danh_gia = {
        dg.ma_khach_hang for dg in danh_sach_danh_gia
    }

    ten_khach_hang = dict(
        HoSoKhachHang.objects.using("default")
        .filter(MaHoSo__in=ma_khach_hang_danh_gia)
        .values_list("MaHoSo", "HoVaTen")
    )

    for dg in danh_sach_danh_gia:
        dg.ten_nguoi_danh_gia = ten_khach_hang.get(
            dg.ma_khach_hang,
            "Khách hàng NOSCO"
        )

    # Trả dữ liệu sang template
    return render(
        request,
        "SANPHAM/chi_tiet_san_pham.html",
        {
            "san_pham": san_pham,
            "bien_the_list": bien_the_list,
            "danh_sach_anh": danh_sach_anh,
            "anh_dai_dien": anh_dai_dien,
            "bien_the_mac_dinh": bien_the_mac_dinh,
            "gia_thap_nhat": gia_thap_nhat,
            "co_khuyen_mai": co_khuyen_mai,
            "phan_tram_giam": phan_tram_giam,
            "gia_khuyen_mai_co_dinh": gia_khuyen_mai_co_dinh,
            "danh_sach_goi_y": danh_sach_goi_y,
            "danh_sach_danh_gia": danh_sach_danh_gia,
            "tong_luot_danh_gia": tong_luot_danh_gia,
            "diem_trung_binh": diem_trung_binh,
            "thong_ke_so_sao": thong_ke_so_sao,
            "thong_ke_so_sao_list": thong_ke_so_sao_list,
            "form_danh_gia": form,
        },
    )



# =========================================================
# 8. DANH SÁCH THƯƠNG HIỆU
# =========================================================

def danh_sach_thuong_hieu(request):

    thuong_hieus = ThuongHieu.objects.all().order_by(
        "ten_thuong_hieu"
    )

    return render(
        request,
        "SANPHAM/danh_sach_thuong_hieu.html",
        {
            "thuong_hieus": thuong_hieus,
        }
    )


# =========================================================
# 9. DANH SÁCH BÀI VIẾT
# =========================================================

def danh_sach_bai_viet(request):

    bai_viets = BaiViet.objects.filter(
        trang_thai="Đã đăng"
    ).order_by("-ngay_dang")

    return render(
        request,
        "SANPHAM/danh_sach_bai_viet.html",
        {
            "bai_viets": bai_viets,
        }
    )


# =========================================================
# 10. GIỚI THIỆU
# =========================================================

def ve_chung_toi(request):
    return render(request, "ve_chung_toi.html")


# =========================================================
# 11. SẢN PHẨM YÊU THÍCH
# =========================================================

@khach_hang_required
def san_pham_yeu_thich(request):

    # Lấy mã khách hàng
    ma_khach_hang = request.session.get("ma_khach_hang")

    # Lấy danh sách mã sản phẩm yêu thích
    danh_sach_yeu_thich = list(
        SanPhamYeuThich.objects.filter(
            ma_khach_hang=ma_khach_hang
        ).values_list(
            "san_pham_id",
            flat=True
        )
    )

    # Lấy sản phẩm yêu thích đang bán
    san_pham_queryset = (
        SanPham.objects
        .filter(
            trang_thai_ban="Đang bán",
            ma_san_pham__in=danh_sach_yeu_thich
        )
        .select_related("thuong_hieu", "danh_muc")
        .prefetch_related("bien_the__hinh_anh")
    )

    cac_san_pham = list(san_pham_queryset)

    # Lấy khuyến mãi đang áp dụng
    khuyen_mai_theo_sp = lay_khuyen_mai_theo_san_pham(
        [sp.ma_san_pham for sp in cac_san_pham]
    )

    danh_sach_san_pham = []

    for san_pham in cac_san_pham:

        cac_bien_the = list(san_pham.bien_the.all())

        # Lấy ảnh đại diện
        cac_anh = [
            anh
            for bien_the in cac_bien_the
            for anh in bien_the.hinh_anh.all()
            if anh.duong_dan_anh
        ]

        anh_dai_dien = next(
            (anh for anh in cac_anh if anh.anh_dai_dien),
            cac_anh[0] if cac_anh else None,
        )

        # Tính giá thấp nhất
        cac_gia = [
            bien_the.gia_ban
            for bien_the in cac_bien_the
            if bien_the.gia_ban is not None
        ]

        gia_thap_nhat = min(cac_gia) if cac_gia else None

        # Chuẩn bị thông tin giá và khuyến mãi
        thong_tin_gia = tao_thong_tin_gia(
            san_pham,
            gia_thap_nhat,
            khuyen_mai_theo_sp
        )

        thong_tin_gia["anh_dai_dien"] = anh_dai_dien
        thong_tin_gia["con_hang"] = any(
            bien_the.so_luong_ton > 0
            for bien_the in cac_bien_the
        )

        danh_sach_san_pham.append(thong_tin_gia)

    return render(
        request,
        "SANPHAM/san_pham_yeu_thich.html",
        {
            "danh_sach_san_pham": danh_sach_san_pham,
            "so_luong_yeu_thich": len(danh_sach_san_pham),
        }
    )


# =========================================================
# 12. BẬT / TẮT SẢN PHẨM YÊU THÍCH
# =========================================================


@khach_hang_required
@require_POST
def toggle_favorite(request):

    ma_san_pham = request.POST.get("ma_san_pham")

    ma_khach_hang = request.session.get("ma_khach_hang")

    san_pham = get_object_or_404(
        SanPham,
        ma_san_pham=ma_san_pham,
        trang_thai_ban="Đang bán"
    )

    yeu_thich = SanPhamYeuThich.objects.filter(
        ma_khach_hang=ma_khach_hang,
        san_pham=san_pham
    )

    if yeu_thich.exists():

        yeu_thich.delete()
        da_yeu_thich = False

    else:

        SanPhamYeuThich.objects.create(
            ma_khach_hang=ma_khach_hang,
            san_pham=san_pham
        )

        da_yeu_thich = True

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        return JsonResponse({
            "success": True,
            "da_yeu_thich": da_yeu_thich,
            "ma_san_pham": san_pham.ma_san_pham,
        })

    next_url = request.POST.get("next", "/")

    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()}
    ):
        next_url = "/"

    return redirect(next_url)


# =========================================================
# 13. TRANG HỖ TRỢ
# =========================================================

def trang_ho_tro(request, slug):

    cac_trang = {
        "huong-dan-dat-hang": "Hướng dẫn đặt hàng",
        "chinh-sach-giao-hang": "Chính sách giao hàng",
        "phuong-thuc-thanh-toan": "Phương thức thanh toán",
        "chinh-sach-bao-mat": "Chính sách bảo mật",
    }

    tieu_de = cac_trang.get(slug)

    if tieu_de is None:
        from django.http import Http404
        raise Http404

    return render(
        request,
        "SANPHAM/trang_ho_tro.html",
        {
            "tieu_de": tieu_de,
        }
    )
