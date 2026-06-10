from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, ROUND_CEILING
from math import ceil

DEFAULT_SQM_PER_RESIDENT = Decimal("30.00")
DEFAULT_DOO_PER_1000 = Decimal("65.00")
DEFAULT_SOSH_PER_1000 = Decimal("135.00")

from .models import (
    BuildingClass,
    BuildingPurpose,
    City,
    ConstructionDuration,
    CostItem,
    CostRate,
    MonthlyInflation,
    ParkingRate,
    Settings,
    SocialNorms,
)


class CalcError(Exception):
    pass


@dataclass
class CalcResult:
    duration_months: int | None
    construction_cost: Decimal
    base_cost: Decimal
    inflation_amount: Decimal
    inflation_rate: Decimal
    clean_coef: Decimal
    total_area: Decimal
    apartments_area: Decimal
    residents: int
    underground_parking: bool
    ground_parking_spaces: int
    ground_parking_cost: Decimal
    doo_seats: int
    doo_cost: Decimal
    sosh_seats: int
    sosh_cost: Decimal
    price_per_sqm: Decimal

    def as_dict(self):
        return asdict(self)


def _interpolate_duration(total_area: Decimal) -> int | None:
    """Линейная интерполяция срока строительства по таблице ConstructionDuration.

    Возвращает срок (мес., целое, округление к ближайшему). Если точек < 2 —
    возвращает None (срок не определён).
    """
    points = list(
        ConstructionDuration.objects.order_by("area").values_list("area", "months")
    )
    if len(points) < 2:
        return None

    area = float(total_area)

    if area <= points[0][0]:
        return int(points[0][1])
    if area >= points[-1][0]:
        return int(points[-1][1])

    for (a1, m1), (a2, m2) in zip(points, points[1:]):
        if a1 <= area <= a2:
            if a2 == a1:
                return int(m1)
            t = (area - a1) / (a2 - a1)
            return int(round(m1 + (m2 - m1) * t))

    return int(points[-1][1])


def _start_month(start_date: date, today: date | None = None) -> int:
    """Точка старта в таблице инфляции.

    Расстояние в месяцах от сегодня до start_date (вверх), затем +1.
    01.01.2025 → 25.05.2025: 4 календ. мес + (день 25>1 → +1) = 5; старт = 6.
    """
    today = today or date.today()
    months = (start_date.year - today.year) * 12 + (start_date.month - today.month)
    if start_date.day > today.day:
        months += 1
    if months < 0:
        months = 0
    return months + 1


