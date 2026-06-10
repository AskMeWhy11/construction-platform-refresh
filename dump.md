# Dump

## Tree

```
calc/models.py
calc/forms.py
calc/services.py
calc/views.py
calc/templates/calc/form.html
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

### `calc/forms.py`

```python
from datetime import date
from django import forms

from .models import BuildingClass, BuildingPurpose, City


class CalcForm(forms.Form):
    city = forms.ModelChoiceField(City.objects.all(), label="Локация")
    purpose = forms.ModelChoiceField(BuildingPurpose.objects.all(), label="Функциональное назначение")
    building_class = forms.ModelChoiceField(BuildingClass.objects.all(), label="Класс строительства")
    floors = forms.IntegerField(label="Количество этажей", min_value=1, max_value=200)
    total_area = forms.DecimalField(label="Общая площадь, м²", min_value=1, max_digits=12, decimal_places=2)
    start_date = forms.DateField(
        label="Дата начала строительства",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    underground_parking = forms.BooleanField(label="Подземный паркинг", required=False)
    ground_parking = forms.BooleanField(label="Наземный отдельностоящий паркинг", required=False)
    ground_parking_spaces = forms.IntegerField(
        label="Количество машиномест (наземный)", min_value=0, required=False, initial=0
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            cls = field.widget.__class__.__name__
            if cls in ("Select", "NullBooleanSelect"):
                field.widget.attrs.setdefault("class", "select")
            elif cls == "CheckboxInput":
                pass
            else:
                field.widget.attrs.setdefault("class", "input")

        # Сужаем queryset классов по выбранному назначению
        purpose_id = (
            self.data.get("purpose")
            or self.initial.get("purpose")
            or None
        )
        if purpose_id:
            try:
                self.fields["building_class"].queryset = BuildingClass.objects.filter(
                    purposes__id=purpose_id
                ).order_by("order", "name")
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned = super().clean()
        purpose = cleaned.get("purpose")
        building_class = cleaned.get("building_class")
        if purpose and building_class:
            if not purpose.allowed_classes.filter(pk=building_class.pk).exists():
                self.add_error(
                    "building_class",
                    "Этот класс недоступен для выбранного назначения.",
                )
        if cleaned.get("ground_parking") and not cleaned.get("ground_parking_spaces"):
            self.add_error("ground_parking_spaces", "Укажите количество машиномест.")
        return cleaned
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

```

### `calc/views.py`

```python
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .forms import CalcForm
from .models import BuildingClass
from .services import CalcError, calculate


def index(request):
    # ... без изменений
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
                    start_date=cd["start_date"],
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

### `calc/templates/calc/form.html`

```
{% extends "calc/base.html" %}
{% load calc_format %}

{% block title %}Калькулятор — СтройКалькулятор{% endblock %}

{% block content %}
<section class="hero">
    <p class="hero-eyebrow">Калькулятор</p>
    <h1 class="hero-title">Расчёт стоимости строительства</h1>
    <p class="hero-sub">
        Параметрический расчёт на базе нормативных стоимостей,
        классов строительства и поправочных коэффициентов.
    </p>
</section>

<div class="split">
    {# ── Левая карточка: форма ─────────────────────────────────────── #}
    <form method="post" class="card" novalidate>
        {% csrf_token %}
        <h2 class="card-title">Параметры проекта</h2>

        {% if error %}
        <div class="alert alert-error">{{ error }}</div>
        {% endif %}

        <div class="field">
            <label class="label" for="{{ form.city.id_for_label }}">{{ form.city.label }}</label>
            {{ form.city }}
            {{ form.city.errors }}
        </div>

        <div class="field">
            <label class="label" for="{{ form.purpose.id_for_label }}">{{ form.purpose.label }}</label>
            {{ form.purpose }}
            {{ form.purpose.errors }}
        </div>

        <div class="field">
            <label class="label" for="{{ form.building_class.id_for_label }}">{{ form.building_class.label }}</label>
            <div data-classes-field data-url-template="{% url 'calc:classes_for_purpose' 0 %}">
                {{ form.building_class }}
            </div>
            {{ form.building_class.errors }}
        </div>

        <div class="field-row">
            <div class="field">
                <label class="label" for="{{ form.floors.id_for_label }}">{{ form.floors.label }}</label>
                {{ form.floors }}
                {{ form.floors.errors }}
            </div>
            <div class="field">
                <label class="label" for="{{ form.total_area.id_for_label }}">{{ form.total_area.label }}</label>
                {{ form.total_area }}
                {{ form.total_area.errors }}
            </div>
        </div>

        <div class="field">
            <label class="label" for="{{ form.start_date.id_for_label }}">{{ form.start_date.label }}</label>
            {{ form.start_date }}
            {{ form.start_date.errors }}
        </div>

        <div class="field">
            <label class="checkbox-row">
                {{ form.underground_parking }}
                <span>{{ form.underground_parking.label }}</span>
            </label>
            {{ form.underground_parking.errors }}
        </div>

        <div class="field">
            <label class="checkbox-row">
                {{ form.ground_parking }}
                <span>{{ form.ground_parking.label }}</span>
            </label>
            {{ form.ground_parking.errors }}
        </div>

        <div class="field {% if not form.ground_parking.value %}hidden{% endif %}" data-depends-on="ground_parking">
            <label class="label" for="{{ form.ground_parking_spaces.id_for_label }}">
                {{ form.ground_parking_spaces.label }}
            </label>
            {{ form.ground_parking_spaces }}
            {{ form.ground_parking_spaces.errors }}
        </div>

        <button type="submit" class="btn btn-primary">Рассчитать проект</button>
    </form>

    {# ── Правая карточка: результаты ──────────────────────────────── #}
    <div class="card">
        <h2 class="card-title">Результат расчёта</h2>

        {% if result %}
        {# Hero — итоговая стоимость строительства #}
        <div class="result-hero">
            <p class="result-hero-label">Стоимость строительства</p>
            <p class="result-hero-value">
                {{ result.construction_cost|spaces }}<span class="suffix">₽</span>
            </p>
            <div class="result-hero-meta">
                <div>
                    Цена за м²
                    <b>{{ result.price_per_sqm|spaces }} ₽</b>
                </div>
                <div>
                    Площадь
                    <b>{{ result.total_area|spaces:2 }} м²</b>
                </div>
                {% if result.duration_months %}
                <div>
                    Срок строительства
                    <b>{{ result.duration_months }} мес.</b>
                </div>
                {% endif %}
            </div>
        </div>

        {# Базовые показатели #}
        <div class="result-section">
            <h3 class="result-section-title">Структура стоимости</h3>
            <div class="result-grid result-grid-3">
                <div class="result-item">
                    <div class="result-item-label">Базовая стоимость</div>
                    <div class="result-item-value">
                        {{ result.base_cost|spaces }}<span class="suffix">₽</span>
                    </div>
                </div>
                <div class="result-item">
                    <div class="result-item-label">Инфляция</div>
                    <div class="result-item-value">
                        {{ result.inflation_amount|spaces }}<span class="suffix">₽</span>
                    </div>
                </div>
                <div class="result-item">
                    <div class="result-item-label">Площадь квартир</div>
                    <div class="result-item-value">
                        {{ result.apartments_area|spaces }}<span class="suffix">м²</span>
                    </div>
                </div>
            </div>
        </div>

        {# Инфляционное удорожание #}
        {% if result.inflation_rows %}
        <div class="result-section">
            <h3 class="result-section-title">Инфляционное удорожание</h3>
            <table class="cost-items-table">
                <thead>
                    <tr>
                        <th class="num">Месяц</th>
                        <th class="num">Инфляция</th>
                        <th class="num">Затраты/мес, ₽</th>
                        <th class="num">Удорожание, ₽</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in result.inflation_rows %}
                    <tr class="cost-item-row">
                        <td class="num">{{ r.month }}</td>
                        <td class="num">{{ r.rate|floatformat:4 }}</td>
                        <td class="num">{{ r.spend|spaces }}</td>
                        <td class="num">{{ r.amount|spaces }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
                <tfoot>
                    <tr class="cost-item-total">
                        <td class="num" colspan="3">Итого удорожание</td>
                        <td class="num">{{ result.inflation_amount|spaces }}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        {% endif %}

        {# Соцобъекты #}
        {% if result.doo_seats or result.sosh_seats %}
        <div class="result-section">
            <h3 class="result-section-title">Социальная инфраструктура</h3>
            <div class="result-grid">
                {% if result.doo_seats %}
                <div class="result-item">
                    <div class="result-item-label">ДОО — мест</div>
                    <div class="result-item-value">
                        {{ result.doo_seats }}
                        <span class="suffix">{{ result.doo_cost|spaces }} ₽</span>
                    </div>
                </div>
                {% endif %}
                {% if result.sosh_seats %}
                <div class="result-item">
                    <div class="result-item-label">СОШ — мест</div>
                    <div class="result-item-value">
                        {{ result.sosh_seats }}
                        <span class="suffix">{{ result.sosh_cost|spaces }} ₽</span>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {# Паркинг #}
        {% if result.underground_parking or result.ground_parking_spaces %}
        <div class="result-section">
            <h3 class="result-section-title">Паркинг</h3>
            <div class="result-grid">
                {% if result.underground_parking %}
                <div class="result-item">
                    <div class="result-item-label">Подземный</div>
                    <div class="result-item-value">да</div>
                </div>
                {% endif %}
                {% if result.ground_parking_spaces %}
                <div class="result-item">
                    <div class="result-item-label">Наземный · {{ result.ground_parking_spaces }} м/м</div>
                    <div class="result-item-value">
                        {{ result.ground_parking_cost|spaces }}<span class="suffix">₽</span>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {# Статьи расходов на строительство #}
        {% if result.cost_items %}
        <div class="result-section">
            <h3 class="result-section-title">Статьи расходов на строительство</h3>
            <table class="cost-items-table">
                <thead>
                    <tr>
                        <th>Код</th>
                        <th>Наименование</th>
                        <th class="num">% от базы</th>
                        <th class="num">Сумма, ₽</th>
                    </tr>
                </thead>
                <tbody>
                    {% for ci in result.cost_items %}
                    <tr
                        class="cost-item-row cost-item-{{ ci.item_type }}{% if ci.is_child %} cost-item-child{% endif %}">
                        <td class="code">{{ ci.code }}</td>
                        <td class="name">{{ ci.name }}</td>
                        <td class="num">{{ ci.percent|floatformat:2 }}%</td>
                        <td class="num">{{ ci.amount|spaces }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
                <tfoot>
                    <tr class="cost-item-total{% if result.cost_items_total_percent > 100 %} cost-item-over{% endif %}">
                        <td></td>
                        <td>ИТОГО</td>
                        <td class="num">{{ result.cost_items_total_percent|floatformat:2 }}%</td>
                        <td class="num">{{ result.cost_items_total_amount|spaces }}</td>
                    </tr>
                </tfoot>
            </table>
            {% if result.cost_items_total_percent > 100 %}
            <p class="cost-items-warning">⚠ Сумма процентов превышает 100%</p>
            {% endif %}
        </div>
        {% endif %}

        {% else %}
        <div class="result-empty">
            <div class="result-empty-icon">∑</div>
            <p class="result-empty-title">Здесь появится расчёт</p>
            <p class="result-empty-sub">
                Заполните параметры слева и нажмите «Рассчитать проект».
            </p>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script>
    (function () {
        const purposeEl = document.querySelector('[name="purpose"]');
        const wrapper = document.querySelector('[data-classes-field]');
        if (!purposeEl || !wrapper) return;

        const classEl = wrapper.querySelector('select[name="building_class"]');
        const urlTemplate = wrapper.dataset.urlTemplate;  // .../api/classes/0/

        function tsOf(el) { return el.tomselect || null; }

        async function loadClasses(purposeId, preserve) {
            const ts = tsOf(classEl);
            if (!purposeId) {
                if (ts) {
                    ts.clear();
                    ts.clearOptions();
                } else {
                    classEl.innerHTML = '<option value="">———</option>';
                }
                return;
            }
            const url = urlTemplate.replace(/\/0\/?$/, '/' + purposeId + '/');
            const resp = await fetch(url, { headers: { 'Accept': 'application/json' } });
            if (!resp.ok) return;
            const data = await resp.json();

            const current = preserve ? (ts ? ts.getValue() : classEl.value) : '';

            if (ts) {
                ts.clear(true);
                ts.clearOptions();
                ts.addOption(data.classes.map(c => ({ value: String(c.id), text: c.name })));
                ts.refreshOptions(false);
                if (current && data.classes.some(c => String(c.id) === String(current))) {
                    ts.setValue(current, true);
                }
            } else {
                classEl.innerHTML = '<option value="">———</option>';
                for (const c of data.classes) {
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.textContent = c.name;
                    if (String(c.id) === String(current)) opt.selected = true;
                    classEl.appendChild(opt);
                }
            }
        }

        // Слушаем как нативное change, так и Tom Select-овское
        purposeEl.addEventListener('change', () => loadClasses(purposeEl.value, false));

        // Догрузка при восстановлении формы
        const initialPurpose = purposeEl.value;
        if (initialPurpose && classEl.options.length <= 1) {
            loadClasses(initialPurpose, true);
        }
    })();
</script>
{% endblock %}
```
