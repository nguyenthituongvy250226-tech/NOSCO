
from django import forms
from django.contrib import admin, messages

from .models import (
    DonHang,
    ChiTietDonHang,
    YeuCauTraHang,
    ChiTietYeuCauTraHang,
    BangChungYeuCauTraHang,
)

from .services import (
    DuLieuDonHangKhongHopLe,
    xu_ly_don_hang,
    cap_nhat_giao_hang,
    xu_ly_yeu_cau_tra_hang,
)


# =========================================================
# FORM ĐIỀU CHỈNH TRẠNG THÁI ĐƠN HÀNG
# =========================================================

class DonHangAdminForm(forms.ModelForm):

    class Meta:
        model = DonHang
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "trang_thai_don" not in self.fields:
            return

        trang_thai_hien_tai = getattr(
            self.instance,
            "trang_thai_don",
            None,
        )

        cac_trang_thai_duoc_chuyen = {
            "cho_xac_nhan": [
                ("cho_lay_hang", "Chờ lấy hàng"),
                ("da_huy", "Đã hủy"),
            ],
            "cho_lay_hang": [
                ("cho_giao_hang", "Chờ giao hàng"),
            ],
            "cho_giao_hang": [
                ("da_giao", "Đã giao"),
                ("da_huy", "Đã hủy"),
            ],
        }

        nhan_trang_thai = dict(DonHang.TRANG_THAI_CHOICES)

        choices = []

        if trang_thai_hien_tai:
            choices.append((
                trang_thai_hien_tai,
                nhan_trang_thai.get(
                    trang_thai_hien_tai,
                    trang_thai_hien_tai,
                ),
            ))

        choices.extend(
            cac_trang_thai_duoc_chuyen.get(
                trang_thai_hien_tai,
                [],
            )
        )

        self.fields["trang_thai_don"].choices = choices


# =========================================================
# BỘ LỌC TRẠNG THÁI
# =========================================================

class TrangThaiDonHangFilter(admin.SimpleListFilter):
    title = "Trạng thái đơn hàng"
    parameter_name = "trang_thai_don"

    def lookups(self, request, model_admin):
        return DonHang.TRANG_THAI_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                trang_thai_don=self.value()
            )
        return queryset


class TrangThaiTraHangFilter(admin.SimpleListFilter):
    title = "Trạng thái trả hàng"
    parameter_name = "trang_thai_tra"

    def lookups(self, request, model_admin):
        return YeuCauTraHang.TRANG_THAI_TRA_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                trang_thai_tra=self.value()
            )
        return queryset


# =========================================================
# INLINE CHI TIẾT ĐƠN HÀNG
# =========================================================

class ChiTietDonHangInline(admin.TabularInline):
    model = ChiTietDonHang
    extra = 0
    can_delete = False

    fields = (
        "ma_chi_tiet_dh",
        "ma_bien_the",
        "so_luong",
        "don_gia",
        "thanh_tien",
    )

    readonly_fields = fields


# =========================================================
# INLINE CHI TIẾT YÊU CẦU TRẢ HÀNG
# =========================================================

class ChiTietYeuCauTraHangInline(admin.TabularInline):
    model = ChiTietYeuCauTraHang
    extra = 0
    can_delete = False

    fields = (
        "chi_tiet_don_hang",
        "so_luong",
    )

    readonly_fields = fields


# =========================================================
# INLINE MINH CHỨNG TRẢ HÀNG
# =========================================================

class BangChungYeuCauTraHangInline(admin.TabularInline):
    model = BangChungYeuCauTraHang
    extra = 0
    can_delete = False

    fields = (
        "ten_tep",
        "tep",
        "loai_tep",
        "ngay_tai_len",
    )

    readonly_fields = fields


# =========================================================
# THÔNG BÁO KẾT QUẢ ACTION
# =========================================================

def thong_bao_ket_qua(
    model_admin,
    request,
    thanh_cong,
    that_bai,
    ten_thao_tac,
):
    if thanh_cong:
        model_admin.message_user(
            request,
            f"{ten_thao_tac} thành công cho {thanh_cong} mục.",
            level=messages.SUCCESS,
        )

    if that_bai:
        model_admin.message_user(
            request,
            "Một số mục chưa xử lý được: " + " | ".join(that_bai),
            level=messages.ERROR,
        )


# =========================================================
# QUẢN LÝ ĐƠN HÀNG
# =========================================================

