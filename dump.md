# Dump

## Tree

```
calc/models.py
calc/forms.py
calc/services.py
calc/views.py
calc/templates/calc/form.html
calc/static/calc/app.css
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
            <details class="accordion">
                <summary class="result-section-title accordion-summary">
                    Инфляционное удорожание
                    <span class="accordion-meta">{{ result.inflation_amount|spaces }} ₽</span>
                </summary>
                <table class="cost-items-table">
                    <thead>
                        <tr>
                            <th class="num">Затраты/мес, ₽</th>
                            <th class="num">Удорожание, ₽</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in result.inflation_rows %}
                        <tr class="cost-item-row">
                            <td class="num">{{ r.spend|spaces }}</td>
                            <td class="num">{{ r.amount|spaces }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                    <tfoot>
                        <tr class="cost-item-total">
                            <td class="num">Итого удорожание</td>
                            <td class="num">{{ result.inflation_amount|spaces }}</td>
                        </tr>
                    </tfoot>
                </table>
            </details>
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

### `calc/static/calc/app.css`

```
/* ==========================================================================
   Шрифты Сбера
   ========================================================================== */
@font-face {
    font-family: "SB Sans Text";
    src: url("fonts/SBSansText-Light.woff2") format("woff2"),
         url("fonts/SBSansText-Light.woff") format("woff");
    font-weight: 300;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: "SB Sans Text";
    src: url("fonts/SBSansText-Regular.woff2") format("woff2"),
         url("fonts/SBSansText-Regular.woff") format("woff");
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: "SB Sans Text";
    src: url("fonts/SBSansText-Medium.woff2") format("woff2"),
         url("fonts/SBSansText-Medium.woff") format("woff");
    font-weight: 500;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: "SB Sans Text";
    src: url("fonts/SBSansText-Semibold.woff2") format("woff2"),
         url("fonts/SBSansText-Semibold.woff") format("woff");
    font-weight: 600;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: "SB Sans Display";
    src: url("fonts/SBSansDisplay-Regular.woff2") format("woff2"),
         url("fonts/SBSansDisplay-Regular.woff") format("woff");
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}

/* ==========================================================================
   Дизайн-токены (палитра Сбера)
   ========================================================================== */
:root {
    /* Brand */
    --sber-green:        #21A19A;
    --sber-green-deep:   #107F8C;
    --sber-ink:          #005E7F;
    --sber-arctic:       #42E3B4;
    --sber-mint-100:     #BEF8EC;
    --sber-mint-50:      #E7FFFF;

    /* Семантика — light */
    --bg:                #F4F6F8;
    --surface:           #FFFFFF;
    --surface-2:         #FAFBFC;
    --surface-soft:      var(--sber-mint-50);
    --border:            #E4E8EC;
    --border-strong:     #D0D6DC;

    --text:              #1D2733;
    --text-soft:         #5B6876;
    --text-muted:        #8A96A3;

    --accent:            var(--sber-green);
    --accent-hover:      var(--sber-green-deep);
    --accent-soft:       var(--sber-mint-50);
    --accent-on:         #FFFFFF;

    --danger:            #E74C3C;
    --warning:           #F39C12;

    --shadow-sm:         0 1px 2px rgba(20, 30, 40, .04);
    --shadow-md:         0 6px 20px rgba(20, 30, 40, .06);

    --radius:            14px;
    --radius-sm:         10px;
    --radius-xs:         8px;

    --font-text:    "SB Sans Text", -apple-system, "Segoe UI", Roboto, Inter, sans-serif;
    --font-display: "SB Sans Display", "SB Sans Text", -apple-system, "Segoe UI", sans-serif;
}

/* Тёмная тема */
body.theme-dark {
    --bg:                #0F1620;
    --surface:           #1A2330;
    --surface-2:         #212C3B;
    --surface-soft:      #16302E;
    --border:            #2C3A4D;
    --border-strong:     #3A4B62;

    --text:              #E6EDF3;
    --text-soft:         #B1BBC6;
    --text-muted:        #7D8893;

    --accent:            var(--sber-arctic);
    --accent-hover:      #6CECC4;
    --accent-soft:       #16302E;
    --accent-on:         #0F1620;

    --shadow-sm:         0 1px 2px rgba(0, 0, 0, .4);
    --shadow-md:         0 6px 20px rgba(0, 0, 0, .4);
}

/* ==========================================================================
   База
   ========================================================================== */
* { box-sizing: border-box; }

html, body {
    margin: 0; padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-text);
    font-size: 14px;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

