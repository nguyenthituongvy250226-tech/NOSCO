
from django.contrib import admin


class NOSCOAdminSite(admin.AdminSite):
    site_header = 'NOSCO | Hệ thống quản trị'
    site_title = 'NOSCO Admin'
    index_title = 'Quản lý hệ thống'
