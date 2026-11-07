from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("DONHANG", "0007_doi_nhan_tra_hang")]

    operations = [
        migrations.AlterField(
            model_name="yeucautrahang",
            name="trang_thai_tra",
            field=models.CharField(
                choices=[
                    ("cho_xu_ly", "Chờ xử lý"),
                    ("da_duyet", "Đã duyệt"),
                    ("hoan_tat", "Hoàn tất"),
                    ("tu_choi", "Từ chối"),
                ],
                default="cho_xu_ly",
                max_length=50,
                verbose_name="Trạng thái trả hàng",
            ),
        ),
    ]
