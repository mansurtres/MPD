from django.http import JsonResponse
from django.shortcuts import render


def inicio(request):
    return render(request, "core/inicio.html")


def healthz(request):
    return JsonResponse({"status": "ok"})
