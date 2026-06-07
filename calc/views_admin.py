import json
from decimal import Decimal, InvalidOperation

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from .services_import import parse_workbook, apply_import

from .models import BuildingClass, City, CostRate


@staff_member_required
def cost_pivot(request):
    classes = list(BuildingClass.objects.all().order_by("order", "name"))
    cities = list(City.objects.all().order_by("name"))

    rates = CostRate.objects.values_list("city_id", "building_class_id", "price_per_sqm")
    rate_map = {(c, b): p for c, b, p in rates}

    rows = [{
        "city_id": city.pk,
        "city_name": city.name,
        "cells": [
            {"class_id": cls.pk, "value": rate_map.get((city.pk, cls.pk))}
            for cls in classes
        ],
    } for city in cities]

    ctx = {
        "classes": classes,
        "rows": rows,
        "cities_count": len(cities),
        "classes_count": len(classes),
        "save_url": reverse("admin:calc_costrate_pivot_save"),
        "add_city_url": reverse("admin:calc_costrate_pivot_add_city"),
        "page_url": reverse("admin:calc_costrate_pivot"),
    }
    return render(request, "calc/admin_cost_pivot.html", ctx)


@staff_member_required
@require_POST
def cost_pivot_save(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("invalid json")

    changes = payload.get("changes", [])
    saved, deleted, errors = 0, 0, []

    for ch in changes:
        city_id = ch.get("city_id")
        class_id = ch.get("class_id")
        raw = ch.get("value")

        if not city_id or not class_id:
            errors.append({"city_id": city_id, "class_id": class_id, "error": "ids required"})
            continue

        is_empty = raw in (None, "", "0", "0.0", "0.00")
        if is_empty:
            d = CostRate.objects.filter(city_id=city_id, building_class_id=class_id).delete()
            if d[0]:
                deleted += 1
            continue

        try:
            value = Decimal(str(raw).replace(",", ".").replace(" ", ""))
        except (InvalidOperation, ValueError):
            errors.append({"city_id": city_id, "class_id": class_id, "error": "bad number"})
            continue

        if value <= 0:
            CostRate.objects.filter(city_id=city_id, building_class_id=class_id).delete()
            deleted += 1
            continue

        CostRate.objects.update_or_create(
            city_id=city_id, building_class_id=class_id,
            defaults={"price_per_sqm": value},
        )
        saved += 1

    return JsonResponse({"ok": True, "saved": saved, "deleted": deleted, "errors": errors})


@staff_member_required
@require_POST
def cost_pivot_add_city(request):
    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "Введите название города."}, status=400)
    city, created = City.objects.get_or_create(name=name)
    return JsonResponse({"ok": True, "id": city.pk, "name": city.name, "created": created})

@staff_member_required
@require_POST
def cost_pivot_import_preview(request):
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"ok": False, "error": "Файл не получен."}, status=400)

    name = (f.name or "").lower()
    if not name.endswith(".xlsx"):
        return JsonResponse({"ok": False, "error": "Поддерживается только .xlsx"}, status=400)

    parsed = parse_workbook(f.read())
    if "fatal" in parsed:
        return JsonResponse({"ok": False, "error": parsed["fatal"]}, status=400)

    return JsonResponse({"ok": True, "parsed": parsed})


@staff_member_required
@require_POST
def cost_pivot_import_apply(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("invalid json")

    parsed = payload.get("parsed")
    if not parsed:
        return HttpResponseBadRequest("parsed required")

    result = apply_import(
        parsed,
        create_missing_cities=bool(payload.get("create_missing_cities", False)),
        overwrite=bool(payload.get("overwrite", False)),
        clear_zeros=bool(payload.get("clear_zeros", False)),
    )
    return JsonResponse({"ok": True, **result})