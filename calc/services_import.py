"""Импорт CostRate из Excel-файла (pivot: строки=города, колонки=классы)."""
from decimal import Decimal, InvalidOperation
from io import BytesIO

from openpyxl import load_workbook

from .models import BuildingClass, City


def _norm(s) -> str:
    if s is None:
        return ""
    return str(s).strip().lower().replace("ё", "е")


def _to_decimal(raw):
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float, Decimal)):
        d = Decimal(str(raw))
        return d if d > 0 else None
    s = str(raw).replace(",", ".").replace(" ", "").replace("\xa0", "").strip()
    if not s:
        return None
    try:
        d = Decimal(s)
        return d if d > 0 else None
    except (InvalidOperation, ValueError):
        raise ValueError(f"Не число: {raw!r}")


def _format_value(d: Decimal) -> str:
    """Число в строку без потери значащих нулей в целой части.

    format(d, "f") даёт "125200" или "125200.0" — обрезаем нули только
    в дробной части, иначе 125200 превратилось бы в "1252".
    """
    text = format(d, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if not text:
        text = "0"
    if "." not in text:
        text += ".00"
    return text


def parse_workbook(file_bytes: bytes) -> dict:
    """
    Возвращает:
    {
        "headers": [{"name": str, "class_id": int|None}, ...],
        "rows": [
            {
                "city_name": str,
                "city_id": int|None,
                "cells": [{"class_id": int|None, "value": str|None, "error": str|None}, ...]
            }, ...
        ],
        "unknown_cities": [str, ...],
        "unknown_classes": [str, ...],
        "errors": [str, ...],
        "summary": {"rows": int, "matched_cells": int, "unknown_cells": int, "error_cells": int}
    }
    """
    try:
        wb = load_workbook(BytesIO(file_bytes), data_only=True, read_only=True)
    except Exception as e:
        return {"fatal": f"Не удалось прочитать файл: {e}"}

    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)

    try:
        header_row = next(rows_iter)
    except StopIteration:
        return {"fatal": "Файл пуст."}

    if not header_row or len(header_row) < 2:
        return {"fatal": "В заголовке должна быть хотя бы 1 колонка с классом."}

    # Карта классов и городов (один запрос)
    classes_by_norm = {_norm(c.name): c for c in BuildingClass.objects.all()}
    cities_by_norm = {_norm(c.name): c for c in City.objects.all()}

    headers = []
    unknown_classes = []
    seen_unknown_classes = set()
    for h in header_row[1:]:
        name = (str(h).strip() if h is not None else "")
        cls = classes_by_norm.get(_norm(name)) if name else None
        if name and not cls and _norm(name) not in seen_unknown_classes:
            unknown_classes.append(name)
            seen_unknown_classes.add(_norm(name))
        headers.append({
            "name": name,
            "class_id": cls.pk if cls else None,
        })

    rows = []
    unknown_cities = []
    seen_unknown_cities = set()
    matched = 0
    unknown_cells = 0
    error_cells = 0

    for r_idx, row in enumerate(rows_iter, start=2):
        if not row or all(v is None or str(v).strip() == "" for v in row):
            continue

        city_raw = row[0]
        city_name = str(city_raw).strip() if city_raw is not None else ""
        if not city_name:
            continue

        city = cities_by_norm.get(_norm(city_name))
        if not city and _norm(city_name) not in seen_unknown_cities:
            unknown_cities.append(city_name)
            seen_unknown_cities.add(_norm(city_name))

        cells = []
        for col_idx, raw in enumerate(row[1:len(headers) + 1]):
            header = headers[col_idx] if col_idx < len(headers) else None
            if header is None:
                continue

            value_str = None
            err = None
            try:
                d = _to_decimal(raw)
                if d is not None:
                    value_str = _format_value(d)
            except ValueError as e:
                err = str(e)
                error_cells += 1

            if header["class_id"] is None and value_str is not None:
                unknown_cells += 1
            elif value_str is not None and city is not None:
                matched += 1
            elif value_str is not None and city is None:
                unknown_cells += 1

            cells.append({
                "class_id": header["class_id"],
                "value": value_str,
                "error": err,
            })

        rows.append({
            "row_idx": r_idx,
            "city_name": city_name,
            "city_id": city.pk if city else None,
            "cells": cells,
        })

    return {
        "headers": headers,
        "rows": rows,
        "unknown_cities": unknown_cities,
        "unknown_classes": unknown_classes,
        "errors": [],
        "summary": {
            "rows": len(rows),
            "matched_cells": matched,
            "unknown_cells": unknown_cells,
            "error_cells": error_cells,
        },
    }


def apply_import(parsed: dict, *, create_missing_cities: bool,
                 overwrite: bool, clear_zeros: bool) -> dict:
    """
    parsed — то, что вернул parse_workbook (headers, rows).
    Возвращает счётчики: created_cities, saved, skipped, deleted, errors.
    """
    from .models import CostRate  # локально, чтобы избежать циклов

    headers = parsed.get("headers", [])
    rows = parsed.get("rows", [])

    created_cities = 0
    saved = 0
    skipped = 0
    deleted = 0
    errors = []

    # Кэш существующих тарифов: (city_id, class_id) -> CostRate
    existing = {
        (r.city_id, r.building_class_id): r
        for r in CostRate.objects.all()
    }

    for row in rows:
        city_id = row.get("city_id")
        if not city_id:
            if create_missing_cities and row.get("city_name"):
                city, _ = City.objects.get_or_create(name=row["city_name"].strip())
                city_id = city.pk
                created_cities += 1
            else:
                skipped += sum(1 for c in row["cells"] if c.get("value"))
                continue

        for cell in row["cells"]:
            class_id = cell.get("class_id")
            if not class_id:
                skipped += 1
                continue
            if cell.get("error"):
                errors.append(f"{row['city_name']}: {cell['error']}")
                continue

            value = cell.get("value")
            key = (city_id, class_id)

            # Пусто или 0
            if not value or value in ("0", "0.0", "0.00"):
                if clear_zeros and key in existing:
                    existing[key].delete()
                    deleted += 1
                else:
                    skipped += 1
                continue

            try:
                d = Decimal(value)
            except (InvalidOperation, ValueError):
                errors.append(f"{row['city_name']}: bad number {value!r}")
                continue

            if key in existing:
                if overwrite:
                    existing[key].price_per_sqm = d
                    existing[key].save(update_fields=["price_per_sqm"])
                    saved += 1
                else:
                    skipped += 1
            else:
                CostRate.objects.create(city_id=city_id, building_class_id=class_id, price_per_sqm=d)
                saved += 1

    return {
        "created_cities": created_cities,
        "saved": saved,
        "skipped": skipped,
        "deleted": deleted,
        "errors": errors,
    }