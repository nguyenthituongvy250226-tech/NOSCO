from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("DONHANG", "0008_hoan_tat_yeu_cau_tra_hang"),
    ]

    operations = [
        migrations.AlterField(
            model_name="yeucautrahang",
            name="ma_thanh_toan",
            field=models.CharField(blank=True, default="", max_length=10, verbose_name="Mã thanh toán"),
        ),
        migrations.AddField(
            model_name="yeucautrahang",
            name="mo_ta_van_de",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="yeucautrahang",
            name="ma_van_don_khach",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="yeucautrahang",
            name="phuong_thuc_hoan_tien",
            field=models.CharField(
                choices=[
                    ("tai_khoan_thanh_toan", "Hoàn tiền về tài khoản thanh toán"),
                    ("vi_nosco", "Hoàn tiền vào ví NOSCO"),
                ],
                default="tai_khoan_thanh_toan",
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="BangChungYeuCauTraHang",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tep", models.FileField(upload_to="donhang/tra_hang/minh_chung/")),
                ("ten_tep", models.CharField(max_length=255)),
                ("loai_tep", models.CharField(blank=True, max_length=100)),
                ("ngay_tai_len", models.DateTimeField(auto_now_add=True)),
                ("yeu_cau", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="minh_chung", to="DONHANG.yeucautrahang")),
            ],
            options={"ordering": ["ngay_tai_len"]},
        ),
    ]
