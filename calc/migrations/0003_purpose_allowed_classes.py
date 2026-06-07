from django.db import migrations, models


MAPPING = {
    "Жилые объекты": [
        "Эконом", "Стандарт", "Комфорт", "Бизнес", "Премиум", "Элит",
        "Апартаменты", "ИЖС", "Таунхаус",
    ],
    "Туристические объекты": [
        "Гостиница 3*", "Гостиница 4*", "Гостиница 5*",
    ],
    "Социальные объекты": [
        "Социальный объект (ДОО/СОШ)", "Медицинский объект",
    ],
    "Административные объекты": [
        "Офис класс A", "Офис класс B", "Офис класс C",
        "Бизнес-центр", "Торговый центр", "Стрит-ритейл",
        "Склад класс A", "Склад класс B", "Производство (лёгкое)",
    ],
}


def seed(apps, schema_editor):
    Purpose = apps.get_model("calc", "BuildingPurpose")
    BClass = apps.get_model("calc", "BuildingClass")

    # 1. Гарантируем существование 4 назначений и нужных классов.
    for purpose_name, class_names in MAPPING.items():
        purpose, _ = Purpose.objects.get_or_create(name=purpose_name)
        class_objs = []
        for cname in class_names:
            obj, _ = BClass.objects.get_or_create(name=cname)
            class_objs.append(obj)
        purpose.allowed_classes.set(class_objs)


def unseed(apps, schema_editor):
    Purpose = apps.get_model("calc", "BuildingPurpose")
    for p in Purpose.objects.all():
        p.allowed_classes.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("calc", "0002_construction_duration_area"),  # имя из предыдущего шага
    ]

    operations = [
        migrations.AddField(
            model_name="buildingpurpose",
            name="allowed_classes",
            field=models.ManyToManyField(
                blank=True,
                help_text="Классы, которые будут предлагаться в форме при выборе этого назначения.",
                related_name="purposes",
                to="calc.buildingclass",
                verbose_name="Доступные классы строительства",
            ),
        ),
        migrations.RunPython(seed, unseed),
    ]