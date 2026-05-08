"""Cliente ViaCEP. Tolerante a falha — qualquer erro retorna None silenciosamente."""

import re

import requests
from django.conf import settings


def consultar(cep):
    """Consulta CEP no ViaCEP. Retorna dict com dados de endereço ou None.

    Resposta esperada (campos do dict, todos podem vir vazios):
        {"cep", "logradouro", "complemento", "bairro", "cidade", "estado"}

    Não levanta exceção. Em caso de timeout/erro/HTTP/CEP inválido, retorna None.
    """
    digits = re.sub(r"\D", "", cep or "")
    if len(digits) != 8:
        return None

    timeout = getattr(settings, "VIACEP_TIMEOUT", 3)
    try:
        response = requests.get(f"https://viacep.com.br/ws/{digits}/json/", timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None

    if data.get("erro"):
        return None

    return {
        "cep": f"{digits[:5]}-{digits[5:]}",
        "logradouro": data.get("logradouro", ""),
        "complemento": data.get("complemento", ""),
        "bairro": data.get("bairro", ""),
        "cidade": data.get("localidade", ""),
        "estado": data.get("uf", ""),
    }
