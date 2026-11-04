from django.db import migrations


def tao_ma_van_don_tra(apps, schema_editor):
    YeuCauTraHang = apps.get_model("DONHANG", "YeuCauTraHang")
    for yeu_cau in YeuCauTraHang.objects.only("ma_yeu_cau_tra").iterator():
        yeu_cau.ma_van_don_tra = f"MVD{yeu_cau.ma_yeu_cau_tra[2:]}"
        yeu_cau.save(update_fields=["ma_van_don_tra"])


class Migration(migrations.Migration):
    dependencies = [("DONHANG", "0009_chi_tiet_yeu_cau_tra_hang")]

    operations = [migrations.RunPython(tao_ma_van_don_tra, migrations.RunPython.noop)]
