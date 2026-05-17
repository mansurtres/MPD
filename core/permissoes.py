"""Checagens de papel centralizadas — única fonte de verdade dos nomes
dos grupos. Qualquer rename de grupo só toca este arquivo.

ADR 0024 (`nunca checar grupo pelo nome no código de produto`) tem como
única exceção controlada esta camada: as funções abaixo são o único
lugar autorizado a referenciar os literais. O resto do código consome
`eh_cg_plus(user)` e `eh_co_plus(user)` — não as strings.

Migrations que criam os grupos (`*_grupos_padrao_*.py`) também usam os
nomes literais; é inerente — elas escrevem no banco. Mantidas como
exceção documentada.
"""

GRUPO_ADM = "Administrador"
GRUPO_CG = "Chefe de Gabinete"
GRUPO_CO = "Coordenador"
GRUPO_AS = "Assessor"


def eh_cg_plus(user):
    """Admin ou Chefe de Gabinete (ou superuser). Visibilidade plena de
    restritas, acesso à auditoria, edição de interação alheia."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=[GRUPO_ADM, GRUPO_CG]).exists()


def eh_co_plus(user):
    """Admin, CG ou Coordenador (ou superuser). Exportação CSV, painel
    /analise, remoção de anexos alheios."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=[GRUPO_ADM, GRUPO_CG, GRUPO_CO]).exists()