def compute_inflation_increase(base_cost: Decimal, duration_months: int, start_date: date):
    """Этапы 1–3 инфляционного удорожания. Возвращает (rows, total)."""
    rows: list[dict] = []
    if not duration_months or duration_months < 1:
        return rows, Decimal("0.00")

    start = _start_month(start_date)

    # Этап 2: месяцев в периоде (мат. округление)
    months_in_period = int(
        (Decimal(duration_months) / Decimal("3")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    if months_in_period < 1:
        months_in_period = 1

    # 3 части по долям, затраты на месяц внутри части
    parts = [Decimal("0.30"), Decimal("0.40"), Decimal("0.30")]
    per_month = [
        (base_cost * p / Decimal(months_in_period)) for p in parts
    ]

    # Помесячная инфляция → словарь (с клампом к максимальному месяцу)
    table = dict(MonthlyInflation.objects.values_list("month", "rate"))
    if not table:
        return rows, Decimal("0.00")
    max_month = max(table)

    total = Decimal("0")
    cur_month = start
    for period_idx in range(3):
        spend = per_month[period_idx]
        for _ in range(months_in_period):
            rate = table.get(cur_month) or table[max_month]
            amount = spend * rate
            rows.append({
                "month": cur_month if cur_month <= max_month else max_month,
                "rate": rate,
                "spend": spend.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "amount": amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            })
            total += amount
            cur_month += 1

    return rows, total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def calculate(
    *,
    city: City,
    purpose: BuildingPurpose,
    building_class: BuildingClass,
    total_area: Decimal,
    floors: int,
    underground_parking: bool,
    ground_parking_spaces: int,
    start_date: date,
) -> dict:
    # 1. Срок — единая таблица (area → months), линейная интерполяция
    duration_months = _interpolate_duration(total_area)

    # 2. Стоимость строительства
    rate = CostRate.objects.filter(city=city, building_class=building_class).first()
    price_per_sqm = rate.price_per_sqm if rate else Decimal("0")

    settings = Settings.objects.filter(is_active=True).first()
    base_cost = (total_area * price_per_sqm).quantize(Decimal("0.01"))

    # Инфляционное удорожание (помесячный метод)
    inflation_rows, inflation_amount = compute_inflation_increase(
        base_cost, duration_months or 0, start_date
    )
    construction_cost = (base_cost + inflation_amount).quantize(Decimal("0.01"))

    # 3. Площадь квартир
    apartments_area = (total_area * purpose.apartments_area_ratio).quantize(
        Decimal("0.01")
    )

    # 4. Социалка
    # 4.1. Число жителей (норма — переопределение города → дефолт настроек → константа)
    sqm_per_resident = (
        city.sqm_per_resident
        or (settings.default_sqm_per_resident if settings else None)
        or DEFAULT_SQM_PER_RESIDENT
    )
    if sqm_per_resident and sqm_per_resident > 0:
        residents = ceil(apartments_area / sqm_per_resident)
    else:
        residents = 0

    # 4.2. Нормативы мест на 1000 жителей (город → дефолт настроек → константа)
    doo_per_1000 = (
        city.doo_per_1000
        or (settings.default_doo_per_1000 if settings else None)
        or DEFAULT_DOO_PER_1000
    )
    sosh_per_1000 = (
        city.sosh_per_1000
        or (settings.default_sosh_per_1000 if settings else None)
        or DEFAULT_SOSH_PER_1000
    )

    # 4.3. Места и стоимость (стоимость места — из активного норматива)
    norms = SocialNorms.objects.filter(is_active=True).first()
    doo_seats = ceil(Decimal(residents) * Decimal("0.001") * doo_per_1000)
    sosh_seats = ceil(Decimal(residents) * Decimal("0.001") * sosh_per_1000)
    if norms:
        doo_cost = (Decimal(doo_seats) * norms.cost_per_doo_seat).quantize(
            Decimal("0.01")
        )
        sosh_cost = (Decimal(sosh_seats) * norms.cost_per_school_seat).quantize(
            Decimal("0.01")
        )
    else:
        doo_cost = sosh_cost = Decimal("0.00")

    # 5. Паркинг
    parking_rate = ParkingRate.objects.filter(city=city).first()
    cost_per_space = parking_rate.cost_per_space if parking_rate else Decimal("0")
    ground_parking_cost = (Decimal(ground_parking_spaces) * cost_per_space).quantize(
        Decimal("0.01")
    )

    # 6. Распределение по статьям расходов (база — стоимость строительства)
    cost_items = []
    cost_items_total_percent = Decimal("0")
    cost_items_total_amount = Decimal("0")
    items = CostItem.objects.filter(is_active=True).order_by("order", "code")
    for item in items:
        # сумма по статье: база × % / 100, округление ВВЕРХ до копейки
        amount = (construction_cost * item.percent / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_CEILING
        )
        cost_items.append(
            {
                "code": item.code,
                "name": item.name,
                "percent": item.percent,
                "amount": amount,
                "item_type": item.item_type,
                "is_child": item.parent_id is not None,
            }
        )
        # в ИТОГО — только обычные статьи и подстатьи (агрегат-сумма не учитывается)
        if item.item_type in (CostItem.TYPE_ARTICLE, CostItem.TYPE_SUBARTICLE):
            cost_items_total_percent += item.percent
            cost_items_total_amount += amount

    return {
        "duration_months": duration_months,
        "price_per_sqm": price_per_sqm,
        "inflation_rows": inflation_rows,
        "start_date": start_date,
        "base_cost": base_cost,
        "inflation_amount": inflation_amount,
        "construction_cost": construction_cost,
        "total_area": total_area,
        "apartments_area": apartments_area,
        "residents": residents,
        "doo_seats": doo_seats,
        "doo_cost": doo_cost,
        "sosh_seats": sosh_seats,
        "sosh_cost": sosh_cost,
        "underground_parking": underground_parking,
        "ground_parking_spaces": ground_parking_spaces,
        "ground_parking_cost": ground_parking_cost,
        "cost_items": cost_items,
        "cost_items_total_percent": cost_items_total_percent,
        "cost_items_total_amount": cost_items_total_amount,
    }
