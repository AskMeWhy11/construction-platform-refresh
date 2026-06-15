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
        initial=date.today,
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

        # data-category на option назначения (для JS-динамики отделки/лейбла)
        cat_map = dict(BuildingPurpose.objects.values_list("pk", "category"))
        self.fields["purpose"].widget = PurposeSelect(category_map=cat_map)
        self.fields["purpose"].widget.choices = self.fields["purpose"].choices

        for name, field in self.fields.items():
            cls = field.widget.__class__.__name__
            if cls in ("Select", "NullBooleanSelect", "PurposeSelect"):
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