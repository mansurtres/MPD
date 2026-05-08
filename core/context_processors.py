from django.conf import settings


def mandato(request):
    return {
        "NOME_DO_MANDATO": settings.NOME_DO_MANDATO,
        "NOME_CURTO_DO_MANDATO": settings.NOME_CURTO_DO_MANDATO,
        "SIGLA_MANDATO": settings.SIGLA_MANDATO,
    }