a { color: var(--accent-hover); text-decoration: none; }
a:hover { text-decoration: underline; }

::selection { background: var(--accent); color: var(--accent-on); }

/* ==========================================================================
   Топбар
   ========================================================================== */
.topbar {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 14px 28px;
    display: flex;
    align-items: center;
    gap: 20px;
    position: sticky; top: 0; z-index: 50;
}
.brand {
    display: flex; align-items: center; gap: 12px;
    color: var(--text);
}
.brand:hover { text-decoration: none; }
.brand-logo {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, var(--sber-green) 0%, var(--sber-arctic) 100%);
    border-radius: 11px;
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 18px;
    box-shadow: 0 2px 8px rgba(33, 161, 154, .25);
}
.brand-text-main {
    font-family: var(--font-display);
    font-weight: 400;
    font-size: 17px;
    line-height: 1.1;
    letter-spacing: -.01em;
}
.brand-text-sub {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 2px;
}

.nav {
    display: flex; gap: 4px;
    margin: 0 auto;
    background: var(--bg);
    padding: 4px;
    border-radius: 11px;
    border: 1px solid var(--border);
}
.nav-link {
    padding: 9px 18px;
    border-radius: 8px;
    color: var(--text-soft);
    font-size: 14px;
    font-weight: 500;
    display: flex; align-items: center; gap: 7px;
    transition: background .15s, color .15s;
}
.nav-link:hover { color: var(--text); text-decoration: none; }
.nav-link.active {
    background: var(--surface);
    color: var(--text);
    box-shadow: var(--shadow-sm);
}

.topbar-actions { display: flex; align-items: center; gap: 8px; }
.icon-btn {
    width: 38px; height: 38px;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: var(--surface);
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    color: var(--text-soft);
    font-size: 16px;
    transition: border-color .15s, color .15s, background .15s;
    font-family: inherit;
}
.icon-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
    text-decoration: none;
}
.icon-btn.icon-btn-avatar {
    background: var(--accent-soft);
    border-color: var(--accent-soft);
    color: var(--accent-hover);
}

/* ==========================================================================
   Layout
   ========================================================================== */
.page {
    max-width: 1400px;
    margin: 0 auto;
    padding: 40px 28px 60px;
}

/* Hero (стиль «Мудреца» — крупный display + мелкая категория) */
.hero { margin-bottom: 32px; }
.hero-eyebrow {
    font-size: 12px;
    font-weight: 500;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--accent-hover);
    margin: 0 0 12px;
}
.hero-title {
    font-family: var(--font-display);
    font-weight: 400;
    font-size: clamp(32px, 4vw, 44px);
    line-height: 1.08;
    letter-spacing: -.02em;
    margin: 0 0 10px;
    color: var(--text);
}
.hero-sub {
    color: var(--text-soft);
    font-size: 15px;
    margin: 0;
    max-width: 640px;
}

/* Split */
.split {
    display: grid;
    grid-template-columns: minmax(380px, 1fr) 1.25fr;
    gap: 24px;
}
@media (max-width: 980px) { .split { grid-template-columns: 1fr; } }

.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 28px;
    box-shadow: var(--shadow-sm);
}
.card-title {
    margin: 0 0 22px;
    font-size: 17px;
    font-weight: 600;
    letter-spacing: -.01em;
}

/* ==========================================================================
   Формы
   ========================================================================== */
.field { margin-bottom: 16px; }
.field:last-child { margin-bottom: 0; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.label {
    display: block;
    font-size: 12px;
    color: var(--text-soft);
    margin-bottom: 6px;
    font-weight: 500;
}

.input, .select {
    width: 100%;
    padding: 11px 14px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--text);
    font-size: 14px;
    outline: none;
    transition: border-color .15s, box-shadow .15s;
    font-family: inherit;
}
.input:focus, .select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(33, 161, 154, .18);
}
body.theme-dark .input:focus,
body.theme-dark .select:focus {
    box-shadow: 0 0 0 3px rgba(66, 227, 180, .22);
}
.select {
    appearance: none;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'><path fill='%238a96a3' d='M6 8 0 0h12z'/></svg>");
    background-repeat: no-repeat;
    background-position: right 14px center;
    padding-right: 38px;
    cursor: pointer;
}
body.theme-dark .select {
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'><path fill='%237d8893' d='M6 8 0 0h12z'/></svg>");
}

