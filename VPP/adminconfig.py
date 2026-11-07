from django.contrib.admin.apps import AdminConfig

class NOSCOAdminConfig(AdminConfig):
    default_site = 'admin.NOSCOAdminSite'