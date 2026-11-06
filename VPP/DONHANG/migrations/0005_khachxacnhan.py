from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("DONHANG", "0004_thongtinvanchuyentra")]

    operations = [
        migrations.AddField(
            model_name="donhang",
            name="khach_da_xac_nhan_nhan",
            field=models.BooleanField(default=False),
        ),
    ]
