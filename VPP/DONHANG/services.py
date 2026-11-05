"""Các hàm nghiệp vụ dùng chung cho module đơn hàng và module khác."""

from decimal import Decimal, InvalidOperation
from datetime import timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from .models import (
    BangChungYeuCauTraHang,
    ChiTietDonHang,
    ChiTietYeuCauTraHang,
    DonHang,
    GiaoHang,
    YeuCauTraHang,
)


def _tra_yeu_cau(yeu_cau, trang_thai, ket_qua=""):
    from django.utils import timezone

    yeu_cau.trang_thai_tra = trang_thai
    yeu_cau.ket_qua_xl = ket_qua
    yeu_cau.ngay_xu_ly = timezone.now()
    yeu_cau.save(update_fields=["trang_thai_tra", "ket_qua_xl", "ngay_xu_ly"])


@transaction.atomic
def xu_ly_don_hang(don, *, hanh_dong):
    """Nhân viên xác nhận đơn hoặc hủy đơn hết hàng."""
    don = DonHang.objects.select_for_update().get(pk=don.pk)
    previous_status = don.trang_thai_don
    if don.trang_thai_don != "cho_xac_nhan":
        raise DuLieuDonHangKhongHopLe("Chỉ xử lý được đơn đang chờ xác nhận.")
    if hanh_dong == "xac_nhan":
        don.trang_thai_don = "cho_lay_hang"
        try:
            giao = don.giao_hang
            giao.trang_thai = "cho_lay_hang"
            giao.save(update_fields=["trang_thai", "cap_nhat_luc"])
        except GiaoHang.DoesNotExist:
            pass
    elif hanh_dong == "het_hang":
        don.trang_thai_don = "da_huy"
        ChiTietDonHang.objects.filter(ma_don_hang=don).update(trang_thai_giao="da_huy")
        try:
            giao = don.giao_hang
            giao.trang_thai = "giao_that_bai"
            giao.ly_do_that_bai = "Đơn hàng hết hàng"
            giao.save(update_fields=["trang_thai", "ly_do_that_bai", "cap_nhat_luc"])
        except GiaoHang.DoesNotExist:
            pass
    else:
        raise DuLieuDonHangKhongHopLe("Hành động xử lý đơn không hợp lệ.")
    don.save(update_fields=["trang_thai_don"])
    _phat_tin_trang_thai(don, previous_status)
    return don


@transaction.atomic
def khach_huy_don_hang(don):
    """Khách chỉ hủy được đơn còn đang chờ nhân viên xác nhận."""
    don = DonHang.objects.select_for_update().get(pk=don.pk)
    previous_status = don.trang_thai_don
    if don.trang_thai_don != "cho_xac_nhan":
        raise DuLieuDonHangKhongHopLe("Chỉ hủy được đơn đang chờ xác nhận.")
    don.trang_thai_don = "da_huy"
    don.save(update_fields=["trang_thai_don"])
    ChiTietDonHang.objects.filter(ma_don_hang=don).update(trang_thai_giao="da_huy")
    _phat_tin_trang_thai(don, previous_status)
    return don


@transaction.atomic
def cap_nhat_thong_tin_nhan(don, *, ten_nguoi_nhan, sdt_nguoi_nhan, dia_chi_nhan_hang, ghi_chu):
    don = DonHang.objects.select_for_update().get(pk=don.pk)
    if don.trang_thai_don != "cho_xac_nhan":
        raise DuLieuDonHangKhongHopLe("Chỉ sửa được đơn đang chờ xác nhận.")
    don.ten_nguoi_nhan = ten_nguoi_nhan
    don.sdt_nguoi_nhan = sdt_nguoi_nhan
    don.dia_chi_nhan_hang = dia_chi_nhan_hang
    don.ghi_chu = ghi_chu
    don.save(update_fields=[
        "ten_nguoi_nhan", "sdt_nguoi_nhan", "dia_chi_nhan_hang", "ghi_chu"
    ])
    return don