.checkbox-row {
    display: flex; align-items: center; gap: 10px;
    padding: 12px 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    cursor: pointer;
    user-select: none;
    transition: border-color .15s, background .15s;
}
.checkbox-row:hover {
    border-color: var(--border-strong);
    background: var(--surface-2);
}
.checkbox-row input {
    width: 18px; height: 18px;
    accent-color: var(--accent);
    cursor: pointer;
}
.checkbox-row span { font-size: 14px; color: var(--text); }

.errorlist {
    color: var(--danger);
    font-size: 12px;
    list-style: none;
    padding: 0;
    margin: 6px 0 0;
}

.btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    padding: 12px 20px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all .15s;
    font-family: inherit;
}
.btn:hover {
    border-color: var(--accent);
    color: var(--accent-hover);
}
.btn-primary {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--accent-on);
    width: 100%;
    padding: 14px 20px;
    font-size: 15px;
    font-weight: 600;
    margin-top: 8px;
    box-shadow: 0 2px 8px rgba(33, 161, 154, .2);
}
.btn-primary:hover {
    background: var(--accent-hover);
    border-color: var(--accent-hover);
    color: var(--accent-on);
    text-decoration: none;
}

/* ==========================================================================
   Алерты
   ========================================================================== */
.alert {
    padding: 12px 16px;
    border-radius: var(--radius-sm);
    margin-bottom: 16px;
    font-size: 14px;
}
.alert-error {
    background: rgba(231, 76, 60, .1);
    border: 1px solid rgba(231, 76, 60, .3);
    color: var(--danger);
}

/* ==========================================================================
   Результаты — стиль «Визуализация данных»
   ========================================================================== */
.result-empty {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    min-height: 440px;
    text-align: center;
    color: var(--text-muted);
    gap: 14px;
}
.result-empty-icon {
    width: 96px; height: 96px;
    border-radius: 50%;
    background: var(--surface-soft);
    display: flex; align-items: center; justify-content: center;
    font-size: 38px;
    color: var(--accent-hover);
}
.result-empty-title {
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 400;
    color: var(--text);
    margin: 0;
    letter-spacing: -.01em;
}
.result-empty-sub { font-size: 13px; margin: 0; max-width: 280px; }

.result-section { margin-bottom: 24px; }
.result-section:last-child { margin-bottom: 0; }
.result-section-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--text-muted);
    font-weight: 600;
    margin: 0 0 12px;
}

.result-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.result-grid-3 { grid-template-columns: repeat(3, 1fr); }

.result-item {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
}
.result-item-label {
    font-size: 11px;
    color: var(--text-muted);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: .04em;
    font-weight: 500;
}
.result-item-value {
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 400;
    line-height: 1.1;
    color: var(--text);
    font-variant-numeric: tabular-nums;
    letter-spacing: -.01em;
}
.result-item-value .suffix {
    font-family: var(--font-text);
    font-size: 12px;
    font-weight: 500;
    color: var(--text-muted);
    margin-left: 4px;
    letter-spacing: 0;
}

/* Hero-карточка результата */
.result-hero {
    background: linear-gradient(135deg, var(--sber-green) 0%, var(--sber-green-deep) 100%);
    color: #fff;
    border-radius: var(--radius);
    padding: 24px 26px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.result-hero::after {
    content: "";
    position: absolute;
    right: -40px; top: -40px;
    width: 220px; height: 220px;
    background: radial-gradient(circle, rgba(66, 227, 180, .35) 0%, transparent 70%);
    pointer-events: none;
}
.result-hero-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .06em;
    opacity: .85;
    margin: 0 0 8px;
}
.result-hero-value {
    font-family: var(--font-display);
    font-size: clamp(32px, 3.5vw, 40px);
    font-weight: 400;
    line-height: 1.05;
    margin: 0;
    letter-spacing: -.02em;
    font-variant-numeric: tabular-nums;
}
.result-hero-value .suffix {
    font-family: var(--font-text);
    font-size: 15px;
    font-weight: 500;
    opacity: .85;
    margin-left: 6px;
    letter-spacing: 0;
}
.result-hero-meta {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid rgba(255, 255, 255, .18);
    display: flex; gap: 28px;
    font-size: 13px;
    opacity: .9;
}
.result-hero-meta b {
    font-weight: 600;
    display: block;
    font-size: 14px;
    margin-top: 2px;
}

/* ==========================================================================
   Placeholder (история)
   ========================================================================== */
.placeholder {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 80px 28px;
    text-align: center;
    color: var(--text-muted);
}
.placeholder-icon {
    width: 96px; height: 96px;
    margin: 0 auto 20px;
    border-radius: 50%;
    background: var(--surface-soft);
    display: flex; align-items: center; justify-content: center;
    font-size: 38px;
    color: var(--accent-hover);
}
.placeholder-title {
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 400;
    color: var(--text);
    margin: 0 0 8px;
    letter-spacing: -.01em;
}
.placeholder-sub { font-size: 14px; margin: 0; line-height: 1.6; }

