
from django.urls import path
from . import views

app_name = "DONHANG"

urlpatterns = [
    # Danh sách đơn hàng
    path("", views.danh_sach_don_hang, name="danh_sach"),
    path(
        "trang-thai/<slug:trang_thai>/",
        views.danh_sach_don_hang,
        name="trang_thai",
    ),

    # Chức năng kiểm thử
    path(
        "tao-don-mau/",
        views.tao_don_hang_mau,
        name="tao_don_hang_mau",
    ),

    # Hướng dẫn và minh chứng trả hàng
    path(
        "tra-hang/huong-dan/",
        views.huong_dan_tra_hang_chung,
        name="huong_dan_tra_hang_chung",
    ),
    path(
        "tra-hang/minh-chung/<int:evidence_id>/",
        views.xem_minh_chung_tra_hang,
        name="minh_chung_tra_hang",
    ),

    # Chức năng khách hàng
    path(
        "<str:ma_don_hang>/sua/",
        views.sua_don_hang,
        name="sua",
    ),
    path(
        "<str:ma_don_hang>/huy/",
        views.huy_don_hang,
        name="huy",
    ),
    path(
        "<str:ma_don_hang>/xac-nhan-da-nhan/",
        views.xac_nhan_da_nhan,
        name="xac_nhan_da_nhan",
    ),
    path(
        "<str:ma_don_hang>/tra-hang/theo-doi/",
        views.theo_doi_yeu_cau_tra,
        name="theo_doi_yeu_cau_tra",
    ),
    path(
        "<str:ma_don_hang>/tra-hang/huy-yeu-cau/",
        views.huy_yeu_cau_tra_hang,
        name="huy_yeu_cau_tra_hang",
    ),
    path(
        "<str:ma_don_hang>/tra-hang/",
        views.yeu_cau_tra_hang,
        name="yeu_cau_tra_hang",
    ),
    path(
        "<str:ma_don_hang>/chon-dia-chi/",
        views.chon_dia_chi,
        name="chon_dia_chi",
    ),
    path(
        "<str:ma_don_hang>/xac-nhan-dia-chi/",
        views.xac_nhan_dia_chi,
        name="xac_nhan_dia_chi",
    ),
path(
    "<str:ma_don_hang>/danh-gia/<str:ma_bien_the>/",
    views.gui_danh_gia_san_pham,
    name="gui_danh_gia_san_pham",
),
    # Chi tiết đơn hàng - đặt cuối để tránh trùng đường dẫn
    path(
        "<str:ma_don_hang>/",
        views.chi_tiet_don_hang,
        name="chi_tiet",
    ),

]
