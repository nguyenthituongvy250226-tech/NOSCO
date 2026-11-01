from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("DONHANG", "0006_cho_xac_nhan_da_nhan")]

    operations = [
        migrations.AlterField(
            model_name="donhang",
            name="trang_thai_don",
            field=models.CharField(
                choices=[
                    ("cho_xac_nhan", "Chờ xác nhận"),
                    ("cho_lay_hang", "Chờ lấy hàng"),
                    ("cho_giao_hang", "Chờ giao hàng"),
                    ("cho_xac_nhan_nhan", "Giao thành công — chờ quyết định trả hàng"),
                    ("da_giao", "Đã giao"),
                    ("tra_hang", "Trả hàng"),
                    ("da_huy", "Đã hủy"),
                ],
                default="cho_xac_nhan",
                max_length=50,
                verbose_name="Trạng thái đơn hàng",
            ),
        ),
    ]
