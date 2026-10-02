"""Тесты импорта Excel для справочника «Инфляция (помесячно)»."""
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from calc.models import MonthlyInflation

IMPORT_URL_NAME = "admin:calc_monthlyinflation_import"


def make_xlsx(rows, sheet_title="Лист1", header=None) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title
    if header is not None:
        ws.append(list(header))
    for row in rows:
        ws.append(list(row))
    buf = BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def upload(payload: bytes, name="inflation.xlsx") -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name,
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class MonthlyInflationImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.force_login(self.user)
        # Миграция-сид 0009 заполняет ~128 месяцев: для арифметики тестов чистим таблицу.
        MonthlyInflation.objects.all().delete()

    def post(self, payload, name="inflation.xlsx"):
        return self.client.post(reverse(IMPORT_URL_NAME), {"file": upload(payload, name)}, follow=True)

    def messages(self, response):
        return [str(m) for m in response.context["messages"]]

    def test_changelist_has_import_button(self):
        response = self.client.get(reverse("admin:calc_monthlyinflation_changelist"))
        self.assertContains(response, "Импорт Excel")
        self.assertContains(response, reverse(IMPORT_URL_NAME))

    def test_import_page_renders(self):
        response = self.client.get(reverse(IMPORT_URL_NAME))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="file"')

    def test_creates_and_updates_rows(self):
        MonthlyInflation.objects.create(month=1, rate=Decimal("0.0732"))

        payload = make_xlsx(
            [
                ("Месяц", "Инфляция"),
                (1, "0,5000"),
                (2, 0.0747),
                (3, "0.0762"),
            ]
        )
        response = self.post(payload)

        self.assertEqual(MonthlyInflation.objects.count(), 3)
        self.assertEqual(MonthlyInflation.objects.get(month=1).rate, Decimal("0.5000"))
        self.assertEqual(MonthlyInflation.objects.get(month=2).rate, Decimal("0.0747"))
        self.assertIn("Создано 2, обновлено 1.", self.messages(response))

    def test_header_is_optional(self):
        payload = make_xlsx([(1, "0,1000"), (2, 0.2000)])
        response = self.post(payload)
        self.assertEqual(MonthlyInflation.objects.count(), 2)
        self.assertIn("Создано 2, обновлено 0.", self.messages(response))

    def test_broken_row_rolls_back(self):
        MonthlyInflation.objects.create(month=1, rate=Decimal("0.0732"))

        payload = make_xlsx(
            [
                ("Месяц", "Инфляция"),
                (1, "0.9000"),
                (2, "не число"),
            ]
        )
        response = self.post(payload)

        self.assertEqual(MonthlyInflation.objects.count(), 1)
        self.assertEqual(MonthlyInflation.objects.get(month=1).rate, Decimal("0.0732"))
        joined = " ".join(self.messages(response))
        self.assertIn("Строка 3", joined)
        self.assertIn("изменения не применены", joined)

    def test_duplicate_month_in_file_is_error(self):
        payload = make_xlsx([(1, 0.1), (1, 0.2)])
        response = self.post(payload)

        self.assertEqual(MonthlyInflation.objects.count(), 0)
        joined = " ".join(self.messages(response))
        self.assertIn("уже встречался", joined)

    def test_month_must_be_positive_integer(self):
        payload = make_xlsx([(0, 0.1)])
        response = self.post(payload)
        self.assertEqual(MonthlyInflation.objects.count(), 0)
        self.assertIn("месяц должен быть ≥ 1", " ".join(self.messages(response)))

    def test_rejects_wrong_extension(self):
        response = self.post(b"not excel", name="inflation.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Требуется файл .xlsx", " ".join(self.messages(response)))

    def test_rejects_unreadable_file(self):
        response = self.post(b"definitely not a workbook")
        self.assertEqual(MonthlyInflation.objects.count(), 0)
        self.assertIn("не удалось прочитать файл", " ".join(self.messages(response)))

    def test_requires_change_permission(self):
        user = User.objects.create_user("viewer", "v@example.com", "pw")
        user.user_permissions.add(
            Permission.objects.get(codename="view_monthlyinflation")
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse(IMPORT_URL_NAME), {"file": upload(make_xlsx([(1, 0.1)]))}, follow=False
        )
        # Без change-права admin_view уводит на страницу логина
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MonthlyInflation.objects.count(), 0)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse(IMPORT_URL_NAME))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
