from decimal import Decimal, InvalidOperation

from django.shortcuts import render, get_object_or_404
from django.db.models import Min, Q

from .models import SanPham, DanhMucSanPham, ThuongHieu, BaiViet,SanPhamQuaTang



def danh_sach_san_pham(request):
    # 1. Nhận các điều kiện tìm kiếm và lọc từ URL
    tu_khoa = request.GET.get("q", "").strip()
    ma_danh_muc = request.GET.get("danh_muc", "").strip()
    nhom = request.GET.get("nhom", "").strip()
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

    # Lấy thương hiệu được chọn từ URL
    thuong_hieu_id = request.GET.get("thuong_hieu")

    # Nếu khách hàng chọn thương hiệu, chỉ lấy sản phẩm của thương hiệu đó
    if thuong_hieu_id and thuong_hieu_id.isdigit():
        san_pham_queryset = san_pham_queryset.filter(thuong_hieu_id=int(thuong_hieu_id))

    # 3. Tìm theo tên sản phẩm hoặc mô tả
    # 3. Tìm theo tên, mô tả, thương hiệu và danh mục
    if tu_khoa:
        tu_khoa = tu_khoa.strip()

        san_pham_queryset = san_pham_queryset.filter(
            Q(ten_san_pham__icontains=tu_khoa)
            | Q(thuong_hieu__ten_thuong_hieu__icontains=tu_khoa)
            | Q(danh_muc__ten_danh_muc__icontains=tu_khoa)
        ).distinct()

    # 4. Lọc theo danh mục và thương hiệu
    # 4. Lọc theo nhóm, danh mục và thương hiệu

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
            "gia_hien_thi": dinh_dang_gia(san_pham.gia_thap_nhat),
        })
        # 9. Khởi tạo danh sách sản phẩm gợi ý
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

        for san_pham in goi_y_queryset:
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

            san_pham_goi_y.append({
                "san_pham": san_pham,
                "anh_dai_dien": anh_dai_dien,
                "gia_thap_nhat": san_pham.gia_thap_nhat,
                "gia_hien_thi": dinh_dang_gia(san_pham.gia_thap_nhat),
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
            "san_pham_goi_y": san_pham_goi_y,
        },
    )



def dinh_dang_gia(gia):
    if gia is None:
        return None
    return f"{gia:,.0f}".replace(",", ".")

