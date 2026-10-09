from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Расширяет точность помесячной инфляции с 4 до 7 знаков после запятой.

    Целая часть не меняется: было 2 знака (max_digits=6, decimal_places=4),
    стало 2 знака (max_digits=9, decimal_places=7) — потолок остаётся 99.9999999.
    """

    dependencies = [("calc", "0010_finishing")]

    operations = [
        migrations.AlterField(
            model_name="monthlyinflation",
            name="rate",
            field=models.DecimalField(
                verbose_name="Инфляция", max_digits=9, decimal_places=7,
                help_text="Доля, например 0.0806000 = 8.06% (до 7 знаков после запятой)",
            ),
        ),
    ]