@transaction.atomic
def khach_xac_nhan_da_nhan(don):
    """Khách xác nhận đã nhận hàng, kết thúc sớm thời hạn yêu cầu trả."""
    don = DonHang.objects.select_for_update().get(pk=don.pk)
    if don.trang_thai_don not in {"cho_giao_hang", "cho_xac_nhan_nhan"}:
        raise DuLieuDonHangKhongHopLe("Đơn hàng không còn chờ bạn xác nhận đã nhận.")
    try:
        giao = don.giao_hang
    except GiaoHang.DoesNotExist:
        raise DuLieuDonHangKhongHopLe("Không tìm thấy thông tin giao hàng.")
    if giao.trang_thai != "da_giao" or not giao.ngay_giao_thanh_cong:
        raise DuLieuDonHangKhongHopLe("Đơn hàng chưa được giao thành công.")
    if timezone.now() > giao.ngay_giao_thanh_cong + timedelta(hours=24):
        raise DuLieuDonHangKhongHopLe("Đã hết thời hạn xác nhận. Hãy tải lại chi tiết đơn hàng.")
    previous_status = don.trang_thai_don
    don.khach_da_xac_nhan_nhan = True
    don.trang_thai_don = "da_giao"
    don.save(update_fields=["khach_da_xac_nhan_nhan", "trang_thai_don"])
    _phat_tin_trang_thai(don, previous_status)
    return don


@transaction.atomic
def tao_yeu_cau_tra_hang(
    don, *, ly_do_tra, mo_ta_van_de, ma_van_don_khach,
    phuong_thuc_hoan_tien, san_pham, tep_minh_chung=(), ma_thanh_toan="",
):
    """Lưu yêu cầu trả một phần/toàn bộ sản phẩm đã giao."""
    don = DonHang.objects.select_for_update().get(pk=don.pk)
    previous_status = don.trang_thai_don
    if don.khach_da_xac_nhan_nhan:
        raise DuLieuDonHangKhongHopLe("Bạn đã xác nhận nhận hàng nên không thể gửi yêu cầu trả.")
    if don.trang_thai_don not in {"cho_giao_hang", "cho_xac_nhan_nhan", "da_giao"}:
        raise DuLieuDonHangKhongHopLe("Chỉ có thể yêu cầu trả hàng sau khi đơn đã giao.")
    try:
        giao_hang = don.giao_hang
    except GiaoHang.DoesNotExist:
        raise DuLieuDonHangKhongHopLe("Không tìm thấy trạng thái giao hàng.")
    if (
        giao_hang.trang_thai != "da_giao"
        or not giao_hang.ngay_giao_thanh_cong
        or timezone.now() > giao_hang.ngay_giao_thanh_cong + timedelta(hours=24)
    ):
        raise DuLieuDonHangKhongHopLe("Thời hạn yêu cầu trả hàng 24 giờ đã kết thúc.")
    if YeuCauTraHang.objects.filter(ma_don_hang=don).exists():
        raise DuLieuDonHangKhongHopLe("Đơn hàng đã có yêu cầu trả hàng.")
    if not ly_do_tra.strip() or not mo_ta_van_de.strip() or not san_pham:
        raise DuLieuDonHangKhongHopLe("Cần chọn lý do, mô tả vấn đề và ít nhất một sản phẩm muốn trả.")

    ma_yeu_cau_tra = _ma("RT")
    request = YeuCauTraHang.objects.create(
        ma_yeu_cau_tra=ma_yeu_cau_tra,
        ma_don_hang=don,
        ma_thanh_toan=ma_thanh_toan.strip(),
        ly_do_tra=ly_do_tra.strip(),
        mo_ta_van_de=mo_ta_van_de.strip(),
        ma_van_don_khach=ma_van_don_khach.strip(),
        phuong_thuc_hoan_tien=phuong_thuc_hoan_tien,
        ma_van_don_tra=f"MVD{ma_yeu_cau_tra[2:]}",
    )
    items = {str(item.pk): item for item in don.chi_tiet.all()}
    for item_id, quantity in san_pham.items():
        item = items.get(str(item_id))
        quantity = int(quantity)
        if item is None or quantity < 1 or quantity > item.so_luong:
            raise DuLieuDonHangKhongHopLe("Sản phẩm hoặc số lượng trả không hợp lệ.")
        ChiTietYeuCauTraHang.objects.create(
            yeu_cau=request, chi_tiet_don_hang=item, so_luong=quantity
        )
    for file in tep_minh_chung:
        BangChungYeuCauTraHang.objects.create(
            yeu_cau=request,
            tep=file,
            ten_tep=file.name[:255],
            loai_tep=getattr(file, "content_type", "") or "",
        )
    don.trang_thai_don = "tra_hang"
    don.save(update_fields=["trang_thai_don"])
    _phat_tin_trang_thai(don, previous_status)
    from .signals import yeu_cau_tra_hang_da_tao
    transaction.on_commit(lambda: yeu_cau_tra_hang_da_tao.send_robust(
        sender=YeuCauTraHang,
        yeu_cau=request,
        don_hang=don,
    ), robust=True)
    return request


