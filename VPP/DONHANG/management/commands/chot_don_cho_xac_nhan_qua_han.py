from django.core.management.base import BaseCommand

from DONHANG.services import chot_don_cho_xac_nhan_qua_han


class Command(BaseCommand):
    help = "Finalize delivered orders with no return request after 24 hours."

    def handle(self, *args, **options):
        count = chot_don_cho_xac_nhan_qua_han()
        self.stdout.write(self.style.SUCCESS(f"Finalized {count} expired order(s)."))
