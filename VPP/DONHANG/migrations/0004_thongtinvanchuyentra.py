from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("DONHANG", "0003_chitietyeucautrahang")]

    operations = [
        migrations.AddField(
            model_name="yeucautrahang",
            name="don_vi_van_chuyen_tra",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="yeucautrahang",
            name="ma_van_don_tra",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