@transaction.atomic
def xu_ly_yeu_cau_tra_hang(
    yeu_cau, *, hanh_dong, ket_qua="", don_vi_van_chuyen_tra="", ma_van_don_tra=""
):
    """Duyệt/từ chối yêu cầu hoặc đánh dấu hoàn tất sau khi đã duyệt."""
    yeu_cau = YeuCauTraHang.objects.select_for_update().select_related("ma_don_hang").get(pk=yeu_cau.pk)
    if hanh_dong == "hoan_tat":
        if yeu_cau.trang_thai_tra != "da_duyet":
            raise DuLieuDonHangKhongHopLe("Chỉ đánh dấu hoàn tất sau khi yêu cầu đã được duyệt.")
    elif yeu_cau.trang_thai_tra != "cho_xu_ly":
        raise DuLieuDonHangKhongHopLe("Yêu cầu này đã được xử lý.")
    if hanh_dong not in {"da_duyet", "tu_choi", "hoan_tat"}:
        raise DuLieuDonHangKhongHopLe("Kết quả xử lý không hợp lệ.")
    if hanh_dong == "da_duyet" and not don_vi_van_chuyen_tra.strip():
        raise DuLieuDonHangKhongHopLe("Cần chọn đơn vị vận chuyển trả hàng trước khi duyệt.")
    if hanh_dong == "da_duyet":
        yeu_cau.don_vi_van_chuyen_tra = don_vi_van_chuyen_tra.strip()
        yeu_cau.ma_van_don_tra = f"MVD{yeu_cau.ma_yeu_cau_tra[2:]}"
        yeu_cau.save(update_fields=["don_vi_van_chuyen_tra", "ma_van_don_tra"])
    _tra_yeu_cau(yeu_cau, hanh_dong, ket_qua.strip())
    don = yeu_cau.ma_don_hang
    if hanh_dong == "tu_choi":
        previous_status = don.trang_thai_don
        don.trang_thai_don = "da_giao"
        don.save(update_fields=["trang_thai_don"])
        _phat_tin_trang_thai(don, previous_status)
    elif hanh_dong == "da_duyet":
        # Module thanh toán có thể đăng ký listener để xử lý hoàn tiền.
        from .signals import yeu_cau_tra_hang_da_duyet
        transaction.on_commit(lambda: yeu_cau_tra_hang_da_duyet.send_robust(
            sender=YeuCauTraHang, yeu_cau=yeu_cau, don_hang=don
        ), robust=True)
    elif hanh_dong == "hoan_tat":
        from .signals import yeu_cau_tra_hang_da_hoan_tat
        transaction.on_commit(lambda: yeu_cau_tra_hang_da_hoan_tat.send_robust(
            sender=YeuCauTraHang, yeu_cau=yeu_cau, don_hang=don
        ), robust=True)
    from .signals import yeu_cau_tra_hang_da_xu_ly
    transaction.on_commit(lambda: yeu_cau_tra_hang_da_xu_ly.send_robust(
        sender=YeuCauTraHang,
        yeu_cau=yeu_cau,
        don_hang=don,
        ket_qua=hanh_dong,
    ), robust=True)
    return yeu_cau


class DuLieuDonHangKhongHopLe(ValueError):
    pass


def _phat_tin_trang_thai(don, trang_thai_cu):
    trang_thai_moi = don.trang_thai_don
    if trang_thai_cu != trang_thai_moi:
        def send_signal():
            from .signals import don_hang_trang_thai_thay_doi
            don_hang_trang_thai_thay_doi.send_robust(
                sender=DonHang,
                don_hang=don,
                trang_thai_cu=trang_thai_cu,
                trang_thai_moi=trang_thai_moi,
            )
        transaction.on_commit(send_signal, robust=True)


def _ma(prefix):
    return f"{prefix}{uuid4().hex[:8].upper()}"


