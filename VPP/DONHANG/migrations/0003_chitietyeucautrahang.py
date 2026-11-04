from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("DONHANG", "0002_giaohang")]

    operations = [
        migrations.CreateModel(
            name="ChiTietYeuCauTraHang",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("so_luong", models.PositiveIntegerField()),
                ("chi_tiet_don_hang", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="yeu_cau_tra", to="DONHANG.chitietdonhang")),
                ("yeu_cau", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="san_pham_tra", to="DONHANG.yeucautrahang")),
            ],
        ),
        migrations.AddConstraint(
            model_name="chitietyeucautrahang",
            constraint=models.UniqueConstraint(fields=("yeu_cau", "chi_tiet_don_hang"), name="uniq_san_pham_trong_yeu_cau_tra"),
        ),
    ]
