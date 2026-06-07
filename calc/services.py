from dataclasses import asdict, dataclass
from decimal import Decimal
from math import ceil

from .models import (
    BuildingClass,
    BuildingPurpose,
    City,
    ConstructionDuration,
    CostRate,
    Inflation,
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


def calculate(*, city: City, purpose: BuildingPurpose, building_class: BuildingClass,
              total_area: Decimal, floors: int, underground_parking: bool,
              ground_parking_spaces: int) -> dict:
    # 1. Срок — единая таблица (area → months), линейная интерполяция
    duration_months = _interpolate_duration(total_area)

    # 2. Стоимость строительства
    rate = CostRate.objects.filter(city=city, building_class=building_class).first()
    price_per_sqm = rate.price_per_sqm if rate else Decimal("0")

    settings = Settings.objects.filter(is_active=True).first()
    clean_coef = settings.inflation_clean_coef if settings else Decimal("0.900")

    inflation = Inflation.objects.filter(is_active=True).first()
    inflation_rate = inflation.rate if inflation else Decimal("0")

    base_cost = (total_area * price_per_sqm * clean_coef).quantize(Decimal("0.01"))
    inflation_amount = (base_cost * inflation_rate).quantize(Decimal("0.01"))
    construction_cost = (base_cost + inflation_amount).quantize(Decimal("0.01"))

    # 3. Площадь квартир
    apartments_area = (total_area * purpose.apartments_area_ratio).quantize(Decimal("0.01"))

    # 4. Социалка
    norms = SocialNorms.objects.filter(is_active=True).first()
    if norms:
        doo_seats = ceil(total_area / norms.sqm_per_doo_seat)
        doo_cost = (Decimal(doo_seats) * norms.cost_per_doo_seat).quantize(Decimal("0.01"))
        sosh_seats = ceil(total_area / norms.sqm_per_school_seat)
        sosh_cost = (Decimal(sosh_seats) * norms.cost_per_school_seat).quantize(Decimal("0.01"))
    else:
        doo_seats = sosh_seats = 0
        doo_cost = sosh_cost = Decimal("0.00")

    # 5. Паркинг
    parking_rate = ParkingRate.objects.filter(city=city).first()
    cost_per_space = parking_rate.cost_per_space if parking_rate else Decimal("0")
    ground_parking_cost = (Decimal(ground_parking_spaces) * cost_per_space).quantize(Decimal("0.01"))

    return {
        "duration_months": duration_months,
        "price_per_sqm": price_per_sqm,
        "clean_coef": clean_coef,
        "inflation_rate": inflation_rate,
        "base_cost": base_cost,
        "inflation_amount": inflation_amount,
        "construction_cost": construction_cost,
        "total_area": total_area,
        "apartments_area": apartments_area,
        "doo_seats": doo_seats,
        "doo_cost": doo_cost,
        "sosh_seats": sosh_seats,
        "sosh_cost": sosh_cost,
        "underground_parking": underground_parking,
        "ground_parking_spaces": ground_parking_spaces,
        "ground_parking_cost": ground_parking_cost,
    }