@transaction.atomic
def tao_don_hang(data):
    """Tạo đơn từ dict Python; phù hợp để giỏ hàng/thanh toán gọi trực tiếp.

    `items` gồm các phần tử: ma_bien_the, so_luong, don_gia.
    Các mã khách hàng, địa chỉ, voucher là mã tham chiếu từ module tương ứng.
    """
    try:
        items = data.get("items") or data.get("chi_tiet") or []
        if not items:
            raise DuLieuDonHangKhongHopLe("Đơn hàng phải có ít nhất một sản phẩm.")
        required = ("ma_khach_hang", "ma_dia_chi", "ten_nguoi_nhan", "sdt_nguoi_nhan", "dia_chi_nhan_hang")
        missing = [field for field in required if not str(data.get(field, "")).strip()]
        if missing:
            raise DuLieuDonHangKhongHopLe("Thiếu thông tin: " + ", ".join(missing))

        normalized = []
        tong_hang = Decimal("0")
        for item in items:
            ma_bien_the = str(item.get("ma_bien_the", "")).strip()
            so_luong = int(item.get("so_luong", 0))
            don_gia = Decimal(str(item.get("don_gia", "0")))
            if not ma_bien_the or so_luong <= 0 or don_gia < 0:
                raise DuLieuDonHangKhongHopLe("Sản phẩm, số lượng hoặc đơn giá không hợp lệ.")
            thanh_tien = don_gia * so_luong
            tong_hang += thanh_tien
            normalized.append((ma_bien_the, so_luong, don_gia, thanh_tien))

        giam = Decimal(str(data.get("so_tien_giam", "0")))
        phi_ship = Decimal(str(data.get("phi_van_chuyen", "0")))
        if giam < 0 or phi_ship < 0:
            raise DuLieuDonHangKhongHopLe("Tiền giảm và phí vận chuyển không được âm.")
        tong_thanh_toan = max(Decimal("0"), tong_hang - giam + phi_ship)

        don = DonHang.objects.create(
            ma_don_hang=_ma("DH"),
            ma_khach_hang=str(data["ma_khach_hang"]).strip(),
            ma_dia_chi=str(data["ma_dia_chi"]).strip(),
            ma_voucher=str(data.get("ma_voucher", "")).strip() or None,
            ngay_dat=timezone.now(),
            ten_nguoi_nhan=str(data["ten_nguoi_nhan"]).strip(),
            sdt_nguoi_nhan=str(data["sdt_nguoi_nhan"]).strip(),
            dia_chi_nhan_hang=str(data["dia_chi_nhan_hang"]).strip(),
            tong_tien_hang=tong_hang,
            so_tien_giam=giam,
            tong_tien=tong_thanh_toan,
            ghi_chu=str(data.get("ghi_chu", "")).strip(),
        )
        ChiTietDonHang.objects.bulk_create([
            ChiTietDonHang(
                ma_chi_tiet_dh=_ma("CT"),
                ma_don_hang=don,
                ma_bien_the=ma,
                so_luong=qty,
                don_gia=price,
                thanh_tien=line_total,
                trang_thai_giao="cho_lay_hang",
            )
            for ma, qty, price, line_total in normalized
        ])
        GiaoHang.objects.create(
            ma_giao_hang=_ma("GH"),
            don_hang=don,
            phi_van_chuyen=phi_ship,
        )
        from .signals import don_hang_da_tao
        transaction.on_commit(lambda: don_hang_da_tao.send_robust(
            sender=DonHang,
            don_hang=don,
        ), robust=True)
        return don
    except (InvalidOperation, TypeError, KeyError, ValueError, AttributeError) as exc:
        if isinstance(exc, DuLieuDonHangKhongHopLe):
            raise
        raise DuLieuDonHangKhongHopLe("Dữ liệu đơn hàng không hợp lệ.") from exc


