# Dump

## Tree

```
calc/services.py
calc/views.py
calc/models.py
```

### `calc/services.py`

```python
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from math import ceil

DEFAULT_SQM_PER_RESIDENT = Decimal("30.00")
DEFAULT_DOO_PER_1000 = Decimal("65.00")
DEFAULT_SOSH_PER_1000 = Decimal("135.00")

FINISH_TYPE_WB = "wb"
FINISH_TYPE_ROUGH = "rough"
FINISH_TYPE_FINE = "fine"
FINISH_TYPE_DESIGNER = "designer"

FLOOR_MULT_THRESHOLD = 30
FLOOR_MULT = Decimal("1.25")

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
    apartments_area_label: str
    residents: int
    underground_parking: bool
    ground_parking_spaces: int
    ground_parking_cost: Decimal
    doo_seats: int
    doo_cost: Decimal
    sosh_seats: int
    sosh_cost: Decimal
    price_per_sqm: Decimal
    floor_multiplier: Decimal
    finish_enabled: bool
    finish_type: str
    finish_rate: Decimal
    finish_cost: Decimal

    def as_dict(self):
        return asdict(self)


def _interpolate_duration(total_area: Decimal) -> int | None:
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
    today = today or date.today()
    months = (start_date.year - today.year) * 12 + (start_date.month - today.month)
    if start_date.day > today.day:
        months += 1
    if months < 0:
        months = 0
    return months + 1


def compute_inflation_increase(base_cost: Decimal, duration_months: int, start_date: date):
    rows: list[dict] = []
    if not duration_months or duration_months < 1:
        return rows, Decimal("0.00")

    start = _start_month(start_date)

    months_in_period = int(
        (Decimal(duration_months) / Decimal("3")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    if months_in_period < 1:
        months_in_period = 1

    last_period_months = duration_months - 2 * months_in_period
    if last_period_months < 1:
        last_period_months = 1

    period_lengths = [months_in_period, months_in_period, last_period_months]

    parts = [Decimal("0.30"), Decimal("0.40"), Decimal("0.30")]
    per_month = [
        base_cost * parts[i] / Decimal(period_lengths[i]) for i in range(3)
    ]

    table = dict(MonthlyInflation.objects.values_list("month", "rate"))
    if not table:
        return rows, Decimal("0.00")
    max_month = max(table)

    total = Decimal("0")
    cur_month = start
    for period_idx in range(3):
        spend = per_month[period_idx]
        for _ in range(period_lengths[period_idx]):
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


def _finish_rate(*, city, purpose, finish_type, finish_custom_rate, settings) -> Decimal:
    """₽/м² отделки по типу и категории. Дизайнерская — ввод пользователя;
    остальное: город → дефолт настроек → 0."""
    if finish_type == FINISH_TYPE_DESIGNER:
        return finish_custom_rate or Decimal("0")

    is_hotel = purpose.category == BuildingPurpose.CAT_HOTEL
    suffix = "hotel" if is_hotel else "res"
    key = {
        FINISH_TYPE_WB: "wb",
        FINISH_TYPE_ROUGH: "rough",
        FINISH_TYPE_FINE: "fine",
    }.get(finish_type)
    if not key:
        return Decimal("0")

    val = getattr(city, f"finish_{key}_{suffix}", None)
    if val is not None:
        return val
    if settings is not None:
        return getattr(settings, f"default_finish_{key}_{suffix}", None) or Decimal("0")
    return Decimal("0")


def _social_price_per_sqm(city) -> Decimal:
    """Себестоимость м² социального объекта (класс is_social) для города."""
    rate = (
        CostRate.objects
        .filter(city=city, building_class__is_social=True)
        .order_by("building_class__order")
        .first()
    )
    return rate.price_per_sqm if rate else Decimal("0")


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
    finish_enabled: bool = False,
    finish_type: str = FINISH_TYPE_WB,
    finish_custom_rate: Decimal | None = None,
) -> dict:
    # 1. Срок
    duration_months = _interpolate_duration(total_area)

    # 2. Стоимость строительства
    rate = CostRate.objects.filter(city=city, building_class=building_class).first()
    price_per_sqm = rate.price_per_sqm if rate else Decimal("0")

    settings = Settings.objects.filter(is_active=True).first()

    # 2.1. Площадь квартир / номерного фонда
    apartments_area = (total_area * purpose.apartments_area_ratio).quantize(
        Decimal("0.01")
    )
    rest_area = total_area - apartments_area
    apartments_area_label = (
        "Площадь номерного фонда" if purpose.is_hotel else "Площадь квартир"
    )

    # 2.2. Множитель этажности (≥30 этажей → 1.25 на rest-площадь)
    floor_multiplier = FLOOR_MULT if floors >= FLOOR_MULT_THRESHOLD else Decimal("1")

    # 2.3. Отделка (только Ж/Г)
    finish_enabled = bool(finish_enabled and purpose.finish_enabled)
    if finish_enabled:
        finish_rate = _finish_rate(
            city=city, purpose=purpose, finish_type=finish_type,
            finish_custom_rate=finish_custom_rate, settings=settings,
        )
    else:
        finish_rate = Decimal("0")

    # 2.4. База: rest × price × floor_mult + квартиры × (price + finish_rate)
    base_rest = (rest_area * price_per_sqm * floor_multiplier)
    apt_unit = price_per_sqm + finish_rate
    base_apt = (apartments_area * apt_unit)
    finish_cost = (apartments_area * finish_rate).quantize(Decimal("0.01"))
    base_cost = (base_rest + base_apt).quantize(Decimal("0.01"))

    # Инфляция
    inflation_rows, inflation_amount = compute_inflation_increase(
        base_cost, duration_months or 0, start_date
    )
    construction_cost = (base_cost + inflation_amount).quantize(Decimal("0.01"))

    inflation_rate = (
        (inflation_amount / base_cost) if base_cost else Decimal("0")
    )
    clean_coef = settings.inflation_clean_coef if settings else Decimal("0.900")

    # 4. Социалка
    sqm_per_resident = (
        city.sqm_per_resident
        or (settings.default_sqm_per_resident if settings else None)
        or DEFAULT_SQM_PER_RESIDENT
    )
    if sqm_per_resident and sqm_per_resident > 0:
        residents = ceil(apartments_area / sqm_per_resident)
    else:
        residents = 0

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

    # 4.3. Места и стоимость: seats × sqm_per_seat × себестоимость соц-класса
    norms = SocialNorms.objects.filter(is_active=True).first()
    doo_seats = ceil(Decimal(residents) * Decimal("0.001") * doo_per_1000)
    sosh_seats = ceil(Decimal(residents) * Decimal("0.001") * sosh_per_1000)

    social_price = _social_price_per_sqm(city)
    if norms and social_price > 0:
        doo_cost = (
            Decimal(doo_seats) * norms.sqm_per_doo_seat * social_price
        ).quantize(Decimal("0.01"))
        sosh_cost = (
            Decimal(sosh_seats) * norms.sqm_per_school_seat * social_price
        ).quantize(Decimal("0.01"))
    else:
        doo_cost = sosh_cost = Decimal("0.00")

    # 5. Паркинг
    parking_rate = ParkingRate.objects.filter(city=city).first()
    cost_per_space = parking_rate.cost_per_space if parking_rate else Decimal("0")
    ground_parking_cost = (Decimal(ground_parking_spaces) * cost_per_space).quantize(
        Decimal("0.01")
    )

    # 6. Статьи расходов
    cost_items = []
    cost_items_total_percent = Decimal("0")
    cost_items_total_amount = Decimal("0")
    items = CostItem.objects.filter(is_active=True).order_by("order", "code")
    for item in items:
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
        "inflation_rate": inflation_rate,
        "clean_coef": clean_coef,
        "construction_cost": construction_cost,
        "total_area": total_area,
        "apartments_area": apartments_area,
        "apartments_area_label": apartments_area_label,
        "residents": residents,
        "doo_seats": doo_seats,
        "doo_cost": doo_cost,
        "sosh_seats": sosh_seats,
        "sosh_cost": sosh_cost,
        "underground_parking": underground_parking,
        "ground_parking_spaces": ground_parking_spaces,
        "ground_parking_cost": ground_parking_cost,
        "floor_multiplier": floor_multiplier,
        "finish_enabled": finish_enabled,
        "finish_type": finish_type,
        "finish_rate": finish_rate,
        "finish_cost": finish_cost,
        "cost_items": cost_items,
        "cost_items_total_percent": cost_items_total_percent,
        "cost_items_total_amount": cost_items_total_amount,
    }
```