@admin.register(DonHang)
class DonHangAdmin(admin.ModelAdmin):

    form = DonHangAdminForm

    list_display = (
        "ma_don_hang",
        "ma_khach_hang",
        "ten_nguoi_nhan",
        "sdt_nguoi_nhan",
        "tong_tien",
        "trang_thai_don",
        "don_vi_van_chuyen",
        "ma_van_don",
        "ngay_dat",
    )

    list_editable = (
        "trang_thai_don",
    )

    list_filter = (
        TrangThaiDonHangFilter,
        "ngay_dat",
    )

    search_fields = (
        "ma_don_hang",
        "ma_khach_hang",
        "ten_nguoi_nhan",
        "sdt_nguoi_nhan",
        "ma_van_don",
        "don_vi_van_chuyen",
    )

    readonly_fields = (
        "ngay_dat",
        "khach_da_xac_nhan_nhan",
        "tong_tien_hang",
        "so_tien_giam",
        "tong_tien",
        "cap_nhat_van_chuyen_luc",
    )

    inlines = [
        ChiTietDonHangInline,
    ]

    actions = (
        "xac_nhan_don_hang",
        "xu_ly_don_het_hang",
        "bat_dau_giao_hang",
        "xac_nhan_giao_thanh_cong",
        "xac_nhan_giao_that_bai",
    )

    # -----------------------------------------------------
    # LƯU VÀ ĐIỀU CHỈNH TRẠNG THÁI
    # -----------------------------------------------------

    def save_model(self, request, obj, form, change):

        if not change:
            super().save_model(request, obj, form, change)
            return

        don_cu = DonHang.objects.get(pk=obj.pk)

        trang_thai_cu = don_cu.trang_thai_don
        trang_thai_moi = obj.trang_thai_don

        if trang_thai_cu == trang_thai_moi:
            super().save_model(request, obj, form, change)
            return

        # Lưu các thông tin khác trước, giữ trạng thái cũ.
        obj.trang_thai_don = trang_thai_cu
        super().save_model(request, obj, form, change)

        try:

            # Chờ xác nhận -> Chờ lấy hàng
            if (
                trang_thai_cu == "cho_xac_nhan"
                and trang_thai_moi == "cho_lay_hang"
            ):
                xu_ly_don_hang(
                    obj,
                    hanh_dong="xac_nhan",
                )

            # Chờ xác nhận -> Đã hủy
            elif (
                trang_thai_cu == "cho_xac_nhan"
                and trang_thai_moi == "da_huy"
            ):
                xu_ly_don_hang(
                    obj,
                    hanh_dong="het_hang",
                )

            # Chờ lấy hàng -> Chờ giao hàng
            elif (
                trang_thai_cu == "cho_lay_hang"
                and trang_thai_moi == "cho_giao_hang"
            ):
                cap_nhat_giao_hang(
                    obj,
                    trang_thai="cho_giao_hang",
                    don_vi_van_chuyen=(
                        obj.don_vi_van_chuyen or "NOSCO Express"
                    ),
                    ma_van_don=obj.ma_van_don,
                )

            # Chờ giao hàng -> Đã giao
            elif (
                trang_thai_cu == "cho_giao_hang"
                and trang_thai_moi == "da_giao"
            ):
                cap_nhat_giao_hang(
                    obj,
                    trang_thai="da_giao",
                    don_vi_van_chuyen=(
                        obj.don_vi_van_chuyen or "NOSCO Express"
                    ),
                    ma_van_don=obj.ma_van_don,
                )

            # Chờ giao hàng -> Đã hủy do giao thất bại
            elif (
                trang_thai_cu == "cho_giao_hang"
                and trang_thai_moi == "da_huy"
            ):
                cap_nhat_giao_hang(
                    obj,
                    trang_thai="giao_that_bai",
                    don_vi_van_chuyen=(
                        obj.don_vi_van_chuyen or "NOSCO Express"
                    ),
                    ma_van_don=obj.ma_van_don,
                    ly_do_that_bai=(
                        obj.ly_do_that_bai
                        or "Giao hàng không thành công."
                    ),
                )

            else:
                raise DuLieuDonHangKhongHopLe(
                    "Không được phép chuyển trạng thái đơn hàng này."
                )

            obj.refresh_from_db()

            self.message_user(
                request,
                f"Đã cập nhật trạng thái đơn {obj.ma_don_hang}.",
                level=messages.SUCCESS,
            )

        except DuLieuDonHangKhongHopLe as exc:
            self.message_user(
                request,
                f"Không thể cập nhật đơn {obj.ma_don_hang}: {exc}",
                level=messages.ERROR,
            )

    # -----------------------------------------------------
    # ACTION: XÁC NHẬN ĐƠN HÀNG
    # -----------------------------------------------------

    @admin.action(description="Xác nhận đơn hàng đã chọn")
    def xac_nhan_don_hang(self, request, queryset):

        thanh_cong = 0
        that_bai = []

        for don in queryset:
            try:
                xu_ly_don_hang(
                    don,
                    hanh_dong="xac_nhan",
                )
                thanh_cong += 1

            except DuLieuDonHangKhongHopLe as exc:
                that_bai.append(
                    f"{don.ma_don_hang}: {exc}"
                )

        thong_bao_ket_qua(
            self,
            request,
            thanh_cong,
            that_bai,
            "Xác nhận đơn hàng",
        )

    # -----------------------------------------------------
    # ACTION: HẾT HÀNG - HỦY ĐƠN
    # -----------------------------------------------------

    @admin.action(description="Đánh dấu hết hàng và hủy đơn")
    def xu_ly_don_het_hang(self, request, queryset):

        thanh_cong = 0
        that_bai = []

        for don in queryset:
            try:
                xu_ly_don_hang(
                    don,
                    hanh_dong="het_hang",
                )
                thanh_cong += 1

            except DuLieuDonHangKhongHopLe as exc:
                that_bai.append(
                    f"{don.ma_don_hang}: {exc}"
                )

        thong_bao_ket_qua(
            self,
            request,
            thanh_cong,
            that_bai,
            "Xử lý hết hàng và hủy đơn",
        )

    # -----------------------------------------------------
    # HÀM DÙNG CHUNG CẬP NHẬT TRẠNG THÁI
    # -----------------------------------------------------

    def _cap_nhat_trang_thai_giao(
        self,
        request,
        queryset,
        trang_thai,
        ten_thao_tac,
    ):

        thanh_cong = 0
        that_bai = []

        for don in queryset:
            try:
                cap_nhat_giao_hang(
                    don,
                    trang_thai=trang_thai,
                    don_vi_van_chuyen=(
                        don.don_vi_van_chuyen or "NOSCO Express"
                    ),
                    ma_van_don=don.ma_van_don,
                    ly_do_that_bai=(
                        don.ly_do_that_bai
                        or "Giao hàng không thành công."
                    ),
                )
                thanh_cong += 1

            except DuLieuDonHangKhongHopLe as exc:
                that_bai.append(
                    f"{don.ma_don_hang}: {exc}"
                )

        thong_bao_ket_qua(
            self,
            request,
            thanh_cong,
            that_bai,
            ten_thao_tac,
        )

    # -----------------------------------------------------
    # ACTION: CHỜ LẤY HÀNG -> CHỜ GIAO HÀNG
    # -----------------------------------------------------

    @admin.action(
        description="Xác nhận đã lấy hàng - chuyển sang Chờ giao hàng"
    )
    def bat_dau_giao_hang(self, request, queryset):

        self._cap_nhat_trang_thai_giao(
            request,
            queryset,
            "cho_giao_hang",
            "Cập nhật đơn sang Chờ giao hàng",
        )

    # -----------------------------------------------------
    # ACTION: CHỜ GIAO HÀNG -> ĐÃ GIAO
    # -----------------------------------------------------

    @admin.action(
        description="Xác nhận giao hàng thành công"
    )
    def xac_nhan_giao_thanh_cong(self, request, queryset):

        self._cap_nhat_trang_thai_giao(
            request,
            queryset,
            "da_giao",
            "Xác nhận giao hàng thành công",
        )

    # -----------------------------------------------------
    # ACTION: CHỜ GIAO HÀNG -> ĐÃ HỦY
    # -----------------------------------------------------

    @admin.action(
        description="Xác nhận giao hàng thất bại"
    )
    def xac_nhan_giao_that_bai(self, request, queryset):

        self._cap_nhat_trang_thai_giao(
            request,
            queryset,
            "giao_that_bai",
            "Xác nhận giao hàng thất bại",
        )


