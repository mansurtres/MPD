from django.http import JsonResponse
from django.shortcuts import render


def inicio(request):
    if request.user.is_authenticated:
        return render(request, "core/inicio_autenticado.html")
    return render(request, "core/inicio.html")


def healthz(request):
    return JsonResponse({"status": "ok"})
