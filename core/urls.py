from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("configuracoes/", views.configuracoes, name="configuracoes"),
    path("healthz/", views.healthz, name="healthz"),
    path("auditoria/", views.AuditoriaListView.as_view(), name="auditoria"),
    path("analise/", views.AnaliseView.as_view(), name="analise"),
]