### `calc/views.py`

```python
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .forms import CalcForm
from .models import BuildingClass
from .services import CalcError, calculate
from .models import BuildingClass, BuildingPurpose


@require_GET
def purpose_meta(request, purpose_id: int):
    p = BuildingPurpose.objects.filter(pk=purpose_id).values(
        "id", "category"
    ).first()
    if not p:
        return JsonResponse({"error": "not found"}, status=404)
    is_hotel = p["category"] == BuildingPurpose.CAT_HOTEL
    finish_enabled = p["category"] in (
        BuildingPurpose.CAT_RESIDENTIAL, BuildingPurpose.CAT_HOTEL
    )
    return JsonResponse({
        "category": p["category"],
        "finish_enabled": finish_enabled,
        "area_label": "Площадь номерного фонда" if is_hotel else "Общая площадь, м²",
    })

def index(request):
    result = None
    error = None
    if request.method == "POST":
        form = CalcForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                result = calculate(
                    city=cd["city"],
                    purpose=cd["purpose"],
                    building_class=cd["building_class"],
                    floors=cd["floors"],
                    total_area=cd["total_area"],
                    underground_parking=cd.get("underground_parking", False),
                    ground_parking_spaces=cd.get("ground_parking_spaces") or 0,
                    start_date=cd["start_date"],
                    finish_enabled=cd.get("finish_enabled", False),
                    finish_type=cd.get("finish_type") or "wb",
                    finish_custom_rate=cd.get("finish_custom_rate"),
                )
            except CalcError as e:
                error = str(e)
    else:
        form = CalcForm()

    return render(request, "calc/form.html", {
        "form": form,
        "result": result,
        "error": error,
        "active": "calc",
    })


def history(request):
    return render(request, "calc/history.html", {"active": "history"})


@require_GET
def classes_for_purpose(request, purpose_id: int):
    qs = (
        BuildingClass.objects
        .filter(purposes__id=purpose_id)
        .order_by("order", "name")
        .values("id", "name")
    )
    return JsonResponse({"classes": list(qs)})
```

