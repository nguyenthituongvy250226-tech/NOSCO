from django.dispatch import Signal


# Module thanh toán có thể kết nối receiver để bắt đầu quy trình hoàn tiền.
yeu_cau_tra_hang_da_duyet = Signal()
yeu_cau_tra_hang_da_hoan_tat = Signal()

# Module khách hàng/thông báo có thể tra hồ sơ bằng ma_khach_hang.
don_hang_da_tao = Signal()
don_hang_trang_thai_thay_doi = Signal()
yeu_cau_tra_hang_da_tao = Signal()
yeu_cau_tra_hang_da_xu_ly = Signal()
