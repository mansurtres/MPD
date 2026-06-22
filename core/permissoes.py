"""Checagens de papel centralizadas — única fonte de verdade dos nomes
dos grupos. Qualquer rename de grupo só toca este arquivo.

ADR 0024 (`nunca checar grupo pelo nome no código de produto`) tem como
única exceção controlada esta camada: as funções abaixo são o único
lugar autorizado a referenciar os literais. O resto do código consome
`eh_admin(user)` e `eh_cg_plus(user)` — não as strings.

Migrations que criam os grupos (`*_grupos_padrao_*.py`) também usam os
nomes literais; é inerente — elas escrevem no banco. Mantidas como
exceção documentada.

Papéis na v1 (ADR 0059): Administrador, Chefe de Gabinete, Assessor.
O papel "Coordenador" foi removido junto com o conceito de coordenação.
"""

GRUPO_ADM = "Administrador"
GRUPO_CG = "Chefe de Gabinete"
GRUPO_AS = "Assessor"


def eh_admin(user):
    """Apenas Administrador (ou superuser). Acesso à auditoria,
    edição/criação de usuários, configurações sensíveis."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=GRUPO_ADM).exists()


def eh_cg_plus(user):
    """Admin ou Chefe de Gabinete (ou superuser). Visibilidade plena de
    restritas, painel /analise, edição de interação alheia."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=[GRUPO_ADM, GRUPO_CG]).exists()
