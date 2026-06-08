from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calc", "0004_seed_demo.py"),
    ]

    operations = [
        migrations.AddField(
            model_name="city",
            name="sqm_per_resident",
            field=models.DecimalField(
                "Норма площади на жителя, м²", max_digits=6, decimal_places=2,
                null=True, blank=True,
                help_text="Переопределение для города. Пусто → значение по умолчанию из настроек.",
            ),
        ),
        migrations.AddField(
            model_name="city",
            name="doo_per_1000",
            field=models.DecimalField(
                "Норматив ДОО на 1000 жителей", max_digits=7, decimal_places=2,
                null=True, blank=True,
                help_text="Переопределение для города. Пусто → значение по умолчанию из настроек.",
            ),
        ),
        migrations.AddField(
            model_name="city",
            name="sosh_per_1000",
            field=models.DecimalField(
                "Норматив СОШ на 1000 жителей", max_digits=7, decimal_places=2,
                null=True, blank=True,
                help_text="Переопределение для города. Пусто → значение по умолчанию из настроек.",
            ),
        ),
        migrations.AddField(
            model_name="settings",
            name="default_sqm_per_resident",
            field=models.DecimalField(
                "Норма площади на жителя, м² (по умолчанию)",
                max_digits=6, decimal_places=2, default=Decimal("30.00"),
            ),
        ),
        migrations.AddField(
            model_name="settings",
            name="default_doo_per_1000",
            field=models.DecimalField(
                "Норматив ДОО на 1000 жителей (по умолчанию)",
                max_digits=7, decimal_places=2, default=Decimal("65.00"),
            ),
        ),
        migrations.AddField(
            model_name="settings",
            name="default_sosh_per_1000",
            field=models.DecimalField(
                "Норматив СОШ на 1000 жителей (по умолчанию)",
                max_digits=7, decimal_places=2, default=Decimal("135.00"),
            ),
        ),
    ]