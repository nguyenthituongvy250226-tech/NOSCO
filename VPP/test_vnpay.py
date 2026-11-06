import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VPP.settings')
django.setup()

from decimal import Decimal
from django.test import RequestFactory
from THANHTOAN.vnpay import tao_url_thanh_toan

request = RequestFactory().get(
    '/',
    secure=True,
    HTTP_HOST='rejoice-hug-populate.ngrok-free.dev'
)

url = tao_url_thanh_toan(
    request,
    'TEST006',
    Decimal('10000')
)

print("URL THANH TOAN:")
print(url)