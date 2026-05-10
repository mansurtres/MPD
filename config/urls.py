from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls", namespace="accounts")),
    path("", include("pessoas.urls", namespace="pessoas")),
    path("", include("demandas.urls", namespace="demandas")),
    path("", include("core.urls")),
]