@transaction.atomic
def cap_nhat_giao_hang(don, *, trang_thai, don_vi_van_chuyen=None, ma_van_don=None, ly_do_that_bai=None):
    """Cập nhật vận chuyển và đồng bộ trạng thái tổng của đơn hàng."""
    don = DonHang.objects.select_for_update().get(pk=don.pk)
    previous_status = don.trang_thai_don
    allowed = dict(GiaoHang.TRANG_THAI_CHOICES)
    if trang_thai not in allowed:
        raise DuLieuDonHangKhongHopLe("Trạng thái giao hàng không hợp lệ.")
    transitions = {
        "cho_lay_hang": {"cho_lay_hang"},
        "dang_giao": {"cho_lay_hang", "cho_giao_hang"},
        "da_giao": {"cho_giao_hang"},
        "giao_that_bai": {"cho_lay_hang", "cho_giao_hang"},
        "hoan_hang": {"cho_giao_hang", "cho_xac_nhan_nhan", "da_giao", "tra_hang"},
    }
    if trang_thai == "cho_xac_nhan" or don.trang_thai_don not in transitions[trang_thai]:
        raise DuLieuDonHangKhongHopLe("Không thể chuyển đơn sang trạng thái giao hàng này.")
    giao, _ = GiaoHang.objects.select_for_update().get_or_create(
        don_hang=don, defaults={"ma_giao_hang": _ma("GH")}
    )
    giao.trang_thai = trang_thai
    if don_vi_van_chuyen is not None:
        giao.don_vi_van_chuyen = str(don_vi_van_chuyen).strip()
    if ma_van_don is not None:
        giao.ma_van_don = str(ma_van_don).strip()
    if ly_do_that_bai is not None:
        giao.ly_do_that_bai = str(ly_do_that_bai).strip()
    if trang_thai == "dang_giao" and not giao.ngay_ban_giao:
        giao.ngay_ban_giao = timezone.now()
    if trang_thai == "da_giao":
        giao.ngay_giao_thanh_cong = timezone.now()
    giao.save()

    status_map = {
        "cho_xac_nhan": "cho_xac_nhan",
        "cho_lay_hang": "cho_lay_hang",
        "dang_giao": "cho_giao_hang",
        # Nhà vận chuyển đã giao; trạng thái đơn tổng tiếp tục là chờ giao
        # cho tới khi khách xác nhận hoặc 24 giờ hết hạn.
        "da_giao": "cho_giao_hang",
        "giao_that_bai": "da_huy",
        "hoan_hang": "tra_hang",
    }
    don.trang_thai_don = status_map[trang_thai]
    don.save(update_fields=["trang_thai_don"])
    _phat_tin_trang_thai(don, previous_status)
    item_status = {
        "cho_xac_nhan": "cho_lay_hang",
        "cho_lay_hang": "cho_lay_hang",
        "dang_giao": "cho_giao_hang",
        "da_giao": "da_giao",
        "giao_that_bai": "giao_khong_thanh_cong",
        "hoan_hang": "da_huy",
    }[trang_thai]
    item_updates = {"trang_thai_giao": item_status}
    if ly_do_that_bai is not None:
        item_updates["ly_do_giao_ktc"] = str(ly_do_that_bai).strip()
    ChiTietDonHang.objects.filter(ma_don_hang=don).update(**item_updates)
    return giao


def chot_don_cho_xac_nhan_qua_han(ma_don_hang=None):
    """Hoàn tất đơn nếu khách không yêu cầu trả trong 24 giờ sau giao."""
    cutoff = timezone.now() - timedelta(days=1)
    candidates = DonHang.objects.filter(
        trang_thai_don__in=["cho_giao_hang", "cho_xac_nhan_nhan"],
        giao_hang__trang_thai="da_giao",
        giao_hang__ngay_giao_thanh_cong__lte=cutoff,
    )
    if ma_don_hang is not None:
        candidates = candidates.filter(pk=ma_don_hang)
    order_ids = list(candidates.values_list("pk", flat=True))
    updated = 0
    for order_id in order_ids:
        with transaction.atomic():
            don = DonHang.objects.select_for_update().get(pk=order_id)
            if don.trang_thai_don not in {"cho_giao_hang", "cho_xac_nhan_nhan"}:
                continue
            try:
                giao = don.giao_hang
            except GiaoHang.DoesNotExist:
                continue
            if (giao.trang_thai != "da_giao" or not giao.ngay_giao_thanh_cong
                    or giao.ngay_giao_thanh_cong > cutoff):
                continue
            previous_status = don.trang_thai_don
            don.trang_thai_don = "da_giao"
            don.save(update_fields=["trang_thai_don"])
            _phat_tin_trang_thai(don, previous_status)
            updated += 1
    # Repair orders finalized by the previous flow before the 24-hour window.
    reopened = DonHang.objects.filter(
        trang_thai_don="da_giao",
        khach_da_xac_nhan_nhan=False,
        giao_hang__trang_thai="da_giao",
        giao_hang__ngay_giao_thanh_cong__gt=cutoff,
    ).exclude(yeu_cau_tra_hang__isnull=False)
    if ma_don_hang is not None:
        reopened = reopened.filter(pk=ma_don_hang)
    for order_id in reopened.values_list("pk", flat=True).iterator():
        with transaction.atomic():
            don = DonHang.objects.select_for_update().get(pk=order_id)
            if don.trang_thai_don != "da_giao" or don.khach_da_xac_nhan_nhan:
                continue
            if YeuCauTraHang.objects.filter(ma_don_hang=don).exists():
                continue
            try:
                giao = don.giao_hang
            except GiaoHang.DoesNotExist:
                continue
            if (giao.trang_thai != "da_giao" or not giao.ngay_giao_thanh_cong
                    or giao.ngay_giao_thanh_cong <= cutoff):
                continue
            previous_status = don.trang_thai_don
            don.trang_thai_don = "cho_giao_hang"
            don.save(update_fields=["trang_thai_don"])
            _phat_tin_trang_thai(don, previous_status)
    return updated