def home(request):
    # Lấy các sản phẩm đang bán và thông tin liên quan
    san_pham_queryset = (
        SanPham.objects
        .filter(trang_thai_ban="Đang bán")
        .select_related("danh_muc", "thuong_hieu")
        .prefetch_related("bien_the__hinh_anh")
        .annotate(gia_thap_nhat=Min("bien_the__gia_ban"))
        .order_by("-ngay_tao", "ten_san_pham")
    )

    # Chuyển thông tin sản phẩm thành dữ liệu dùng cho giao diện
    danh_sach_the = []

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
            cac_anh[0] if cac_anh else None
        )

        danh_sach_the.append({
            "san_pham": san_pham,
            "anh_dai_dien": anh_dai_dien,
            "gia_thap_nhat": san_pham.gia_thap_nhat,
            "gia_hien_thi": dinh_dang_gia(san_pham.gia_thap_nhat),
            "con_hang": any(
                bien_the.so_luong_ton > 0
                for bien_the in cac_bien_the
            ),
        })

        # Lấy 8 sản phẩm được chọn trong bộ sưu tập quà tặng
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

    # Nhóm sản phẩm nổi bật: 4 sản phẩm mới nhất
    san_pham_noi_bat = danh_sach_the[:4]

    # Nhóm gợi ý hôm nay: 4 sản phẩm tiếp theo
    goi_y_hom_nay = danh_sach_the[4:8]

    # Lấy tối đa 4 danh mục có sản phẩm đang bán
    danh_muc_noi_bat = (
        DanhMucSanPham.objects
        .filter(san_pham__trang_thai_ban="Đang bán")
        .distinct()
        .order_by("ten_danh_muc")[:4]
    )
    danh_sach_thuong_hieu = ThuongHieu.objects.all().order_by(
        "ten_thuong_hieu"
    )
    # Sản phẩm nổi bật: giữ nguyên cách lấy 4 sản phẩm mới nhất
    # 4 sản phẩm nổi bật
    san_pham_noi_bat = danh_sach_the[:4]

    # Lấy lịch sử xem sản phẩm
    lich_su_xem = request.session.get(
        "lich_su_xem_san_pham", []
    )
    lich_su_xem = [str(ma) for ma in lich_su_xem]

    # Lấy mã sản phẩm nổi bật để tránh trùng
    ma_san_pham_noi_bat = {
        str(the["san_pham"].ma_san_pham)
        for the in san_pham_noi_bat
    }

    # Ưu tiên sản phẩm cùng danh mục với sản phẩm xem gần nhất
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
                ly_do_goi_y = "Vì bạn quan tâm đến danh mục này"

    # Loại sản phẩm đã xem và sản phẩm nổi bật
    cac_san_pham_goi_y = [
        the for the in cac_san_pham_goi_y
        if str(the["san_pham"].ma_san_pham)
           not in lich_su_xem
           and str(the["san_pham"].ma_san_pham)
           not in ma_san_pham_noi_bat
    ]

    # Chọn tối đa 4 sản phẩm gợi ý
    goi_y_hom_nay = cac_san_pham_goi_y[:4]

    # Nếu không đủ sản phẩm cùng danh mục, lấy sản phẩm khác
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

    # Lý do mặc định khi không có lịch sử xem
    if not lich_su_xem:
        ly_do_goi_y = "Khám phá sản phẩm dành cho bạn"
    # Các sản phẩm dùng để xây dựng nhóm gợi ý chủ đề
    san_pham_chu_de = [
        the for the in danh_sach_the
        if str(the["san_pham"].ma_san_pham)
        not in ma_san_pham_noi_bat
    ]

    # Nhóm Dành cho bạn: giữ kết quả gợi ý cá nhân hóa
    cac_nhom_goi_y = [
        {
            "ma_nhom": "ca_nhan",
            "san_pham": goi_y_hom_nay,
        }
    ]

    # Nhóm Học tập hiệu quả: bút, vở và dụng cụ học tập
    hoc_tap = [
        the for the in san_pham_chu_de
        if the["san_pham"].danh_muc_id in ["DM001", "DM002", "DM004"]
    ][:3]

    # Nhóm Góc làm việc: bút, giấy và dụng cụ hỗ trợ làm việc
    goc_lam_viec = [
        the for the in san_pham_chu_de
        if the["san_pham"].danh_muc_id in ["DM001", "DM003", "DM004"]
    ][:6]

    # Nhóm Sáng tạo mỗi ngày: vở, giấy và dụng cụ học tập
    sang_tao = [
        the for the in san_pham_chu_de
        if the["san_pham"].danh_muc_id in ["DM002", "DM003", "DM004"]
    ][:5]

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

    # Gộp các nhóm thành danh sách để hiển thị trên giao diện
    danh_sach_goi_y = []

    for nhom in cac_nhom_goi_y:
        for the in nhom["san_pham"]:
            danh_sach_goi_y.append({
                "nhom_goi_y": nhom["ma_nhom"],
                "the": the,
            })

    return render(request, "home.html", {
        "san_pham_noi_bat": san_pham_noi_bat,
        "goi_y_hom_nay": danh_sach_goi_y,
        "danh_muc_noi_bat": danh_muc_noi_bat,
        "danh_sach_thuong_hieu": danh_sach_thuong_hieu,
        "ly_do_goi_y": ly_do_goi_y,
        "san_pham_qua_tang": san_pham_qua_tang,
    })


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
    # Lưu sản phẩm khách vừa xem vào session
    lich_su_xem = request.session.get("lich_su_xem_san_pham", [])

    ma_san_pham = str(san_pham.ma_san_pham)

    # Đưa sản phẩm vừa xem lên đầu danh sách
    lich_su_xem = [
        ma for ma in lich_su_xem
        if str(ma) != ma_san_pham
    ]

    lich_su_xem.insert(0, ma_san_pham)

    # Chỉ lưu tối đa 10 sản phẩm gần nhất
    request.session["lich_su_xem_san_pham"] = lich_su_xem[:10]

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

    # Lấy sản phẩm cùng danh mục, loại sản phẩm đang xem.
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

    # Nếu chưa đủ 4 sản phẩm, bổ sung từ danh mục khác.
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

    # Chuẩn bị ảnh đại diện và giá thấp nhất.
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

        cac_gia = [
            bt.gia_ban
            for bt in cac_bien_the
            if bt.gia_ban is not None
        ]

        danh_sach_goi_y.append({
            "san_pham": sp,
            "anh_dai_dien": anh_sp,
            "gia_thap_nhat": min(cac_gia) if cac_gia else None,
        })


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
            "danh_sach_goi_y": danh_sach_goi_y,
        },
    )

def danh_sach_thuong_hieu(request):
    thuong_hieus = ThuongHieu.objects.all().order_by("ten_thuong_hieu")

    return render(request, "SANPHAM/danh_sach_thuong_hieu.html", {
        "thuong_hieus": thuong_hieus,
    })
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



def ve_chung_toi(request):
    return render(request, "ve_chung_toi.html")