### `calc/models.py`

```python
from decimal import Decimal
from django.db import models


class City(models.Model):
    name = models.CharField("Город", max_length=100, unique=True)

    sqm_per_resident = models.DecimalField(
        "Норма площади на жителя, м²", max_digits=6, decimal_places=2,
        null=True, blank=True,
        help_text="Переопределение для города. Пусто → значение по умолчанию из настроек.",
    )
    doo_per_1000 = models.DecimalField(
        "Норматив ДОО на 1000 жителей", max_digits=7, decimal_places=2,
        null=True, blank=True,
        help_text="Переопределение для города. Пусто → значение по умолчанию из настроек.",
    )
    sosh_per_1000 = models.DecimalField(
        "Норматив СОШ на 1000 жителей", max_digits=7, decimal_places=2,
        null=True, blank=True,
        help_text="Переопределение для города. Пусто → значение по умолчанию из настроек.",
    )
    # ── Множители отделки, ₽/м² (переопределение для города; пусто → дефолт из настроек) ──
    finish_wb_res = models.DecimalField(
        "Отделка White Box, жилое, ₽/м²", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    finish_wb_hotel = models.DecimalField(
        "Отделка White Box, гостиница, ₽/м²", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    finish_rough_res = models.DecimalField(
        "Отделка черновая, жилое, ₽/м²", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    finish_rough_hotel = models.DecimalField(
        "Отделка черновая, гостиница, ₽/м²", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    finish_fine_res = models.DecimalField(
        "Отделка чистовая, жилое, ₽/м²", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    finish_fine_hotel = models.DecimalField(
        "Отделка чистовая, гостиница, ₽/м²", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BuildingPurpose(models.Model):
    """Функциональное назначение (для расчёта площади квартир и формы)."""
    CAT_RESIDENTIAL = "residential"
    CAT_HOTEL = "hotel"
    CAT_OTHER = "other"
    CATEGORY_CHOICES = [
        (CAT_RESIDENTIAL, "Жилое"),
        (CAT_HOTEL, "Гостиница / туризм"),
        (CAT_OTHER, "Прочее"),
    ]

    name = models.CharField("Назначение", max_length=100, unique=True)
    category = models.CharField(
        "Категория", max_length=20, choices=CATEGORY_CHOICES, default=CAT_OTHER,
        help_text="Влияет на учёт отделки и лейбл площади. Отделка доступна для «Жилое» и «Гостиница».",
    )
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

    @property
    def finish_enabled(self) -> bool:
        return self.category in (self.CAT_RESIDENTIAL, self.CAT_HOTEL)

    @property
    def is_hotel(self) -> bool:
        return self.category == self.CAT_HOTEL


class BuildingClass(models.Model):
    name = models.CharField("Класс/Тип объекта", max_length=100, unique=True)
    order = models.PositiveIntegerField("Порядок", default=0)
    is_social = models.BooleanField(
        "Социальный объект (ДОО/СОШ)", default=False,
        help_text="Используется как источник себестоимости для расчёта стоимости ДОО/СОШ.",
    )

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
    default_sqm_per_resident = models.DecimalField(
        "Норма площади на жителя, м² (по умолчанию)",
        max_digits=6, decimal_places=2, default=Decimal("30.00"),
    )
    default_doo_per_1000 = models.DecimalField(
        "Норматив ДОО на 1000 жителей (по умолчанию)",
        max_digits=7, decimal_places=2, default=Decimal("65.00"),
    )
    default_sosh_per_1000 = models.DecimalField(
        "Норматив СОШ на 1000 жителей (по умолчанию)",
        max_digits=7, decimal_places=2, default=Decimal("135.00"),
    )
    # ── Дефолтные множители отделки, ₽/м² (п.6) ──
    default_finish_wb_res = models.DecimalField(
        "WB, жилое, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("15000.00"),
    )
    default_finish_wb_hotel = models.DecimalField(
        "WB, гостиница, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("20000.00"),
    )
    default_finish_rough_res = models.DecimalField(
        "Черновая, жилое, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("5000.00"),
    )
    default_finish_rough_hotel = models.DecimalField(
        "Черновая, гостиница, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("6000.00"),
    )
    default_finish_fine_res = models.DecimalField(
        "Чистовая, жилое, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("25000.00"),
    )
    default_finish_fine_hotel = models.DecimalField(
        "Чистовая, гостиница, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("40000.00"),
    )
    is_active = models.BooleanField("Активна", default=False)

    class Meta:
        verbose_name = "Настройка расчёта"
        verbose_name_plural = "Настройки расчёта"

    def __str__(self):
        return f"clean={self.inflation_clean_coef} ({'актив' if self.is_active else 'архив'})"
    
class CostItem(models.Model):
    """Статья расходов на строительство. % считается от стоимости строительства."""

    TYPE_ARTICLE = "article"
    TYPE_SUM = "sum"
    TYPE_SUBARTICLE = "subarticle"
    TYPE_CHOICES = [
        (TYPE_ARTICLE, "статья"),
        (TYPE_SUM, "Σ сумма"),
        (TYPE_SUBARTICLE, "подстатья"),
    ]

    code = models.CharField("Код", max_length=20)
    name = models.CharField("Наименование", max_length=400)
    percent = models.DecimalField(
        "% от базы", max_digits=7, decimal_places=2, default=Decimal("0.00"),
        help_text="Процент от стоимости строительства.",
    )
    order = models.PositiveIntegerField("Порядок", default=0)
    item_type = models.CharField("Тип", max_length=20, choices=TYPE_CHOICES, default=TYPE_ARTICLE)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children", verbose_name="Родительская статья",
    )
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Статья расходов"
        verbose_name_plural = "Статьи расходов на строительство"
        ordering = ["order", "code"]

    def __str__(self):
        return f"{self.code} {self.name}"

    @property
    def counts_in_total(self) -> bool:
        """В ИТОГО входят только обычные статьи и подстатьи (не агрегат-сумма)."""
        return self.item_type in (self.TYPE_ARTICLE, self.TYPE_SUBARTICLE)

class MonthlyInflation(models.Model):
    """Помесячная таблица инфляции для расчёта инфляционного удорожания."""
    month = models.PositiveSmallIntegerField("Месяц", unique=True)
    rate = models.DecimalField(
        "Инфляция", max_digits=6, decimal_places=4,
        help_text="Доля, например 0.0806 = 8.06%",
    )

    class Meta:
        verbose_name = "Помесячная инфляция"
        verbose_name_plural = "Инфляция (помесячно)"
        ordering = ["month"]

    def __str__(self):
        return f"мес. {self.month}: {self.rate}"

```
