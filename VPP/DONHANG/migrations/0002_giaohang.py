from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("DONHANG", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="GiaoHang",
            fields=[
                ("ma_giao_hang", models.CharField(max_length=32, primary_key=True, serialize=False)),
                ("don_vi_van_chuyen", models.CharField(blank=True, max_length=100)),
                ("ma_van_don", models.CharField(blank=True, db_index=True, max_length=100)),
                ("phi_van_chuyen", models.DecimalField(decimal_places=0, default=0, max_digits=15)),
                ("trang_thai", models.CharField(choices=[("cho_xac_nhan", "Chờ xác nhận đơn"), ("cho_lay_hang", "Chờ lấy hàng"), ("dang_giao", "Đang giao"), ("da_giao", "Đã giao"), ("giao_that_bai", "Giao thất bại"), ("hoan_hang", "Hoàn hàng")], default="cho_xac_nhan", max_length=30)),
                ("ly_do_that_bai", models.CharField(blank=True, max_length=255)),
                ("ngay_ban_giao", models.DateTimeField(blank=True, null=True)),
                ("ngay_giao_thanh_cong", models.DateTimeField(blank=True, null=True)),
                ("cap_nhat_luc", models.DateTimeField(auto_now=True)),
                ("don_hang", models.OneToOneField(db_column="MaDonHang", on_delete=django.db.models.deletion.CASCADE, related_name="giao_hang", to="DONHANG.donhang")),
            ],
            options={"verbose_name": "Thông tin giao hàng", "verbose_name_plural": "Thông tin giao hàng"},
        ),
    ]
