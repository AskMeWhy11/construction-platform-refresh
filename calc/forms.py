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