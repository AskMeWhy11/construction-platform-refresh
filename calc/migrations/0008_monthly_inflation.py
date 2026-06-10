from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("calc", "0007_seed_costitem")]

    operations = [
        migrations.CreateModel(
            name="MonthlyInflation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.PositiveSmallIntegerField(unique=True, verbose_name="Месяц")),
                ("rate", models.DecimalField(decimal_places=4, max_digits=6, help_text="Доля, например 0.0806 = 8.06%", verbose_name="Инфляция")),
            ],
            options={
                "verbose_name": "Помесячная инфляция",
                "verbose_name_plural": "Инфляция (помесячно)",
                "ordering": ["month"],
            },
        ),
    ]