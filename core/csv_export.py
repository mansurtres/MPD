"""CSV export scaffold shared by DemandaCSVExportView, EncaminhamentoCSVExportView,
and PessoaCSVExportView."""

import csv

from django.http import HttpResponse

from core.utils import registrar_export


def exportar_csv(request, *, list_view_cls, modelo, filename, header, row_fn):
    """Shared scaffold for list-driven CSV exports.

    Permission is already checked by the caller before this function is called.

    Args:
        request: current HttpRequest (used to configure the list view and
                 for registrar_export).
        list_view_cls: the ListView subclass whose get_queryset() provides the
                       filtered queryset (instantiated here with request and
                       empty kwargs).
        modelo: human-readable model name passed to registrar_export (e.g.
                "Demanda").
        filename: CSV filename for Content-Disposition (without path).
        header: list of column header strings.
        row_fn: callable(instance) -> list of values for one CSV row.

    Returns:
        HttpResponse with content_type text/csv.
    """
    lista = list_view_cls()
    lista.request = request
    lista.kwargs = {}
    qs = lista.get_queryset()
    total_filtrado = qs.count()
    qs = qs[:10000]

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")  # UTF-8 BOM for Excel BR
    writer = csv.writer(response, delimiter=";")
    writer.writerow(header)
    for obj in qs:
        writer.writerow(row_fn(obj))

    registrar_export(request.user, modelo, dict(request.GET.lists()), total_filtrado)
    return response
