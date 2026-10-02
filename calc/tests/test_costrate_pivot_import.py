"""Тесты импорта Excel для страницы «Себестоимость (таблица)» → «Таблица».

Регресс: значения с конечными нулями (125200) не должны обрезаться до 1252.
"""
import json
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from calc.models import BuildingClass, City, CostRate
from calc.services_import import parse_workbook

PREVIEW_URL_NAME = "admin:calc_costrate_pivot_import_preview"
APPLY_URL_NAME = "admin:calc_costrate_pivot_import_apply"
PIVOT_URL_NAME = "admin:calc_costrate_pivot"


def make_xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(list(row))
    buf = BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def upload(payload: bytes, name="costrate.xlsx") -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name,
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class CostRatePivotImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.force_login(self.user)
        # Миграции-сиды 0004/0007 заполняют справочники.
        CostRate.objects.all().delete()
        City.objects.all().delete()
        BuildingClass.objects.all().delete()

        self.cls = BuildingClass.objects.create(name="БИЗНЕС", order=1)
        self.city = City.objects.create(name="Алтайский край")

    def test_parse_keeps_trailing_zeros(self):
        parsed = parse_workbook(make_xlsx([
            ("ГОРОД", "БИЗНЕС"),
            ("Алтайский край", 125200),
        ]))
        value = parsed["rows"][0]["cells"][0]["value"]
        self.assertEqual(value, "125200.00")
        self.assertEqual(Decimal(value), Decimal("125200"))

    def test_parse_keeps_trailing_zeros_in_decimals(self):
        parsed = parse_workbook(make_xlsx([
            ("ГОРОД", "БИЗНЕС"),
            ("Алтайский край", "1252,50"),
        ]))
        value = parsed["rows"][0]["cells"][0]["value"]
        self.assertEqual(Decimal(value), Decimal("1252.50"))

    def test_parse_various_trailing_zero_values(self):
        cases = [
            (125200, Decimal("125200")),
            (100, Decimal("100")),
            ("10.00", Decimal("10")),
            (125200000, Decimal("125200000")),
            ("77594,00", Decimal("77594")),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                parsed = parse_workbook(make_xlsx([
                    ("ГОРОД", "БИЗНЕС"),
                    ("Алтайский край", raw),
                ]))
                value = parsed["rows"][0]["cells"][0]["value"]
                self.assertEqual(Decimal(value), expected)

    def test_apply_stores_full_value(self):
        response = self.client.post(
            reverse(APPLY_URL_NAME),
            data=json.dumps({
                "parsed": {
                    "headers": [{"name": "БИЗНЕС", "class_id": self.cls.pk}],
                    "rows": [{
                        "city_name": self.city.name,
                        "city_id": self.city.pk,
                        "cells": [{
                            "class_id": self.cls.pk,
                            "value": "125200.00",
                            "error": None,
                        }],
                    }],
                },
                "overwrite": True,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        rate = CostRate.objects.get(city=self.city, building_class=self.cls)
        self.assertEqual(rate.price_per_sqm, Decimal("125200"))

    def test_preview_endpoint_keeps_trailing_zeros(self):
        response = self.client.post(
            reverse(PREVIEW_URL_NAME),
            {"file": upload(make_xlsx([
                ("ГОРОД", "БИЗНЕС"),
                ("Алтайский край", 125200),
            ]))},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(Decimal(payload["parsed"]["rows"][0]["cells"][0]["value"]), Decimal("125200"))

    def test_imported_value_renders_on_pivot_page(self):
        preview = self.client.post(
            reverse(PREVIEW_URL_NAME),
            {"file": upload(make_xlsx([
                ("ГОРОД", "БИЗНЕС"),
                ("Алтайский край", 125200),
            ]))},
        ).json()

        self.client.post(
            reverse(APPLY_URL_NAME),
            data=json.dumps({"parsed": preview["parsed"], "overwrite": True}),
            content_type="application/json",
        )

        # ru-ru: Decimal на странице рендерится с запятой
        response = self.client.get(reverse(PIVOT_URL_NAME))
        self.assertContains(response, "125200,00")
