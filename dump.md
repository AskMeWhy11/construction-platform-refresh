# Dump

## Tree

```
calc/templates/calc/form.html
calc/forms.py
calc/models.py
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
                <label class="label" for="{{ form.total_area.id_for_label }}" data-area-label>{{ form.total_area.label }}</label>
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
                <div class="field {% if not form.ground_parking.value %}hidden{% endif %}" data-depends-on="ground_parking">
            <label class="label" for="{{ form.ground_parking_spaces.id_for_label }}">
                {{ form.ground_parking_spaces.label }}
            </label>
            {{ form.ground_parking_spaces }}
            {{ form.ground_parking_spaces.errors }}
        </div>

        {# ── Отделка (только Ж/Г) ── #}
        <div class="field hidden" data-finish-block>
            <label class="checkbox-row">
                {{ form.finish_enabled }}
                <span>{{ form.finish_enabled.label }}</span>
            </label>
            {{ form.finish_enabled.errors }}
        </div>

        <div class="field hidden" data-finish-options>
            <span class="label">{{ form.finish_type.label }}</span>
            <div class="radio-group">{{ form.finish_type }}</div>
            {{ form.finish_type.errors }}

            <div class="field hidden" data-finish-custom>
                <label class="label" for="{{ form.finish_custom_rate.id_for_label }}">
                    {{ form.finish_custom_rate.label }}
                </label>
                {{ form.finish_custom_rate }}
                {{ form.finish_custom_rate.errors }}
            </div>
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
                    <div class="result-item-label">{{ result.apartments_area_label }}</div>
                    <div class="result-item-value">
                        {{ result.apartments_area|spaces }}<span class="suffix">м²</span>
                    </div>
                </div>
            </div>
        </div>

        {% if result.finish_enabled or result.floor_multiplier > 1 %}
        <div class="result-section">
            <h3 class="result-section-title">Коэффициенты и отделка</h3>
            <div class="result-grid">
                {% if result.floor_multiplier > 1 %}
                <div class="result-item">
                    <div class="result-item-label">Множитель этажности (≥30 эт.)</div>
                    <div class="result-item-value">×{{ result.floor_multiplier }}</div>
                </div>
                {% endif %}
                {% if result.finish_enabled %}
                <div class="result-item">
                    <div class="result-item-label">Отделка · {{ result.finish_rate|spaces }} ₽/м²</div>
                    <div class="result-item-value">
                        {{ result.finish_cost|spaces }}<span class="suffix">₽</span>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {# Инфляционное удорожание #}
        {% if result.inflation_rows %}
        <div class="result-section">
            <details class="accordion">
                <summary class="accordion-summary">
                    <span class="accordion-head">
                        <span class="accordion-title">Инфляционное удорожание</span>
                        <span class="accordion-hint">Помесячный расчёт · нажмите, чтобы развернуть</span>
                    </span>
                    <span class="accordion-meta">{{ result.inflation_amount|spaces }} ₽</span>
                    <span class="accordion-chevron" aria-hidden="true">▾</span>
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
        {% if result.doo_cost or result.sosh_cost %}
        <div class="result-section">
            <h3 class="result-section-title">Социальная инфраструктура</h3>
            <div class="result-grid">
                {% if result.doo_cost %}
                <div class="result-item">
                    <div class="result-item-label">ДОО — мест</div>
                    <div class="result-item-value">
                        {{ result.doo_seats }}
                        <span class="suffix">{{ result.doo_cost|spaces }} ₽</span>
                    </div>
                </div>
                {% endif %}
                {% if result.sosh_cost %}
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

### `calc/forms.py`

```python
from datetime import date
from decimal import Decimal
from django import forms

from .models import BuildingClass, BuildingPurpose, City


FINISH_TYPE_WB = "wb"
FINISH_TYPE_ROUGH = "rough"
FINISH_TYPE_FINE = "fine"
FINISH_TYPE_DESIGNER = "designer"
FINISH_TYPE_CHOICES = [
    (FINISH_TYPE_WB, "White Box"),
    (FINISH_TYPE_ROUGH, "Черновая"),
    (FINISH_TYPE_FINE, "Чистовая"),
    (FINISH_TYPE_DESIGNER, "Дизайнерская"),
]


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
    # ── Отделка ──
    finish_enabled = forms.BooleanField(label="Учитывать отделку", required=False)
    finish_type = forms.ChoiceField(
        label="Тип отделки", choices=FINISH_TYPE_CHOICES,
        widget=forms.RadioSelect, required=False, initial=FINISH_TYPE_WB,
    )
    finish_custom_rate = forms.DecimalField(
        label="Стоимость дизайнерской отделки, ₽/м²",
        min_value=0, max_digits=12, decimal_places=2, required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            cls = field.widget.__class__.__name__
            if cls in ("Select", "NullBooleanSelect"):
                field.widget.attrs.setdefault("class", "select")
            elif cls in ("CheckboxInput", "RadioSelect"):
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

        # Отделка доступна только для Ж/Г
        if cleaned.get("finish_enabled"):
            if purpose and not purpose.finish_enabled:
                self.add_error(
                    "finish_enabled",
                    "Отделка доступна только для жилых и гостиничных объектов.",
                )
                cleaned["finish_enabled"] = False
            else:
                ftype = cleaned.get("finish_type")
                if not ftype:
                    self.add_error("finish_type", "Выберите тип отделки.")
                elif ftype == FINISH_TYPE_DESIGNER and not cleaned.get("finish_custom_rate"):
                    self.add_error(
                        "finish_custom_rate",
                        "Укажите стоимость дизайнерской отделки.",
                    )
        return cleaned

class PurposeSelect(forms.Select):
    """Select с data-category на каждом option (для JS-динамики отделки/лейбла)."""

    def __init__(self, *args, **kwargs):
        self._category_map = kwargs.pop("category_map", {})
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        pk = getattr(value, "value", value)
        cat = self._category_map.get(pk)
        if cat:
            option["attrs"]["data-category"] = cat
        return option
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
