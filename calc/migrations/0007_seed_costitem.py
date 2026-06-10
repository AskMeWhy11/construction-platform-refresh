from decimal import Decimal

from django.db import migrations


SEED = [
    # code, name, percent, order, type, parent_code
    ("2.1", "Подготовительный период, в т.ч. устройство подкрановых путей, перебазировка вертикального транспорта, демонтажные работы и работы по выносу сетей", "1.20", 10, "article", None),
    ("2.2", "Общестроительные работы, в т.ч.:", "68.89", 20, "sum", None),
    ("2.2.1", "Внутренняя отделка реализуемых площадей", "5.89", 21, "subarticle", "2.2"),
    ("2.2.2", "Общестроительные работы (за исключением внутренней отделки реализуемых площадей)", "63.00", 22, "subarticle", "2.2"),
    ("2.3", "Внутренние инженерные системы", "15.00", 30, "article", None),
    ("2.4", "Наружные инженерные сети, в т.ч. затраты на техприсоединение к ИС", "10.00", 40, "article", None),
    ("2.5", "Благоустройство и озеленение территории, объекты транспортного хозяйства", "3.50", 50, "article", None),
    ("2.6", "Содержание службы заказчика-застройщика, в т.ч. охрана объекта", "4.00", 60, "article", None),
    ("2.7", "Проектные и изыскательские работы, авторский надзор, экспертиза проекта, экспертное сопровождение", "3.30", 70, "article", None),
    ("2.8", "Резерв на непредвиденные расходы", "7.00", 80, "article", None),
]


def seed(apps, schema_editor):
    CostItem = apps.get_model("calc", "CostItem")
    if CostItem.objects.exists():
        return
    created = {}
    for code, name, percent, order, item_type, parent_code in SEED:
        created[code] = CostItem.objects.create(
            code=code, name=name, percent=Decimal(percent),
            order=order, item_type=item_type, is_active=True,
            parent=created.get(parent_code),
        )


def unseed(apps, schema_editor):
    CostItem = apps.get_model("calc", "CostItem")
    CostItem.objects.filter(code__in=[r[0] for r in SEED]).delete()


class Migration(migrations.Migration):
    dependencies = [("calc", "0006_costitem")]  # заменить на имя файла выше
    operations = [migrations.RunPython(seed, unseed)]