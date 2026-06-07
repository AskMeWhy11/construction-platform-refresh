from decimal import Decimal
from django.db import migrations


# name -> order
BUILDING_CLASSES = [
    ("Эконом", 10), ("Стандарт", 20), ("Комфорт", 30), ("Бизнес", 40),
    ("Премиум", 50), ("Элит", 60), ("Апартаменты", 70), ("ИЖС", 80),
    ("Таунхаус", 90), ("Офис класс A", 100), ("Офис класс B", 110),
    ("Офис класс C", 120), ("Бизнес-центр", 130), ("Торговый центр", 140),
    ("Стрит-ритейл", 150), ("Гостиница 3*", 160), ("Гостиница 4*", 170),
    ("Гостиница 5*", 180), ("Склад класс A", 190), ("Склад класс B", 200),
    ("Производство (лёгкое)", 210), ("Социальный объект (ДОО/СОШ)", 220),
    ("Медицинский объект", 230),
]

CITIES = [
    "Астрахань", "Брянск", "Владивосток", "Волгоград", "Иваново", "Иркутск",
    "Казань", "Калининград", "Калуга", "Кострома", "Крым", "ЛО", "МО",
    "Москва", "Пенза", "Рязань", "Самара", "Санкт-Петербург", "Саратов",
    "Смоленск", "Сочи", "Тверь", "Тула", "Тюмень", "Уфа", "Хабаровск",
    "Челябинск", "Ярославль", "Ростов-на-Дону",
]

# (город, класс, цена/м²)
COST_RATES = [
    ("Москва", "Эконом", "95000.00"),
    ("Москва", "Стандарт", "115000.00"),
    ("Москва", "Комфорт", "135000.00"),
    ("Москва", "Бизнес", "165000.00"),
    ("Москва", "Премиум", "210000.00"),
    ("Москва", "Бизнес-центр", "135000.00"),
    ("Москва", "Торговый центр", "135000.00"),
    ("Санкт-Петербург", "Эконом", "85000.00"),
    ("Санкт-Петербург", "Стандарт", "100000.00"),
    ("Санкт-Петербург", "Комфорт", "120000.00"),
    ("Санкт-Петербург", "Бизнес-центр", "120000.00"),
    ("Казань", "Эконом", "65000.00"),
    ("Казань", "Стандарт", "78000.00"),
    ("Казань", "Торговый центр", "82000.00"),
]

# город -> цена машиноместа
PARKING_RATES = [
    ("Москва", "850000.00"),
    ("Санкт-Петербург", "750000.00"),
    ("Казань", "550000.00"),
]


def seed(apps, schema_editor):
    City = apps.get_model("calc", "City")
    BuildingClass = apps.get_model("calc", "BuildingClass")
    CostRate = apps.get_model("calc", "CostRate")
    ParkingRate = apps.get_model("calc", "ParkingRate")
    Inflation = apps.get_model("calc", "Inflation")
    SocialNorms = apps.get_model("calc", "SocialNorms")
    Settings = apps.get_model("calc", "Settings")

    for name, order in BUILDING_CLASSES:
        BuildingClass.objects.get_or_create(name=name, defaults={"order": order})

    for name in CITIES:
        City.objects.get_or_create(name=name)

    cls = {c.name: c for c in BuildingClass.objects.all()}
    cities = {c.name: c for c in City.objects.all()}

    for city_name, class_name, price in COST_RATES:
        CostRate.objects.get_or_create(
            city=cities[city_name],
            building_class=cls[class_name],
            defaults={"price_per_sqm": Decimal(price)},
        )

    for city_name, cost in PARKING_RATES:
        ParkingRate.objects.get_or_create(
            city=cities[city_name],
            defaults={"cost_per_space": Decimal(cost)},
        )

    if not Inflation.objects.exists():
        Inflation.objects.create(
            rate=Decimal("0.0732"), is_active=True, note="ЦБ РФ, 2025 Q1"
        )

    if not SocialNorms.objects.exists():
        SocialNorms.objects.create(
            sqm_per_doo_seat=Decimal("8.50"),
            cost_per_doo_seat=Decimal("1500000.00"),
            sqm_per_school_seat=Decimal("12.00"),
            cost_per_school_seat=Decimal("1800000.00"),
            is_active=True,
        )

    if not Settings.objects.exists():
        Settings.objects.create(
            inflation_clean_coef=Decimal("0.900"), is_active=True
        )


def unseed(apps, schema_editor):
    # Демо-данные удаляем только то, что безопасно (не трогаем классы/города:
    # ими также владеет миграция 0003). Оставляем no-op во избежание потери данных.
    pass


class Migration(migrations.Migration):

    dependencies = [("calc", "0003_purpose_allowed_classes")]

    operations = [
        migrations.RunPython(seed, unseed),
    ]