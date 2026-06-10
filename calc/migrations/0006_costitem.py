from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("calc", "0005_social_norms"),
    ]

    operations = [
        migrations.CreateModel(
            name="CostItem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField("Код", max_length=20)),
                ("name", models.CharField("Наименование", max_length=400)),
                ("percent", models.DecimalField("% от базы", max_digits=7, decimal_places=2, default=Decimal("0.00"), help_text="Процент от стоимости строительства.")),
                ("order", models.PositiveIntegerField("Порядок", default=0)),
                ("item_type", models.CharField("Тип", max_length=20, default="article",
                    choices=[("article", "статья"), ("sum", "Σ сумма"), ("subarticle", "подстатья")])),
                ("is_active", models.BooleanField("Активна", default=True)),
                ("parent", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="children", to="calc.costitem", verbose_name="Родительская статья")),
            ],
            options={
                "verbose_name": "Статья расходов",
                "verbose_name_plural": "Статьи расходов на строительство",
                "ordering": ["order", "code"],
            },
        ),
    ]