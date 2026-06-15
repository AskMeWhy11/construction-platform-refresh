from decimal import Decimal

from django.db import migrations, models


# (тип, города-дефолты) — заполняются константы по умолчанию из п.6
FINISH_DEFAULTS = {
    "default_finish_wb_res": Decimal("15000.00"),
    "default_finish_wb_hotel": Decimal("20000.00"),
    "default_finish_rough_res": Decimal("5000.00"),
    "default_finish_rough_hotel": Decimal("6000.00"),
    "default_finish_fine_res": Decimal("25000.00"),
    "default_finish_fine_hotel": Decimal("40000.00"),
}

# назначение → категория (сид)
PURPOSE_CATEGORY = {
    "Жилые объекты": "residential",
    "Туристические объекты": "hotel",
}


def seed_data(apps, schema_editor):
    BuildingClass = apps.get_model("calc", "BuildingClass")
    BuildingPurpose = apps.get_model("calc", "BuildingPurpose")
    Settings = apps.get_model("calc", "Settings")

    # Флаг социального класса
    BuildingClass.objects.filter(
        name="Социальный объект (ДОО/СОШ)"
    ).update(is_social=True)

    # Категории назначений
    for name, cat in PURPOSE_CATEGORY.items():
        BuildingPurpose.objects.filter(name=name).update(category=cat)

    # Дефолты отделки в активных/существующих настройках
    for s in Settings.objects.all():
        changed = False
        for field, val in FINISH_DEFAULTS.items():
            if getattr(s, field, None) in (None, Decimal("0.00")):
                setattr(s, field, val)
                changed = True
        if changed:
            s.save()


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("calc", "0009_seed_monthly_inflation"),
    ]

    operations = [
        # ── BuildingPurpose.category ──
        migrations.AddField(
            model_name="buildingpurpose",
            name="category",
            field=models.CharField(
                "Категория", max_length=20, default="other",
                choices=[
                    ("residential", "Жилое"),
                    ("hotel", "Гостиница / туризм"),
                    ("other", "Прочее"),
                ],
                help_text="Влияет на учёт отделки и лейбл площади. Отделка доступна для «Жилое» и «Гостиница».",
            ),
        ),
        # ── BuildingClass.is_social ──
        migrations.AddField(
            model_name="buildingclass",
            name="is_social",
            field=models.BooleanField(
                "Социальный объект (ДОО/СОШ)", default=False,
                help_text="Используется как источник себестоимости для расчёта стоимости ДОО/СОШ.",
            ),
        ),
        # ── City.finish_* ──
        migrations.AddField(model_name="city", name="finish_wb_res",
            field=models.DecimalField("Отделка White Box, жилое, ₽/м²", max_digits=12, decimal_places=2, null=True, blank=True)),
        migrations.AddField(model_name="city", name="finish_wb_hotel",
            field=models.DecimalField("Отделка White Box, гостиница, ₽/м²", max_digits=12, decimal_places=2, null=True, blank=True)),
        migrations.AddField(model_name="city", name="finish_rough_res",
            field=models.DecimalField("Отделка черновая, жилое, ₽/м²", max_digits=12, decimal_places=2, null=True, blank=True)),
        migrations.AddField(model_name="city", name="finish_rough_hotel",
            field=models.DecimalField("Отделка черновая, гостиница, ₽/м²", max_digits=12, decimal_places=2, null=True, blank=True)),
        migrations.AddField(model_name="city", name="finish_fine_res",
            field=models.DecimalField("Отделка чистовая, жилое, ₽/м²", max_digits=12, decimal_places=2, null=True, blank=True)),
        migrations.AddField(model_name="city", name="finish_fine_hotel",
            field=models.DecimalField("Отделка чистовая, гостиница, ₽/м²", max_digits=12, decimal_places=2, null=True, blank=True)),
        # ── Settings.default_finish_* ──
        migrations.AddField(model_name="settings", name="default_finish_wb_res",
            field=models.DecimalField("WB, жилое, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("15000.00"))),
        migrations.AddField(model_name="settings", name="default_finish_wb_hotel",
            field=models.DecimalField("WB, гостиница, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("20000.00"))),
        migrations.AddField(model_name="settings", name="default_finish_rough_res",
            field=models.DecimalField("Черновая, жилое, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("5000.00"))),
        migrations.AddField(model_name="settings", name="default_finish_rough_hotel",
            field=models.DecimalField("Черновая, гостиница, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("6000.00"))),
        migrations.AddField(model_name="settings", name="default_finish_fine_res",
            field=models.DecimalField("Чистовая, жилое, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("25000.00"))),
        migrations.AddField(model_name="settings", name="default_finish_fine_hotel",
            field=models.DecimalField("Чистовая, гостиница, ₽/м² (по умолчанию)", max_digits=12, decimal_places=2, default=Decimal("40000.00"))),
        migrations.RunPython(seed_data, unseed),
    ]