# Dump

## Tree

```
calc/models.py
calc/services.py
```

### `calc/models.py`

```python
from decimal import Decimal
from django.db import models


class City(models.Model):
    name = models.CharField("Город", max_length=100, unique=True)

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BuildingPurpose(models.Model):
    """Функциональное назначение (для расчёта площади квартир и формы)."""
    name = models.CharField("Назначение", max_length=100, unique=True)
    apartments_area_ratio = models.DecimalField(
        "Доля площади квартир",
        max_digits=4, decimal_places=3, default=Decimal("0.000"),
        help_text="0.000–1.000. Например, 0.750 = 75% от общей площади.",
    )
    allowed_classes = models.ManyToManyField(
        "BuildingClass",
        verbose_name="Доступные классы строительства",
        related_name="purposes",
        blank=True,
        help_text="Классы, которые будут предлагаться в форме при выборе этого назначения.",
    )

    class Meta:
        verbose_name = "Функциональное назначение"
        verbose_name_plural = "Функциональные назначения"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BuildingClass(models.Model):
    name = models.CharField("Класс/Тип объекта", max_length=100, unique=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Класс строительства"
        verbose_name_plural = "Классы строительства"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class CostRate(models.Model):
    """Себестоимость ₽/м² по (город × класс)."""
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="Город")
    building_class = models.ForeignKey(BuildingClass, on_delete=models.CASCADE, verbose_name="Класс")
    price_per_sqm = models.DecimalField("Цена за м², ₽", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Себестоимость"
        verbose_name_plural = "Себестоимость (таблица)"
        unique_together = [("city", "building_class")]
        ordering = ["city__name", "building_class__order"]

    def __str__(self):
        return f"{self.city} / {self.building_class}: {self.price_per_sqm} ₽/м²"


class ConstructionDuration(models.Model):
    """Опорная точка зависимости «общая площадь → срок строительства, мес.».

    Срок для произвольной площади вычисляется линейной интерполяцией между
    ближайшими опорными точками. За пределами диапазона срок клампится
    к крайним значениям таблицы.
    """
    area = models.PositiveIntegerField("Площадь, м²", unique=True)
    months = models.PositiveSmallIntegerField("Срок строительства, мес.")

    class Meta:
        verbose_name = "Срок строительства"
        verbose_name_plural = "Сроки строительства"
        ordering = ["area"]

    def __str__(self):
        return f"{self.area:,} м² → {self.months} мес."


class Inflation(models.Model):
    rate = models.DecimalField("Ставка инфляции", max_digits=6, decimal_places=4, help_text="Например, 0.0732")
    is_active = models.BooleanField("Активна", default=False)
    note = models.CharField("Комментарий", max_length=200, blank=True)

    class Meta:
        verbose_name = "Инфляция"
        verbose_name_plural = "Инфляция"

    def __str__(self):
        return f"{self.rate} ({'актив' if self.is_active else 'архив'})"


class SocialNorms(models.Model):
    sqm_per_doo_seat = models.DecimalField("м² на место ДОО", max_digits=8, decimal_places=2)
    cost_per_doo_seat = models.DecimalField("Стоимость места ДОО, ₽", max_digits=12, decimal_places=2)
    sqm_per_school_seat = models.DecimalField("м² на место СОШ", max_digits=8, decimal_places=2)
    cost_per_school_seat = models.DecimalField("Стоимость места СОШ, ₽", max_digits=12, decimal_places=2)
    is_active = models.BooleanField("Активна", default=False)

    class Meta:
        verbose_name = "Норматив социалки"
        verbose_name_plural = "Нормативы социалки"

    def __str__(self):
        return f"ДОО {self.sqm_per_doo_seat}м²/{self.cost_per_doo_seat}₽ | СОШ {self.sqm_per_school_seat}м²/{self.cost_per_school_seat}₽"


class ParkingRate(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name="Город", unique=True)
    cost_per_space = models.DecimalField("Стоимость машиноместа, ₽", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Тариф наземного паркинга"
        verbose_name_plural = "Наземный паркинг (тарифы)"

    def __str__(self):
        return f"{self.city}: {self.cost_per_space} ₽/мм"


class Settings(models.Model):
    inflation_clean_coef = models.DecimalField(
        "Коэф. очистки от инфляции", max_digits=4, decimal_places=3, default=Decimal("0.900"),
    )
    is_active = models.BooleanField("Активна", default=False)

    class Meta:
        verbose_name = "Настройка расчёта"
        verbose_name_plural = "Настройки расчёта"

    def __str__(self):
        return f"clean={self.inflation_clean_coef} ({'актив' if self.is_active else 'архив'})"
```

### `calc/services.py`

```python
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

    base_cost = (total_area * price_per_sqm).quantize(Decimal("0.01"))
    inflation_amount = (base_cost * clean_coef * inflation_rate).quantize(Decimal("0.01"))
    construction_cost = (base_cost + inflation_amount).quantize(Decimal("0.01"))

    # 3. Площадь квартир
    apartments_area = (total_area * purpose.apartments_area_ratio).quantize(Decimal("0.01"))

    # 4. Социалка
    norms = SocialNorms.objects.filter(is_active=True).first()
    if norms:
        doo_seats = ceil(apartments_area / norms.sqm_per_doo_seat)
        doo_cost = (Decimal(doo_seats) * norms.cost_per_doo_seat).quantize(Decimal("0.01"))
        sosh_seats = ceil(apartments_area / norms.sqm_per_school_seat)
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
```
