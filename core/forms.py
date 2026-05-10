"""Helpers compartilhados de forms.

`aplicar_tailwind` injeta classes Tailwind nos widgets dos forms via `__init__`,
evitando duplicar attrs em cada field e dispensando JS client-side. Padrão
adotado em pessoas/forms.py (DT-006) e herdável por demandas/forms.py na Fase 3.
"""

from django import forms

_TAILWIND_INPUT = (
    "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-slate-400"
)
_TAILWIND_CHECKBOX = "rounded border-slate-300"

_INPUT_WIDGETS = (
    forms.TextInput,
    forms.EmailInput,
    forms.NumberInput,
    forms.DateInput,
    forms.URLInput,
    forms.Textarea,
    forms.Select,
    forms.PasswordInput,
)


def aplicar_tailwind(form):
    """Injeta classes Tailwind nos widgets do form. Idempotente."""
    for field in form.fields.values():
        w = field.widget
        if isinstance(w, forms.CheckboxInput):
            existente = w.attrs.get("class", "")
            if _TAILWIND_CHECKBOX not in existente:
                w.attrs["class"] = (existente + " " + _TAILWIND_CHECKBOX).strip()
        elif isinstance(w, _INPUT_WIDGETS):
            existente = w.attrs.get("class", "")
            if _TAILWIND_INPUT not in existente:
                w.attrs["class"] = (existente + " " + _TAILWIND_INPUT).strip()
