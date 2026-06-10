# Dump

## Tree

```
calc/admin.py
calc/views.py
calc/templates/calc/result.html
calc/templates/calc/form.html
```

### `calc/admin.py`

```python
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from . import views_admin
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


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(BuildingPurpose)
class BuildingPurposeAdmin(admin.ModelAdmin):
    list_display = ("name", "apartments_area_ratio", "allowed_classes_count")
    search_fields = ("name",)
    filter_horizontal = ("allowed_classes",)

    @admin.display(description="Классов")
    def allowed_classes_count(self, obj):
        return obj.allowed_classes.count()


@admin.register(BuildingClass)
class BuildingClassAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    list_editable = ("order",)


class CostRateAdmin(admin.ModelAdmin):
    list_display = ("city", "building_class", "price_per_sqm")
    list_filter = ("city", "building_class")
    search_fields = ("city__name", "building_class__name")
    list_editable = ("price_per_sqm",)
    change_list_template = "calc/admin_costrate_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("pivot/", self.admin_site.admin_view(views_admin.cost_pivot),
                 name="calc_costrate_pivot"),
            path("pivot/save/", self.admin_site.admin_view(views_admin.cost_pivot_save),
                 name="calc_costrate_pivot_save"),
            path("pivot/add-city/", self.admin_site.admin_view(views_admin.cost_pivot_add_city),
                 name="calc_costrate_pivot_add_city"),
            path("pivot/import/preview/",
                 self.admin_site.admin_view(views_admin.cost_pivot_import_preview),
                 name="calc_costrate_pivot_import_preview"),
            path("pivot/import/apply/",
                 self.admin_site.admin_view(views_admin.cost_pivot_import_apply),
                 name="calc_costrate_pivot_import_apply"),
        ]
        return custom + urls


admin.site.register(CostRate, CostRateAdmin)


# Алиасы под namespace, который ждёт views_admin (reverse 'calc_admin:...').
# Используем имена URL-ов admin-сайта напрямую — переопределим reverse через шорткат.
# Чтобы не плодить namespace, переписываем views_admin reverse на admin-имена:
# (см. правки ниже в шаблоне — используем {% url 'admin:calc_costrate_pivot_save' %})


@admin.register(ConstructionDuration)
class ConstructionDurationAdmin(admin.ModelAdmin):
    list_display = ("area", "months")
    list_editable = ("months",)
    list_display_links = ("area",)
    ordering = ("area",)
    list_per_page = 100
    search_fields = ("area",)


@admin.register(Inflation)
class InflationAdmin(admin.ModelAdmin):
    list_display = ("rate", "is_active", "note")
    list_editable = ("is_active",)


@admin.register(SocialNorms)
class SocialNormsAdmin(admin.ModelAdmin):
    list_display = (
        "sqm_per_doo_seat",
        "cost_per_doo_seat",
        "sqm_per_school_seat",
        "cost_per_school_seat",
        "is_active",
    )


@admin.register(ParkingRate)
class ParkingRateAdmin(admin.ModelAdmin):
    list_display = ("city", "cost_per_space")
    list_editable = ("cost_per_space",)


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ("inflation_clean_coef", "is_active")


admin.site.site_header = "Экспресс-стройэкспертиза — админка"
admin.site.site_title = "Экспресс-стройэкспертиза"
admin.site.index_title = "Управление справочниками"
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
                    ground_parking_spaces=cd.get("ground_parking_spaces") or 0,
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

        {# Коэффициенты #}
        <div class="result-section">
            <h3 class="result-section-title">Коэффициенты</h3>
            <div class="result-grid">
                <div class="result-item">
                    <div class="result-item-label">Очистка от инфляции</div>
                    <div class="result-item-value">{{ result.clean_coef|floatformat:3 }}</div>
                </div>
                <div class="result-item">
                    <div class="result-item-label">Ставка инфляции</div>
                    <div class="result-item-value">{{ result.inflation_rate|floatformat:4 }}</div>
                </div>
            </div>
        </div>

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
