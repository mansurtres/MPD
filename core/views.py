from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render


def inicio(request):
    contexto = {
        "NOME_DO_MANDATO": settings.NOME_DO_MANDATO,
        "NOME_CURTO_DO_MANDATO": settings.NOME_CURTO_DO_MANDATO,
        "SIGLA_MANDATO": settings.SIGLA_MANDATO,
    }
    return render(request, "core/inicio.html", contexto)


def healthz(request):
    return JsonResponse({"status": "ok"})