# =========================================================
# QUẢN LÝ CHI TIẾT ĐƠN HÀNG
# =========================================================

@admin.register(ChiTietDonHang)
class ChiTietDonHangAdmin(admin.ModelAdmin):

    list_display = (
        "ma_chi_tiet_dh",
        "ma_don_hang",
        "ma_bien_the",
        "so_luong",
        "don_gia",
        "thanh_tien",
    )

    search_fields = (
        "ma_chi_tiet_dh",
        "ma_don_hang__ma_don_hang",
        "ma_bien_the",
    )


# =========================================================
# QUẢN LÝ YÊU CẦU TRẢ HÀNG
# =========================================================

@admin.register(YeuCauTraHang)
class YeuCauTraHangAdmin(admin.ModelAdmin):

    list_display = (
        "ma_yeu_cau_tra",
        "ma_don_hang",
        "ly_do_tra",
        "phuong_thuc_hoan_tien",
        "trang_thai_tra",
        "ngay_tao",
        "ngay_xu_ly",
    )

    list_filter = (
        TrangThaiTraHangFilter,
        "phuong_thuc_hoan_tien",
        "ngay_tao",
    )

    search_fields = (
        "ma_yeu_cau_tra",
        "ma_don_hang__ma_don_hang",
        "ma_don_hang__ma_khach_hang",
        "ly_do_tra",
    )

    readonly_fields = (
        "ngay_tao",
        "ngay_xu_ly",
        "trang_thai_tra",
    )

    inlines = [
        ChiTietYeuCauTraHangInline,
        BangChungYeuCauTraHangInline,
    ]

    actions = (
        "duyet_yeu_cau_tra_hang",
        "tu_choi_yeu_cau_tra_hang",
        "hoan_tat_yeu_cau_tra_hang",
    )

    # -----------------------------------------------------
    # ACTION: DUYỆT YÊU CẦU
    # -----------------------------------------------------

    @admin.action(description="Duyệt yêu cầu trả hàng")
    def duyet_yeu_cau_tra_hang(self, request, queryset):

        thanh_cong = 0
        that_bai = []

        for yeu_cau in queryset:
            try:
                xu_ly_yeu_cau_tra_hang(
                    yeu_cau,
                    hanh_dong="da_duyet",
                    ket_qua=(
                        "Yêu cầu trả hàng đã được NOSCO phê duyệt."
                    ),
                    don_vi_van_chuyen_tra=(
                        yeu_cau.don_vi_van_chuyen_tra
                        or "NOSCO Express"
                    ),
                    ma_van_don_tra=yeu_cau.ma_van_don_tra,
                )
                thanh_cong += 1

            except DuLieuDonHangKhongHopLe as exc:
                that_bai.append(
                    f"{yeu_cau.ma_yeu_cau_tra}: {exc}"
                )

        thong_bao_ket_qua(
            self,
            request,
            thanh_cong,
            that_bai,
            "Duyệt yêu cầu trả hàng",
        )

    # -----------------------------------------------------
    # ACTION: TỪ CHỐI YÊU CẦU
    # -----------------------------------------------------

    @admin.action(description="Từ chối yêu cầu trả hàng")
    def tu_choi_yeu_cau_tra_hang(self, request, queryset):

        thanh_cong = 0
        that_bai = []

        for yeu_cau in queryset:
            try:
                xu_ly_yeu_cau_tra_hang(
                    yeu_cau,
                    hanh_dong="tu_choi",
                    ket_qua=(
                        "Yêu cầu trả hàng không được phê duyệt."
                    ),
                )
                thanh_cong += 1

            except DuLieuDonHangKhongHopLe as exc:
                that_bai.append(
                    f"{yeu_cau.ma_yeu_cau_tra}: {exc}"
                )

        thong_bao_ket_qua(
            self,
            request,
            thanh_cong,
            that_bai,
            "Từ chối yêu cầu trả hàng",
        )

    # -----------------------------------------------------
    # ACTION: HOÀN TẤT YÊU CẦU
    # -----------------------------------------------------

    @admin.action(description="Hoàn tất yêu cầu trả hàng")
    def hoan_tat_yeu_cau_tra_hang(self, request, queryset):

        thanh_cong = 0
        that_bai = []

        for yeu_cau in queryset:
            try:
                xu_ly_yeu_cau_tra_hang(
                    yeu_cau,
                    hanh_dong="hoan_tat",
                    ket_qua="Quy trình trả hàng đã hoàn tất.",
                )
                thanh_cong += 1

            except DuLieuDonHangKhongHopLe as exc:
                that_bai.append(
                    f"{yeu_cau.ma_yeu_cau_tra}: {exc}"
                )

        thong_bao_ket_qua(
            self,
            request,
            thanh_cong,
            that_bai,
            "Hoàn tất yêu cầu trả hàng",
        )


# =========================================================
# QUẢN LÝ MINH CHỨNG TRẢ HÀNG
# =========================================================

@admin.register(BangChungYeuCauTraHang)
class BangChungYeuCauTraHangAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "yeu_cau",
        "ten_tep",
        "loai_tep",
        "ngay_tai_len",
    )

    search_fields = (
        "yeu_cau__ma_yeu_cau_tra",
        "ten_tep",
    )

    readonly_fields = (
        "ngay_tai_len",
    )
