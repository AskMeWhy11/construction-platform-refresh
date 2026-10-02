"""Служебные view админки для «Инфляция (помесячно)»."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import MonthlyInflation
from .services_inflation_import import (
    MAX_FILE_SIZE,
    MonthlyInflationImportError,
    import_from_bytes,
)

FILE_ERROR_SUFFIX = "Поддерживается только файл .xlsx."


def _changelist_url() -> str:
    return reverse("admin:calc_monthlyinflation_changelist")


def monthlyinflation_import(request):
    """
    Форма загрузки Excel и применение импорта.
    Доступ: пользователи с change-правом на модель (admin_site.admin_view + проверка).
    """
    if not request.user.has_perm("calc.change_monthlyinflation"):
        messages.error(request, "Недостаточно прав для импорта помесячной инфляции.")
        return redirect(_changelist_url())

    context = {
        "title": "Импорт Excel",
        "opts": MonthlyInflation._meta,
        "has_view_permission": True,
        "changelist_url": _changelist_url(),
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
    }

    if request.method != "POST":
        return render(request, "calc/admin_monthlyinflation_import.html", context)

    upload = request.FILES.get("file")
    if not upload:
        messages.error(request, "Файл не выбран. " + FILE_ERROR_SUFFIX)
        return render(request, "calc/admin_monthlyinflation_import.html", context)

    if not (upload.name or "").lower().endswith(".xlsx"):
        messages.error(request, "Требуется файл .xlsx. " + FILE_ERROR_SUFFIX)
        return render(request, "calc/admin_monthlyinflation_import.html", context)

    if upload.size > MAX_FILE_SIZE:
        messages.error(
            request,
            f"Файл больше {context['max_file_size_mb']} МБ ({upload.size} байт).",
        )
        return render(request, "calc/admin_monthlyinflation_import.html", context)

    data = upload.read()
    try:
        created, updated = import_from_bytes(data)
    except MonthlyInflationImportError as e:
        messages.error(request, f"Импорт отменён (изменения не применены). Строка {e.row_number}: {e.reason}.")
        return render(request, "calc/admin_monthlyinflation_import.html", context)

    messages.success(request, f"Создано {created}, обновлено {updated}.")
    return redirect(_changelist_url())
