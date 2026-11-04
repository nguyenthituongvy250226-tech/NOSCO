from django.shortcuts import render, get_object_or_404

from decimal import Decimal, InvalidOperation

from django.db.models import Min, Q

from .models import SanPham, DanhMucSanPham, ThuongHieu



def danh_sach_san_pham(request):
    # 1. Nhận các điều kiện tìm kiếm và lọc từ URL
    tu_khoa = request.GET.get("q", "").strip()
    ma_danh_muc = request.GET.get("danh_muc", "").strip()
    ma_thuong_hieu = request.GET.get("thuong_hieu", "").strip()
    gia_tu_text = request.GET.get("gia_tu", "").strip()
    gia_den_text = request.GET.get("gia_den", "").strip()
    sap_xep = request.GET.get("sap_xep", "ten_a_z")

    # 2. Chỉ lấy sản phẩm đang bán, tính giá thấp nhất
    san_pham_queryset = (
        SanPham.objects
        .filter(trang_thai_ban="Đang bán")
        .select_related("danh_muc", "thuong_hieu")
        .prefetch_related("bien_the__hinh_anh")
        .annotate(gia_thap_nhat=Min("bien_the__gia_ban"))
    )

    # 3. Tìm theo tên sản phẩm hoặc mô tả
    if tu_khoa:
        san_pham_queryset = san_pham_queryset.filter(
            Q(ten_san_pham__icontains=tu_khoa)
            | Q(mo_ta__icontains=tu_khoa)
        )

    # 4. Lọc theo danh mục và thương hiệu
    if ma_danh_muc:
        san_pham_queryset = san_pham_queryset.filter(
            danh_muc_id=ma_danh_muc
        )

    if ma_thuong_hieu:
        san_pham_queryset = san_pham_queryset.filter(
            thuong_hieu_id=ma_thuong_hieu
        )

    # 5. Kiểm tra giá nhập vào có hợp lệ không
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

    # 6. Lọc theo giá thấp nhất của sản phẩm
    if gia_tu is not None:
        san_pham_queryset = san_pham_queryset.filter(
            gia_thap_nhat__gte=gia_tu
        )

    if gia_den is not None:
        san_pham_queryset = san_pham_queryset.filter(
            gia_thap_nhat__lte=gia_den
        )

    # 7. Sắp xếp kết quả
    if sap_xep == "gia_tang":
        san_pham_queryset = san_pham_queryset.order_by(
            "gia_thap_nhat", "ten_san_pham"
        )
    elif sap_xep == "gia_giam":
        san_pham_queryset = san_pham_queryset.order_by(
            "-gia_thap_nhat", "ten_san_pham"
        )
    elif sap_xep == "moi_nhat":
        san_pham_queryset = san_pham_queryset.order_by(
            "-ngay_tao", "ten_san_pham"
        )
    else:
        sap_xep = "ten_a_z"
        san_pham_queryset = san_pham_queryset.order_by(
            "ten_san_pham"
        )

    # 8. Chuẩn bị ảnh đại diện và giá cho từng sản phẩm
    danh_sach_san_pham = []

    for san_pham in san_pham_queryset:
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

        danh_sach_san_pham.append({
            "san_pham": san_pham,
            "anh_dai_dien": anh_dai_dien,
            "gia_thap_nhat": san_pham.gia_thap_nhat,
        })

    # 9. Gửi dữ liệu cho giao diện
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
        },
    )


def home(request):
    return render(request, "home.html")


def base(request):
    return render(request, "base.html")


def chi_tiet_san_pham(request, ma_san_pham):
    # Lấy sản phẩm đang bán theo mã sản phẩm.
    san_pham = get_object_or_404(
        SanPham.objects
        .filter(trang_thai_ban="Đang bán")
        .select_related("danh_muc", "thuong_hieu")
        .prefetch_related("bien_the__hinh_anh"),
        ma_san_pham=ma_san_pham,
    )

    # Lấy danh sách biến thể của sản phẩm.
    bien_the_list = list(san_pham.bien_the.all())

    # Gom tất cả hình ảnh của các biến thể.
    danh_sach_anh = []

    for bien_the in bien_the_list:
        cac_anh = sorted(
            list(bien_the.hinh_anh.all()),
            key=lambda anh: anh.thu_tu_hien_thi,
        )

        for hinh_anh in cac_anh:
            # Chỉ đưa vào danh sách ảnh đã có file ảnh thực tế.
            if hinh_anh.duong_dan_anh:
                danh_sach_anh.append({
                    "bien_the": bien_the,
                    "hinh_anh": hinh_anh,
                })

    # Ưu tiên ảnh được đánh dấu là ảnh đại diện.
    anh_dai_dien = next(
        (
            item["hinh_anh"]
            for item in danh_sach_anh
            if item["hinh_anh"].anh_dai_dien
        ),
        None,
    )

    # Nếu chưa đánh dấu ảnh đại diện, lấy ảnh đầu tiên.
    if anh_dai_dien is None and danh_sach_anh:
        anh_dai_dien = danh_sach_anh[0]["hinh_anh"]

    # Xác định biến thể mặc định tương ứng với ảnh đại diện.
    bien_the_mac_dinh = next(
        (
            item["bien_the"]
            for item in danh_sach_anh
            if item["hinh_anh"] == anh_dai_dien
        ),
        None,
    )

    # Nếu chưa xác định được, lấy biến thể đầu tiên.
    if bien_the_mac_dinh is None and bien_the_list:
        bien_the_mac_dinh = bien_the_list[0]

    # Tính giá thấp nhất trong các biến thể.
    cac_gia = [bien_the.gia_ban for bien_the in bien_the_list]
    gia_thap_nhat = min(cac_gia) if cac_gia else None

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
        },
    )
