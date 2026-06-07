from django.db import migrations, models


DEFAULT_POINTS = [
    (10_000, 18),
    (20_000, 24),
    (30_000, 32),
    (40_000, 36),
    (50_000, 39),
    (60_000, 42),
    (70_000, 45),
    (80_000, 48),
    (100_000, 48),
    (120_000, 48),
    (150_000, 48),
]


def wipe_old(apps, schema_editor):
    apps.get_model("calc", "ConstructionDuration").objects.all().delete()


def seed(apps, schema_editor):
    Model = apps.get_model("calc", "ConstructionDuration")
    Model.objects.bulk_create(
        [Model(area=a, months=m) for a, m in DEFAULT_POINTS],
        ignore_conflicts=True,
    )


def unseed(apps, schema_editor):
    apps.get_model("calc", "ConstructionDuration").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("calc", "0001_initial")]

    operations = [
        migrations.RunPython(wipe_old, migrations.RunPython.noop),

        migrations.RemoveField(model_name="constructionduration", name="building_class"),
        migrations.RemoveField(model_name="constructionduration", name="purpose"),
        migrations.RemoveField(model_name="constructionduration", name="floors_min"),
        migrations.RemoveField(model_name="constructionduration", name="floors_max"),

        migrations.AddField(
            model_name="constructionduration",
            name="area",
            field=models.PositiveIntegerField(default=0, unique=True, verbose_name="Площадь, м²"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="constructionduration",
            name="months",
            field=models.PositiveSmallIntegerField(verbose_name="Срок строительства, мес."),
        ),
        migrations.AlterModelOptions(
            name="constructionduration",
            options={
                "ordering": ["area"],
                "verbose_name": "Срок строительства",
                "verbose_name_plural": "Сроки строительства",
            },
        ),

        migrations.RunPython(seed, unseed),
    ]