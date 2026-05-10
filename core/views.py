from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render


def inicio(request):
    if request.user.is_authenticated:
        return render(request, "core/inicio_autenticado.html")
    return render(request, "core/inicio.html")


@login_required
def configuracoes(request):
    """Hub de configurações administrativas. Cada card aparece conforme a
    permissão do usuário."""
    return render(request, "core/configuracoes.html")


def healthz(request):
    return JsonResponse({"status": "ok"})