/* ==========================================================================
   Tom Select — темизация под общий дизайн
   ========================================================================== */

/* Контейнер «кнопки» (свёрнутого селекта) */
.ts-wrapper.single .ts-control,
.ts-wrapper.multi .ts-control {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px 14px;
    min-height: 44px;
    font-family: var(--font-text);
    font-size: 15px;
    color: var(--text);
    box-shadow: none;
    transition: border-color .15s ease, box-shadow .15s ease;
}
.ts-wrapper.single.focus .ts-control,
.ts-wrapper.multi.focus .ts-control {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-soft);
    outline: none;
}
.ts-wrapper.single .ts-control > input,
.ts-wrapper.multi .ts-control > input {
    color: var(--text);
    font-family: inherit;
    font-size: inherit;
}
.ts-wrapper.single .ts-control > input::placeholder {
    color: var(--text-muted);
}

/* Стрелка справа */
.ts-wrapper.single .ts-control::after {
    border-color: var(--text-muted) transparent transparent transparent;
}
.ts-wrapper.single.dropdown-active .ts-control::after {
    border-color: transparent transparent var(--text-muted) transparent;
}

/* Выпадающее меню */
.ts-dropdown {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    box-shadow: 0 12px 32px rgba(15, 23, 42, .12);
    margin-top: 6px;
    padding: 6px;
    z-index: 1000;
}
.ts-dropdown .option {
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 14px;
    color: var(--text);
    cursor: pointer;
}
.ts-dropdown .option:hover,
.ts-dropdown .active {
    background: var(--surface-soft);
    color: var(--text);
}
.ts-dropdown .option.selected,
.ts-dropdown .active.selected {
    background: var(--accent);
    color: #fff;
    font-weight: 500;
}
.ts-dropdown .no-results {
    padding: 12px;
    color: var(--text-muted);
    font-size: 14px;
    text-align: center;
}

/* Строка поиска внутри dropdown */
.ts-dropdown .dropdown-input-wrap {
    padding: 6px 6px 8px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 6px;
}
.ts-dropdown input.dropdown-input {
    background: var(--surface-soft);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    font-family: var(--font-text);
    color: var(--text);
    width: 100%;
}
.ts-dropdown input.dropdown-input:focus {
    border-color: var(--accent);
    outline: none;
}

/* Состояние disabled */
.ts-wrapper.disabled .ts-control {
    background: var(--surface-soft);
    color: var(--text-muted);
    cursor: not-allowed;
    opacity: .7;
}


/* ==========================================================================
   Таблица статей расходов
   ========================================================================== */
.cost-items-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.cost-items-table th {
    text-align: left;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .04em;
    font-weight: 500;
    color: var(--text-muted);
    padding: 0 12px 10px;
    border-bottom: 1px solid var(--border);
}
.cost-items-table th.num,
.cost-items-table td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}
.cost-items-table td {
    padding: 11px 12px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    vertical-align: top;
}
.cost-items-table .code {
    color: var(--accent-hover);
    font-weight: 500;
    white-space: nowrap;
}
.cost-items-table .name { line-height: 1.4; }

/* Агрегат «Σ сумма» */
.cost-item-sum .name,
.cost-item-sum .code { font-weight: 600; color: var(--text); }

/* Подстатья — отступ */
.cost-item-child .code { padding-left: 18px; }
.cost-item-child .name { color: var(--text-soft); }

/* Итого */
.cost-item-total td {
    border-bottom: none;
    border-top: 2px solid var(--border-strong);
    padding-top: 13px;
    font-weight: 600;
    font-size: 14px;
}
.cost-item-total.cost-item-over .num { color: var(--danger); }

.cost-items-warning {
    margin: 10px 0 0;
    font-size: 12px;
    color: var(--danger);
    font-weight: 500;
}

.accordion-summary {
    cursor: pointer;
    list-style: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .5rem;
}
.accordion-summary::-webkit-details-marker { display: none; }
.accordion-summary::after {
    content: "▾";
    transition: transform .2s ease;
    font-size: .85em;
    opacity: .6;
}
.accordion[open] .accordion-summary::after { transform: rotate(180deg); }
.accordion-meta {
    font-weight: 600;
    opacity: .7;
    margin-left: auto;
}

/* ==========================================================================
   Утилиты
   ========================================================================== */
.hidden { display: none !important; }
```
