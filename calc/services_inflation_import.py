"""Импорт MonthlyInflation из Excel-файла (колонка A — месяц, колонка B — инфляция)."""
from decimal import Decimal, InvalidOperation
from io import BytesIO
from itertools import chain

from django.db import transaction
from openpyxl import load_workbook

from .models import MonthlyInflation

MAX_FILE_SIZE = 5 * 1024 * 1024

HEADER_MONTH = "месяц"
HEADER_RATE = "инфляция"

MAX_RATE_DIGITS = MonthlyInflation._meta.get_field("rate").max_digits
MAX_RATE_DECIMALS = MonthlyInflation._meta.get_field("rate").decimal_places
MAX_RATE_INT_DIGITS = MAX_RATE_DIGITS - MAX_RATE_DECIMALS


class MonthlyInflationImportError(Exception):
    """Ошибка импорта: номер строки файла + причина. Откат — на вызывающей стороне."""

    def __init__(self, row_number: int, reason: str):
        self.row_number = row_number
        self.reason = reason
        super().__init__(f"Строка {row_number}: {reason}.")


def _norm(s) -> str:
    if s is None:
        return ""
    return str(s).strip().lower().replace("ё", "е")


def _clean_text(raw) -> str:
    return str(raw).replace(" ", "").replace("\xa0", "").strip()


def _is_header(row) -> bool:
    month = _norm(row[0]) if len(row) > 0 else ""
    rate = _norm(row[1]) if len(row) > 1 else ""
    return month == HEADER_MONTH and rate == HEADER_RATE


def _parse_month(raw, row_number: int) -> int:
    if raw is None or _clean_text(raw) == "":
        raise MonthlyInflationImportError(row_number, "не заполнен месяц (колонка A)")

    if isinstance(raw, bool):
        raise MonthlyInflationImportError(row_number, f"месяц должен быть целым числом: {raw!r}")

    try:
        value = Decimal(_clean_text(raw).replace(",", "."))
    except (InvalidOperation, ValueError):
        raise MonthlyInflationImportError(row_number, f"месяц должен быть целым числом: {raw!r}")

    if value != value.to_integral_value():
        raise MonthlyInflationImportError(row_number, f"месяц должен быть целым числом: {raw!r}")

    month = int(value)
    if month < 1:
        raise MonthlyInflationImportError(row_number, f"месяц должен быть ≥ 1, получено {month}")
    return month


def _parse_rate(raw, row_number: int) -> Decimal:
    if raw is None or _clean_text(raw) == "":
        raise MonthlyInflationImportError(row_number, "не заполнена инфляция (колонка B)")

    if isinstance(raw, bool):
        raise MonthlyInflationImportError(row_number, f"инфляция — не число: {raw!r}")

    if isinstance(raw, (int, float, Decimal)):
        value = Decimal(str(raw))
    else:
        try:
            value = Decimal(_clean_text(raw).replace(",", "."))
        except (InvalidOperation, ValueError):
            raise MonthlyInflationImportError(row_number, f"инфляция — не число: {raw!r}")

    if value <= 0:
        raise MonthlyInflationImportError(row_number, f"инфляция должна быть > 0, получено {raw!r}")

    _, digits, exponent = value.as_tuple()
    decimals = max(0, -exponent)
    int_digits = max(len(digits) - decimals, 0)
    if decimals > MAX_RATE_DECIMALS or int_digits > MAX_RATE_INT_DIGITS:
        raise MonthlyInflationImportError(
            row_number,
            f"инфляция не помещается в формат поля (до {MAX_RATE_INT_DIGITS} цифр "
            f"перед запятой, до {MAX_RATE_DECIMALS} после): {raw!r}",
        )
    return value


def parse_workbook(file_bytes: bytes) -> list[tuple[int, int, Decimal]]:
    """
    Первый лист файла → список (номер строки, месяц, ставка).
    Шапка («Месяц», «Инфляция») опциональна. Любая битая строка → MonthlyInflationImportError.
    """
    try:
        wb = load_workbook(BytesIO(file_bytes), data_only=True, read_only=True)
    except Exception as e:
        raise MonthlyInflationImportError(1, f"не удалось прочитать файл: {e}")

    try:
        ws = wb.active
        if ws is None:
            raise MonthlyInflationImportError(1, "в файле нет листов")

        rows_iter = ws.iter_rows(values_only=True)
        try:
            first_row = next(rows_iter)
        except StopIteration:
            raise MonthlyInflationImportError(1, "файл пуст")

        parsed: list[tuple[int, int, Decimal]] = []
        seen: dict[int, int] = {}

        if _is_header(first_row):
            data_rows = rows_iter
        elif first_row and any(v is not None and str(v).strip() != "" for v in first_row):
            data_rows = chain([first_row], rows_iter)
        else:
            data_rows = rows_iter

        for row_number, row in enumerate(data_rows, start=2):
            if not row or all(v is None or str(v).strip() == "" for v in row):
                continue
            if _is_header(row):
                continue

            month = _parse_month(row[0] if len(row) > 0 else None, row_number)
            rate = _parse_rate(row[1] if len(row) > 1 else None, row_number)

            if month in seen:
                raise MonthlyInflationImportError(
                    row_number, f"месяц {month} уже встречался в строке {seen[month]}"
                )
            seen[month] = row_number
            parsed.append((row_number, month, rate))
    finally:
        wb.close()

    if not parsed:
        raise MonthlyInflationImportError(2, "в файле нет строк с данными")

    return parsed


def apply_import(parsed: list[tuple[int, int, Decimal]]) -> tuple[int, int]:
    """
    Upsert по месяцу внутри одной транзакции. Возвращает (создано, обновлено).
    Ошибка любой строки → исключение → полный откат.
    """
    created = 0
    updated = 0
    with transaction.atomic():
        for _row_number, month, rate in parsed:
            _obj, was_created = MonthlyInflation.objects.update_or_create(
                month=month, defaults={"rate": rate}
            )
            if was_created:
                created += 1
            else:
                updated += 1
    return created, updated


def import_from_bytes(file_bytes: bytes) -> tuple[int, int]:
    """Парсинг + применение. Возвращает (создано, обновлено)."""
    return apply_import(parse_workbook(file_bytes))
