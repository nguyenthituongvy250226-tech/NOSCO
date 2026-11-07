from django.core.management.base import BaseCommand

from DONHANG.services import het_han_don_chua_thanh_toan


class Command(BaseCommand):
    help = "Cancel prepaid orders that remain unpaid for more than 24 hours."

    def handle(self, *args, **options):
        count = het_han_don_chua_thanh_toan()
        self.stdout.write(self.style.SUCCESS(f"Canceled {count} expired order(s)."))
