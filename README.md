# Express Construction Expertise

[🇷🇺 Русский](#-русская-версия) · [🇬🇧 English](#-english-version)

---

<a id="-english-version"></a>

## 🇬🇧 English version

A web service for preliminary estimation of construction cost and timelines. The user enters object parameters and receives calculated timelines, cost, inflation markup, and social load. All reference data and rates are editable through the Django Admin; large tables are imported and exported as Excel files.

Released under the [MIT](LICENSE) license.

### Contents

- [Express Construction Expertise](#express-construction-expertise)
  - [🇬🇧 English version](#-english-version)
    - [Contents](#contents)
    - [Features](#features)
    - [Stack](#stack)
    - [Quick start](#quick-start)
    - [Running in Docker](#running-in-docker)
    - [Environment variables](#environment-variables)
    - [Project structure](#project-structure)
    - [Calculator: fields and result](#calculator-fields-and-result)
    - [HTTP endpoints](#http-endpoints)
    - [Admin panel](#admin-panel)
      - [Cost table (pivot)](#cost-table-pivot)
    - [Excel import and export](#excel-import-and-export)
      - [Inflation (monthly)](#inflation-monthly)
      - [Cost](#cost)
    - [Default settings](#default-settings)
    - [Calculation formulas](#calculation-formulas)
    - [Migrations](#migrations)
    - [Tests](#tests)
    - [Deployment](#deployment)
    - [Known limitations](#known-limitations)
    - [Contributing](#contributing)
    - [Security](#security)
    - [Third parties and licenses](#third-parties-and-licenses)
    - [License](#license)
  - [🇷🇺 Русская версия](#-русская-версия)
    - [Содержание](#содержание)
    - [Возможности](#возможности)
    - [Стек](#стек)
    - [Быстрый старт](#быстрый-старт)
    - [Запуск в Docker](#запуск-в-docker)
    - [Переменные окружения](#переменные-окружения)
    - [Структура проекта](#структура-проекта)
    - [Калькулятор: поля и результат](#калькулятор-поля-и-результат)
    - [HTTP-эндпоинты](#http-эндпоинты)
    - [Админка](#админка)
      - [Таблица себестоимости (pivot)](#таблица-себестоимости-pivot)
    - [Импорт и экспорт Excel](#импорт-и-экспорт-excel)
      - [Инфляция (помесячно)](#инфляция-помесячно)
      - [Себестоимость](#себестоимость)
    - [Настройки по умолчанию](#настройки-по-умолчанию)
    - [Формулы расчёта](#формулы-расчёта)
    - [Миграции](#миграции)
    - [Тесты](#тесты)
    - [Развёртывание](#развёртывание)
    - [Известные ограничения](#известные-ограничения)
    - [Участие в разработке](#участие-в-разработке)
    - [Безопасность](#безопасность)
    - [Третьи стороны и лицензии](#третьи-стороны-и-лицензии)
    - [Лицензия](#лицензия)

### Features

- **Calculator.** Enter object parameters (location, purpose, building class, number of floors, area, parking, finishing, start date) and get timelines and cost.
- **Inflation markup.** Itemised calculation over a monthly inflation table: the budget is split into three periods 30% / 40% / 30%, each month applies its own rate.
- **Social load.** Number of preschool (DOO) and school (SOSH) places by norms and their cost.
- **Ground parking.** Cost of parking spaces by city rate.
- **Cost items.** Configurable percentage breakdown of construction cost (items and sub-items).
- **Finishing.** White Box, rough, fine, and designer — with rates by city and purpose.
- **Django Admin back office.** Fully editable reference data, cost table as a pivot grid, inline editing of lists.
- **Excel import/export.** Monthly inflation — upload from `.xlsx` with validation and rollback, one-click download. Cost rate — pivot page: import from `.xlsx` with preview and grid export.
- **Editable pivot table.** Grid "city × class": search by city, add a missing city on the fly, edit cells with a single save request.
- **Inline editing of reference data.** Prices, percentages, order and active flag are edited directly in admin lists, without opening a card.
- **Dark theme and PWA.** Theme switcher with the choice saved in `localStorage`; favicon and `site.webmanifest` — the service installs as an app.

### Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.13 |
| Framework | Django | `>=5.2,<6.0` |
| Excel | openpyxl | `3.1.5` |
| WSGI server | Gunicorn | `23.0.0` |
| Static | WhiteNoise | `6.8.2` |
| DB (default) | SQLite | built-in |
| DB (optional) | PostgreSQL | via `DATABASE_URL` |
| Configuration | python-decouple | `3.8` |
| `DATABASE_URL` parsing | dj-database-url | `2.3.0` |
| Frontend | Django templates + vanilla JS/CSS | — |
| Dropdowns | Tom Select (vendored) | `2.4.3` |
| Fonts | SB Sans Text / SB Sans Display (vendored, ParaType) | — |
| Containerisation | Docker, Docker Compose | image `python:3.13-slim` |
| Web server | nginx | reverse proxy + TLS Let's Encrypt |

Dependencies are pinned in [`requirements.txt`](requirements.txt).

### Quick start

Python 3.13 (or 3.12+) is required.

```bash
git clone <repo-url>
cd construction-platform-refresh

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

mkdir -p data                    # SQLite directory; not stored in git
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Calculator: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

Demo reference data (23 building classes, 29 cities, cost rates, 128 months of inflation, norms and cost items) is loaded automatically by migrations `0004_seed_demo`, `0005_social_norms`, `0007_seed_costitem` and `0009_seed_monthly_inflation` — no separate `loaddata` is required.

> `python manage.py loaddata calc/fixtures/demo.json` on a fresh database **fails** with `UNIQUE constraint failed: calc_buildingclass.name`: the `calc/fixtures/demo.json` reference file duplicates seed migration data. The file is kept as an export source usable only on an empty database after `migrate` without seeds (see "Known limitations").

The default database is SQLite at `data/db.sqlite3`. The `data/` directory is absent from the repository (it is in `.gitignore`), so it must be created before the first `migrate` — otherwise Django crashes with `unable to open database file`.

### Running in Docker

```bash
cp .env.example .env      # fill in SECRET_KEY, DEBUG=False, ALLOWED_HOSTS
docker compose up -d --build
```

The `calcsite-web` container listens on `127.0.0.1:8080`; it is published externally only through the system nginx. On start, `entrypoint.sh` runs `migrate`, `collectstatic`, and launches Gunicorn (3 workers, 60 s timeout). The `./data` directory is mounted as a volume — the SQLite database survives rebuilds.

> The code is copied into the image at build time (`COPY . .`), so after editing sources you need `docker compose up -d --build web`, not `docker restart`.

### Environment variables

Read via `python-decouple` from `.env` or environment variables. Template — [`.env.example`](.env.example).

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-me` | Django key. A custom one is mandatory in production. |
| `DEBUG` | `True` | Debug mode. In production — `False`. |
| `ALLOWED_HOSTS` | `*` | Comma-separated host list. |
| `CSRF_TRUSTED_ORIGINS` | empty | Comma-separated origin list (with scheme). |
| `DATABASE_URL` | `sqlite:///<BASE_DIR>/data/db.sqlite3` | Database connection string. |

With `DEBUG=False`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY` are enabled automatically, and the `X-Forwarded-Proto` header is honoured.

### Project structure

```
.
├── manage.py
├── requirements.txt
├── Dockerfile               # python:3.13-slim
├── docker-compose.yml       # web service
├── entrypoint.sh            # migrate → collectstatic → gunicorn
├── deploy.sh                # git pull → docker compose up -d --build
├── .env.example
├── LICENSE                # MIT
├── dump.md                # source dump for AI assistants (outdated, see limitations)
├── scripts/dump.sh        # dump.md generator
├── nginx/
│   └── construction-platform.conf   # HTTP→HTTPS, TLS, proxy to :8080
├── expertise/               # project configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── calc/                    # the only application
    ├── models.py            # reference data and rates
    ├── forms.py             # calculator form
    ├── views.py             # calculator page, API helpers
    ├── views_admin.py       # cost pivot page and its import
    ├── admin_views_inflation.py    # custom admin views for inflation
    ├── services.py          # calculation core
    ├── services_import.py          # cost import from Excel (pivot)
    ├── services_export.py          # cost export to Excel (pivot)
    ├── services_inflation_import.py # monthly inflation import from Excel
    ├── services_inflation_export.py # monthly inflation export to Excel
    ├── admin.py             # model registration and custom URLs
    ├── migrations/          # 0001…0011
    ├── fixtures/demo.json   # demo data
    ├── static/calc/         # app.css, app.js, cost_pivot.*, fonts, favicon
    ├── templates/calc/      # base.html, form.html, history.html, admin_*
    ├── templatetags/calc_format.py  # spaces filter: digit grouping with narrow space
    └── tests/               # 5 modules, 44 tests: inflation (import/export/precision) and cost
```

### Calculator: fields and result

The `/` page is the calculation form. All fields are mandatory unless noted.

| Field | Type | Constraints |
|---|---|---|
| Location | choice from city reference | — |
| Functional purpose | choice | determines the available classes |
| Building class | choice | list is filtered by purpose (AJAX) |
| Number of floors | integer | 1…200 |
| Total area, m² | decimal | ≥ 1, up to 2 decimals |
| Construction start date | date | defaults to today |
| Underground parking | flag | treated as a flag, cost is not calculated |
| Ground detached parking | flag | only enables the "Number of spaces" field |
| Number of spaces (ground) | integer | ≥ 0, default 0 |
| Consider finishing | flag | available only for purposes "Residential" and "Hotel" |
| Finishing type | radio | White Box / Rough / Fine / Designer |
| Designer finishing cost, ₽/m² | decimal | ≥ 0, only for the "Designer" type |

The result block shows: construction duration, base cost, inflation markup (in an expandable accordion — by month with rate and amount), apartment area, floor multiplier, finishing cost, DOO and SOSH places and cost, parking, and a cost-items table with the total by percentage and amount. Monetary values are output with the `spaces` filter: digit groups are separated by a narrow non-breaking space, the fractional part — by a comma.

The `/history/` page is a stub: the calculation log is not maintained yet.

### HTTP endpoints

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/` | calculator | public |
| GET | `/history/` | "History" page (stub) | public |
| GET | `/api/classes/<purpose_id>/` | building classes available for the purpose | public, JSON |
| GET | `/api/purpose-meta/<purpose_id>/` | purpose category, whether finishing is needed, area label | public, JSON; frontend does not call it — see limitations |
| GET | `/admin/` | Django Admin | staff |
| GET | `/admin/calc/monthlyinflation/import/` | inflation import form | `calc.change_monthlyinflation` |
| GET | `/admin/calc/monthlyinflation/export/` | inflation export to `.xlsx` | `calc.view_monthlyinflation` |
| GET | `/admin/calc/costrate/pivot/` | cost pivot table | staff |
| POST | `/admin/calc/costrate/pivot/save/` | save grid edits | staff |
| POST | `/admin/calc/costrate/pivot/add-city/` | create a city from the pivot page | staff |
| POST | `/admin/calc/costrate/pivot/import/preview/` | parse `.xlsx` and return a preview | staff |
| POST | `/admin/calc/costrate/pivot/import/apply/` | apply parsed data | staff |
| GET | `/admin/calc/costrate/pivot/export/` | cost export to `.xlsx` | staff |

JSON endpoints do not require authentication — they serve the public calculation form.

### Admin panel

| Section | Purpose |
|---|---|
| Cities | Locations; overrides for norms and finishing rates |
| Functional purposes | Purpose + apartment area share + available classes |
| Building classes | Economy / Comfort / Business / Premium |
| **Cost (table)** | Pivot grid "city × class": cell editing, adding a city, Excel import/export |
| Construction timelines | Months by area |
| Inflation | Active rate (archival model) |
| **Inflation (monthly)** | Month table for the inflation calculation, Excel import/export |
| Social norms | m²/place and cost of a DOO/SOSH place |
| Ground parking (rates) | ₽ per parking space by city |
| Calculation settings | Inflation adjustment coefficient, default norms and finishing |
| Construction cost items | Percentage breakdown of cost, items and sub-items |

In admin lists, columns with prices, percentages, order and the "active" flag are edited inline (`list_editable`) and saved with the "Save" button — no need to open a card. Cost items have inline sub-items right in the item card.

#### Cost table (pivot)

Section "Cost (table)" → button **📊 Open pivot table**.

The page `/admin/calc/costrate/pivot/` shows a grid "city × building class": a row — city, a column — class. Capabilities:

- **Search by city** — filters rows on the client, without reload.
- **Cell editing** — values are entered as text; `,` and `.` are accepted as separators; an empty value or `0` removes the rate. The "Save" button is enabled only when there are changes.
- **Add city** — creates a city and a row in the grid without leaving the page.
- **Excel import** — after selecting a file, a preview window opens with a summary (how many cells matched, how many cities and classes were not found) and three toggles: create missing cities, overwrite existing rates, delete rates where the file has empty or `0`. Application is a separate request after preview.
- **Excel export** — exports the current grid to `costrate_pivot_YYYY-MM-DD.xlsx`: header "CITY", then class names in page order, rows — cities in page order, missing cells stay empty. The first row and first column are frozen.

Import file format: first row — header (anything in the first cell, then class names), then rows "city + values by columns". City and class names are matched case-insensitively and with `ё` → `е` replacement; spaces in values are ignored.

### Excel import and export

#### Inflation (monthly)

In the list header — buttons **⬆ Import Excel** and **⬇ Export Excel**.

File format (first sheet):

| A | B |
|---|---|
| Month | Inflation |
| 1 | 0.0732001 |
| 2 | 0.0747 |

- **Column A** — month, integer ≥ 1.
- **Column B** — rate, number; `,` or `.` as decimal separator, spaces ignored.
- **Header** ("Month" / "Inflation") is optional: recognised and skipped.
- Rate precision — **7 decimals**, integer part — up to 2 digits (`99.9999999`).
- **The rate is rounded to 7 decimals** (ROUND_HALF_UP, "half up" rule). Excel stores numbers as binary doubles, so `0.17233` in a cell is physically `0.17232999999999998`; such values are not treated as errors, but normalised: `0.1723300`. Rounding is also applied to rows with greater precision: `0.07320015` → `0.0732002`, `0.07320011` → `0.0732001`.

Import rules:

- Import **upserts by month**: an existing month is updated, a new one is created.
- A duplicate month inside the file is an error with the row number.
- Import is **atomic**: an error in any row rolls back the whole operation, the message includes the row number and cause.
- The `.xlsx` extension, the fact that the file opens with the library, and size ≤ 5 MB are checked.
- Format errors are only values that do not fit even after rounding: more than 2 digits in the integer part (`123.4567890` → `123.4567890`; `99.99999999` → `100.0000000`). A value that rounds to zero (`0.00000004`) is rejected with the message "became 0".
- Requires the `calc.change_monthlyinflation` permission; on success the message "Created N, updated M" is shown.

The export returns a file sorted by month, `monthly_inflation_YYYYMMDD.xlsx`, with the number format `0.0000000` (the value can be summed and plotted). The exported file can be re-uploaded by import. Requires the `calc.view_monthlyinflation` permission.

#### Cost

Section "Cost (table)" → "Open pivot table" → "Import Excel". File: column A — city, then columns by building class. Import is preceded by a preview and lets you choose whether to create missing cities, overwrite existing rates, and delete zero values.

### Default settings

Section "Calculation settings" stores fallback values: they are used when a city has no override. The active set is the one with `is_active = True` — the first such set is used.

| Parameter | Default value |
|---|---|
| Inflation adjustment coefficient | `0.900` |
| Area norm per resident, m² | `30.00` |
| DOO norm per 1000 residents | `65.00` |
| SOSH norm per 1000 residents | `135.00` |
| White Box finishing, residential, ₽/m² | `15000.00` |
| White Box finishing, hotel, ₽/m² | `20000.00` |
| Rough finishing, residential, ₽/m² | `5000.00` |
| Rough finishing, hotel, ₽/m² | `6000.00` |
| Fine finishing, residential, ₽/m² | `25000.00` |
| Fine finishing, hotel, ₽/m² | `40000.00` |

If there is no "Calculation settings" record at all, `services.py` substitutes hard-coded constants: area norm `30.00`, DOO `65.00`, SOSH `135.00`, and adjustment coefficient `0.900`. The floor threshold for the multiplier (`30` floors → `1.25`) is defined only in code and is not editable from the admin.

### Calculation formulas

```
# Areas
apartments_area = total_area × apartments_area_ratio
rest_area       = total_area − apartments_area

# Floor multiplier
floor_multiplier = 1.25 if floors >= 30 else 1

# Base cost
base_cost = rest_area × price_per_sqm × floor_multiplier
          + apartments_area × (price_per_sqm + finish_rate)

# Inflation: 3 periods 30 % / 40 % / 30 %, duration from the timeline reference
inflation_amount = Σ (spend_month × rate_month)
construction_cost = base_cost + inflation_amount

# Social load
residents  = ceil(apartments_area / sqm_per_resident)
doo_seats  = ceil(residents × 0.001 × doo_per_1000)
sosh_seats = ceil(residents × 0.001 × sosh_per_1000)
doo_cost   = doo_seats  × price_per_seat
sosh_cost  = sosh_seats × price_per_seat

# Parking
ground_parking_cost = ground_parking_spaces × cost_per_space

# Cost items
amount = ceil(construction_cost × percent / 100)
```

Construction duration is interpolated from the "Construction timelines" reference (key — total area). Calculations are performed in `Decimal`; monetary values are rounded to kopecks, cost items — up (`ROUND_CEILING`).

### Migrations

| Migration | Content |
|---|---|
| `0001_initial` | base references: cities, purposes, classes, cost, timelines, inflation, social norms, parking, settings |
| `0002_construction_duration_area` | timeline key switched to area |
| `0003_purpose_allowed_classes` | "purpose → available classes" relation |
| `0004_seed_demo` | demo references: 29 cities, 23 building classes, rates, timelines |
| `0005_social_norms` | demo social load norms |
| `0006_costitem` | construction cost items |
| `0007_seed_costitem` | demo cost items |
| `0008_monthly_inflation` | monthly inflation model |
| `0009_seed_monthly_inflation` | 128 months of inflation |
| `0010_finishing` | finishing: rates by city, defaults, `is_social` flag |
| `0011_monthly_inflation_rate_precision` | inflation rate precision `decimal_places` 4 → 7 |

Seed migrations are idempotent and fill demo data automatically on the first `migrate`. `0011` extends only the fractional part: the integer part stays at 2 digits, the ceiling — `99.9999999`. Existing 4-decimal values are preserved unchanged.

### Tests

```bash
python manage.py collectstatic --noinput     # mandatory before tests, see below
python manage.py test calc.tests -v 2
```

44 tests in 5 modules:

| Module | Tests | Coverage |
|---|---|---|
| `test_monthlyinflation_import` | 11 | header optional, upsert, duplicate months, rollback, permissions, broken file, extension |
| `test_monthlyinflation_export` | 7 | sorting, empty table, headers, round-trip, permissions |
| `test_monthlyinflation_precision` | 11 | 7 decimals, format boundaries, compatibility with 4-decimal data |
| `test_costrate_pivot_import` | 6 | preserving trailing zeros, preview, application |
| `test_costrate_pivot_export` | 9 | city and class order, empty cells, export headers |

> `collectstatic` before tests is required because of `CompressedManifestStaticFilesStorage`: without a manifest, tests that render admin pages fail with `Missing staticfiles manifest entry`. This applies to any admin tests in the project.

### Deployment

1. Clone the repository and fill in `.env` (mandatory: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`).
2. Place the config [`nginx/construction-platform.conf`](nginx/construction-platform.conf) into `/etc/nginx/sites-enabled/` and issue a Let's Encrypt certificate for your domain.
3. Bring the application up:

```bash
docker compose up -d --build
# or update an existing deployment:
sh deploy.sh
```

nginx terminates TLS and proxies to `127.0.0.1:8080`; the request body size limit is 20 MB. Migrations and `collectstatic` run automatically on container start.

### Known limitations

- `python manage.py makemigrations --check` shows a discrepancy on `calc.CostItem.id`: migration `0006_costitem` declares `id` as `AutoField`, while settings use `DEFAULT_AUTO_FIELD = BigAutoField`. The discrepancy is pre-existing (reproduced on a clean `main`) and unrelated to current functionality; it is deliberately not "fixed" by a migration.
- The fixture `calc/fixtures/demo.json` is incompatible with seed migrations: building class and city references are already created by migration `0004_seed_demo`, so `loaddata` fails with `UNIQUE constraint failed: calc_buildingclass.name`. Current demo data is shipped by migrations; the fixture is not used.
- The exported filename is intentionally ASCII-only, so that `Content-Disposition` does not require RFC 5987.
- Underground parking is treated as a flag and is not separately costed.
- Calculation history is not stored: the "History" page is a stub.
- The calculator has no authentication — the calculation is open to everyone; restrictions exist only in the admin.
- The endpoint `/api/purpose-meta/<purpose_id>/` is implemented and available, but the frontend does not call it: the area label and finishing availability come from server-side rendering (`data-category` attributes on purpose options). Effectively dead code.
- The flag "Ground detached parking" is not passed to `calculate()`: it only requires the number of spaces to be filled in. The cost is calculated solely as `spaces × city rate`.
- There is no underground parking rate: the flag is treated as a feature, cost is not estimated.
- `dump.md` is a snapshot of sources (`services.py`, `views.py`, `models.py`) for feeding AI assistants. It has not been updated since June 2026 and does not know about models and modules added later; only the sources themselves are current. In `.gitignore`, there is a typo for it (`dumb.md` instead of `dump.md`).
- `calc/fixtures/demo.json` remains in the repository although it is unused: demo data is placed by migration `0004_seed_demo`. The file diverges from it in primary keys.

### Contributing

1. Fork and create a branch from `main`: `git checkout -b feature/short-description`.
2. Code style follows existing files: double quotes, `snake_case`, comments in Russian, calculation logic in `services*.py`, views — thin.
3. New dependencies — only by agreement, with a pinned version in `requirements.txt`.
4. Migrations — `python manage.py makemigrations`; check `python manage.py check` with no new errors.
5. Tests — `python manage.py test calc.tests` green; new tests for new functionality.
6. Pull request with a description: what changed, why, how it was tested.

### Security

Secrets are not stored in the repository — only in `.env` (in `.gitignore` and `.dockerignore`). Do not publish `SECRET_KEY`, `.env` contents, DB credentials, or data dumps. Report vulnerabilities privately to the repository maintainer, without opening a public issue.

### Third parties and licenses

The repository contains vendored components, each under its own license — it is not covered by the project's license:

| Component | Where | License |
|---|---|---|
| Tom Select 2.4.3 | `calc/static/calc/vendor/` | Apache License 2.0 (header preserved in files) |
| Fonts SB Sans Text / SB Sans Display | `calc/static/calc/fonts/` | © ParaType, 2019, "All rights reserved" — see warning below |
| Favicon and PWA icons | `calc/static/calc/*.png`, `favicon.*` | Generated with nano banana (Google Gemini); released under the MIT license as part of this project |

> **The fonts require attention when publishing.** The file headers say `Copyright © ParaType, 2019. All rights reserved.` — this is not a free license. To distribute the project under MIT, you need either explicit permission from the copyright holder for the fonts, or replace them with open-licensed fonts (e.g., SIL OFL). The fonts are the only component that formally conflicts with MIT for the entire repository.

### License

The project is released under the [MIT](LICENSE) license. You are free to use, modify, and distribute the code, including for commercial purposes, provided that the license text and copyright notice are preserved.

[⬆ Back to top](#express-construction-expertise)

---

<a id="-русская-версия"></a>

## 🇷🇺 Русская версия

Веб-сервис предварительной оценки стоимости и сроков строительства. Пользователь вводит параметры объекта — получает расчёт сроков, себестоимости, инфляционного удорожания и социальной нагрузки. Все справочники и тарифы редактируются через Django Admin, большие таблицы загружаются и выгружаются файлами Excel.

Проект распространяется под лицензией [MIT](LICENSE).

### Содержание

- [Express Construction Expertise](#express-construction-expertise)
  - [🇬🇧 English version](#-english-version)
    - [Contents](#contents)
    - [Features](#features)
    - [Stack](#stack)
    - [Quick start](#quick-start)
    - [Running in Docker](#running-in-docker)
    - [Environment variables](#environment-variables)
    - [Project structure](#project-structure)
    - [Calculator: fields and result](#calculator-fields-and-result)
    - [HTTP endpoints](#http-endpoints)
    - [Admin panel](#admin-panel)
      - [Cost table (pivot)](#cost-table-pivot)
    - [Excel import and export](#excel-import-and-export)
      - [Inflation (monthly)](#inflation-monthly)
      - [Cost](#cost)
    - [Default settings](#default-settings)
    - [Calculation formulas](#calculation-formulas)
    - [Migrations](#migrations)
    - [Tests](#tests)
    - [Deployment](#deployment)
    - [Known limitations](#known-limitations)
    - [Contributing](#contributing)
    - [Security](#security)
    - [Third parties and licenses](#third-parties-and-licenses)
    - [License](#license)
  - [🇷🇺 Русская версия](#-русская-версия)
    - [Содержание](#содержание)
    - [Возможности](#возможности)
    - [Стек](#стек)
    - [Быстрый старт](#быстрый-старт)
    - [Запуск в Docker](#запуск-в-docker)
    - [Переменные окружения](#переменные-окружения)
    - [Структура проекта](#структура-проекта)
    - [Калькулятор: поля и результат](#калькулятор-поля-и-результат)
    - [HTTP-эндпоинты](#http-эндпоинты)
    - [Админка](#админка)
      - [Таблица себестоимости (pivot)](#таблица-себестоимости-pivot)
    - [Импорт и экспорт Excel](#импорт-и-экспорт-excel)
      - [Инфляция (помесячно)](#инфляция-помесячно)
      - [Себестоимость](#себестоимость)
    - [Настройки по умолчанию](#настройки-по-умолчанию)
    - [Формулы расчёта](#формулы-расчёта)
    - [Миграции](#миграции)
    - [Тесты](#тесты)
    - [Развёртывание](#развёртывание)
    - [Известные ограничения](#известные-ограничения)
    - [Участие в разработке](#участие-в-разработке)
    - [Безопасность](#безопасность)
    - [Третьи стороны и лицензии](#третьи-стороны-и-лицензии)
    - [Лицензия](#лицензия)

### Возможности

- **Калькулятор.** Ввод параметров объекта (локация, назначение, класс строительства, этажность, площадь, парковка, отделка, дата начала) и расчёт сроков и стоимости.
- **Инфляционное удорожание.** Постатейный расчёт по помесячной таблице инфляции: бюджет делится на три периода 30 % / 40 % / 30 %, каждый месяц применяется своя ставка.
- **Социальная нагрузка.** Количество мест ДОО и СОШ по нормативам и их стоимость.
- **Наземный паркинг.** Стоимость машиномест по тарифу города.
- **Статьи расходов.** Настраиваемый процентный разрез стоимости строительства (статьи и подстатьи).
- **Отделка.** White Box, черновая, чистовая и дизайнерская — с тарифами по городам и назначениям.
- **Админка на Django Admin.** Полностью редактируемые справочники, таблица себестоимости в виде pivot-сетки, inline-редактирование списков.
- **Импорт/экспорт Excel.** Помесячная инфляция — загрузка из `.xlsx` с валидацией и откатом, выгрузка одним кликом. Себестоимость — pivot-страница: импорт из `.xlsx` с превью и выгрузка сетки.
- **Редактируемая pivot-таблица.** Сетка «город × класс»: поиск по городу, добавление отсутствующего города на лету, правка ячеек с сохранением одним запросом.
- **Инлайн-редактирование справочников.** Цены, проценты, порядок и активность правятся прямо в списках админки, без открытия карточки.
- **Тёмная тема и PWA.** Переключатель темы с сохранением выбора в `localStorage`; favicon и `site.webmanifest` — сервис устанавливается как приложение.

### Стек

| Слой | Технология | Версия |
|---|---|---|
| Язык | Python | 3.13 |
| Фреймворк | Django | `>=5.2,<6.0` |
| Excel | openpyxl | `3.1.5` |
| WSGI-сервер | Gunicorn | `23.0.0` |
| Статика | WhiteNoise | `6.8.2` |
| БД (по умолчанию) | SQLite | встроенный |
| БД (опционально) | PostgreSQL | через `DATABASE_URL` |
| Конфигурация | python-decouple | `3.8` |
| Парсинг `DATABASE_URL` | dj-database-url | `2.3.0` |
| Frontend | Django templates + ванильный JS/CSS | — |
| Выпадающие списки | Tom Select (вендорен) | `2.4.3` |
| Шрифты | SB Sans Text / SB Sans Display (вендорены, ParaType) | — |
| Контейнеризация | Docker, Docker Compose | образ `python:3.13-slim` |
| Веб-сервер | nginx | reverse proxy + TLS Let's Encrypt |

Зависимости зафиксированы в [`requirements.txt`](requirements.txt).

### Быстрый старт

Требуется Python 3.13 (или 3.12+).

```bash
git clone <URL-репозитория>
cd construction-platform-refresh

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

mkdir -p data                    # каталог под SQLite; в git не хранится
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Калькулятор: http://127.0.0.1:8000/
- Админка: http://127.0.0.1:8000/admin/

Демо-справочники (23 класса строительства, 29 городов, тарифы себестоимости, 128 месяцев инфляции, нормативы и статьи расходов) загружаются миграциями `0004_seed_demo`, `0005_social_norms`, `0007_seed_costitem` и `0009_seed_monthly_inflation` автоматически — отдельный `loaddata` не нужен.

> `python manage.py loaddata calc/fixtures/demo.json` на свежей базе **завершится ошибкой** (`UNIQUE constraint failed: calc_buildingclass.name`): справочник `calc/fixtures/demo.json` дублирует данные сид-миграций. Файл оставлен как источник выгрузки, пригодный только для пустой базы после `migrate` без сидов (см. «Известные ограничения»).

База по умолчанию — SQLite в `data/db.sqlite3`. Каталог `data/` в репозитории отсутствует (он в `.gitignore`), поэтому его нужно создать перед первым `migrate` — иначе Django упадёт с `unable to open database file`.

### Запуск в Docker

```bash
cp .env.example .env      # заполнить SECRET_KEY, DEBUG=False, ALLOWED_HOSTS
docker compose up -d --build
```

Контейнер `calcsite-web` слушает `127.0.0.1:8080`, наружу публикуется только через системный nginx. При старте `entrypoint.sh` последовательно выполняет `migrate`, `collectstatic` и запускает Gunicorn (3 воркера, таймаут 60 с). Каталог `./data` смонтирован как volume — база SQLite сохраняется между пересборками.

> Код копируется в образ на этапе сборки (`COPY . .`), поэтому после изменения исходников нужен `docker compose up -d --build web`, а не `docker restart`.

### Переменные окружения

Читаются через `python-decouple` из `.env` или переменных окружения. Шаблон — [`.env.example`](.env.example).

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-me` | Ключ Django. В продакшене обязателен свой. |
| `DEBUG` | `True` | Режим отладки. В продакшене — `False`. |
| `ALLOWED_HOSTS` | `*` | Список хостов через запятую. |
| `CSRF_TRUSTED_ORIGINS` | пусто | Список origin'ов через запятую (со схемой). |
| `DATABASE_URL` | `sqlite:///<BASE_DIR>/data/db.sqlite3` | Строка подключения к БД. |

При `DEBUG=False` автоматически включаются `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY` и учитывается заголовок `X-Forwarded-Proto`.

### Структура проекта

```
.
├── manage.py
├── requirements.txt
├── Dockerfile               # python:3.13-slim
├── docker-compose.yml       # сервис web
├── entrypoint.sh            # migrate → collectstatic → gunicorn
├── deploy.sh                # git pull → docker compose up -d --build
├── .env.example
├── LICENSE                # MIT
├── dump.md                # выгрузка исходников для ИИ-ассистентов (устарела, см. ограничения)
├── scripts/dump.sh        # генератор dump.md
├── nginx/
│   └── construction-platform.conf   # HTTP→HTTPS, TLS, proxy на :8080
├── expertise/               # конфигурация проекта
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── calc/                    # единственное приложение
    ├── models.py            # справочники и тарифы
    ├── forms.py             # форма калькулятора
    ├── views.py             # страница калькулятора, API-хелперы
    ├── views_admin.py       # pivot-страница себестоимости, её импорт
    ├── admin_views_inflation.py    # custom views админки инфляции
    ├── services.py          # ядро расчёта
    ├── services_import.py          # импорт себестоимости из Excel (pivot)
    ├── services_export.py          # выгрузка себестоимости в Excel (pivot)
    ├── services_inflation_import.py # импорт помесячной инфляции из Excel
    ├── services_inflation_export.py # выгрузка помесячной инфляции в Excel
    ├── admin.py             # регистрация моделей и кастомных URL
    ├── migrations/          # 0001…0011
    ├── fixtures/demo.json   # демо-данные
    ├── static/calc/         # app.css, app.js, cost_pivot.*, шрифты, favicon
    ├── templates/calc/      # base.html, form.html, history.html, admin_*
    ├── templatetags/calc_format.py  # фильтр spaces: разряды через узкий пробел
    └── tests/               # 5 модулей, 44 теста: инфляция (импорт/экспорт/точность) и себестоимость
```

### Калькулятор: поля и результат

Страница `/` — форма расчёта. Все поля обязательны, кроме отмеченных.

| Поле | Тип | Ограничения |
|---|---|---|
| Локация | выбор из справочника городов | — |
| Функциональное назначение | выбор | определяет набор доступных классов |
| Класс строительства | выбор | список фильтруется по назначению (AJAX) |
| Количество этажей | целое | 1…200 |
| Общая площадь, м² | десятичное | ≥ 1, до 2 знаков |
| Дата начала строительства | дата | по умолчанию — сегодня |
| Подземный паркинг | флаг | учитывается как признак, стоимость не считается |
| Наземный отдельностоящий паркинг | флаг | только включает поле «Количество машиномест» |
| Количество машиномест (наземный) | целое | ≥ 0, по умолчанию 0 |
| Учитывать отделку | флаг | доступно только для назначений «Жилое» и «Гостиница» |
| Тип отделки | радио | White Box / Черновая / Чистовая / Дизайнерская |
| Стоимость дизайнерской отделки, ₽/м² | десятичное | ≥ 0, только для типа «Дизайнерская» |

Блок результата показывает: срок строительства, базовую стоимость, инфляционное удорожание (в раскрывающемся аккордеоне — по месяцам с ставкой и суммой), площадь квартир, множитель этажности, стоимость отделки, места и стоимость ДОО и СОШ, паркинг и таблицу статей расходов с итогом по проценту и сумме. Денежные значения выводятся фильтром `spaces`: разряды разделяются узким неразрывным пробелом, дробная часть — запятой.

Страница `/history/` — заглушка: журнал расчётов пока не ведётся.

### HTTP-эндпоинты

| Метод | URL | Назначение | Доступ |
|---|---|---|---|
| GET | `/` | калькулятор | публичный |
| GET | `/history/` | страница «История» (заглушка) | публичный |
| GET | `/api/classes/<purpose_id>/` | классы строительства, доступные для назначения | публичный, JSON |
| GET | `/api/purpose-meta/<purpose_id>/` | категория назначения, нужна ли отделка, подпись площади | публичный, JSON; фронтенд его не запрашивает — см. ограничения |
| GET | `/admin/` | Django Admin | staff |
| GET | `/admin/calc/monthlyinflation/import/` | форма импорта инфляции | `calc.change_monthlyinflation` |
| GET | `/admin/calc/monthlyinflation/export/` | выгрузка инфляции в `.xlsx` | `calc.view_monthlyinflation` |
| GET | `/admin/calc/costrate/pivot/` | pivot-таблица себестоимости | staff |
| POST | `/admin/calc/costrate/pivot/save/` | сохранить правки сетки | staff |
| POST | `/admin/calc/costrate/pivot/add-city/` | создать город из pivot-страницы | staff |
| POST | `/admin/calc/costrate/pivot/import/preview/` | разобрать `.xlsx` и вернуть превью | staff |
| POST | `/admin/calc/costrate/pivot/import/apply/` | применить разобранные данные | staff |
| GET | `/admin/calc/costrate/pivot/export/` | выгрузка себестоимости в `.xlsx` | staff |

JSON-эндпоинты не требуют аутентификации — они обслуживают публичную форму расчёта.

### Админка

| Раздел | Назначение |
|---|---|
| Города | Локации; переопределения нормативов и тарифов отделки |
| Функциональные назначения | Назначение + доля площади квартир + доступные классы |
| Классы строительства | Эконом / Комфорт / Бизнес / Премиум |
| **Себестоимость (таблица)** | pivot-сетка «город × класс»: правка ячеек, добавление города, импорт и экспорт Excel |
| Сроки строительства | Месяцы по площади |
| Инфляция | Активная ставка (архивная модель) |
| **Инфляция (помесячно)** | Таблица месяцев для инфляционного расчёта, импорт/экспорт Excel |
| Нормативы социальки | м²/место и стоимость места ДОО/СОШ |
| Наземный паркинг (тарифы) | ₽ за машиноместо по городу |
| Настройки расчёта | Коэф. очистки от инфляции, нормативы и отделка по умолчанию |
| Статьи расходов на строительство | Процентный разрез стоимости, статьи и подстатьи |

В списках админки колонки с ценами, процентами, порядком и признаком «активна» редактируются инлайн (`list_editable`) и сохраняются кнопкой «Сохранить» — открывать карточку не нужно. У статей расходов есть inline-подстатьи прямо в карточке статьи.

#### Таблица себестоимости (pivot)

Раздел «Себестоимость (таблица)» → кнопка **📊 Открыть таблицу-pivot**.

Страница `/admin/calc/costrate/pivot/` показывает сетку «город × класс строительства»: строка — город, столбец — класс. Возможности:

- **Поиск по городу** — фильтрует строки на клиенте, без перезагрузки.
- **Правка ячеек** — значения вводятся как текст, допустимы `,` и `.` как разделитель; пустое значение или `0` удаляет тариф. Кнопка «Сохранить» активна, только когда есть изменения.
- **Добавить город** — создаёт город и строку в сетке, не уходя со страницы.
- **Импорт Excel** — после выбора файла открывается окно превью со сводкой (сколько ячеек сопоставлено, сколько городов и классов не найдено) и тремя переключателями: создавать отсутствующие города, перезаписывать существующие тарифы, удалять тарифы там, где в файле пусто или `0`. Применение — отдельным запросом после проверки превью.
- **Экспорт Excel** — выгружает текущую сетку в `costrate_pivot_ГГГГ-ММ-ДД.xlsx`: заголовок «ГОРОД», далее названия классов в порядке страницы, строки — города в порядке страницы, отсутствующие ячейки остаются пустыми. Закреплена первая строка и первый столбец.

Формат файла для импорта: первая строка — заголовок (в первой ячейке — что угодно, далее названия классов), далее строки «город + значения по колонкам». Названия городов и классов сопоставляются без учёта регистра и с заменой `ё` → `е`; пробелы в значениях игнорируются.

### Импорт и экспорт Excel

#### Инфляция (помесячно)

В шапке списка — кнопки **⬆ Импорт Excel** и **⬇ Экспорт Excel**.

Формат файла (первый лист):

| A | B |
|---|---|
| Месяц | Инфляция |
| 1 | 0,0732001 |
| 2 | 0,0747 |

- **Колонка A** — месяц, целое число ≥ 1.
- **Колонка B** — ставка, число; разделитель дробной части — `,` или `.`, пробелы игнорируются.
- **Шапка** («Месяц» / «Инфляция») опциональна: распознаётся и пропускается.
- Точность ставки — **7 знаков** после запятой, целая часть — до 2 знаков (`99.9999999`).
- **Ставка округляется до 7 знаков** (ROUND_HALF_UP, правило «половина вверх»). Excel хранит числа как двоичные double, поэтому `0,17233` в ячейке физически равно `0,17232999999999998`; такие значения не считаются ошибкой, а нормализуются: `0,1723300`. Округление применяется и к строкам с большей точностью: `0,07320015` → `0,0732002`, `0,07320011` → `0,0732001`.

Правила импорта:

- Импорт **upsert по месяцу**: существующий месяц обновляется, новый создаётся.
- Дубликат месяца внутри файла — ошибка с указанием строки.
- Импорт **атомарен**: ошибка любой строки откатывает всю операцию, в сообщении — номер строки и причина.
- Проверяется расширение `.xlsx`, факт открытия файла библиотекой и размер ≤ 5 МБ.
- Ошибкой формата остаются только значения, которые не влезают и после округления: более 2 цифр в целой части (`123.4567890` → `123.4567890`; `99.99999999` → `100.0000000`). Значение, которое после округления обращается в ноль (`0.00000004`), отвергается с сообщением «получился 0».
- Требуется право `calc.change_monthlyinflation`; по успеху выводится «Создано N, обновлено M».

Экспорт отдаёт отсортированный по месяцу файл `monthly_inflation_ГГГГММДД.xlsx` с числовым форматом `0.0000000` (значение можно суммировать и строить по нему графики). Экспортированный файл пригоден для обратной загрузки импортом. Требуется право `calc.view_monthlyinflation`.

#### Себестоимость

Раздел «Себестоимость (таблица)» → «Открыть таблицу-pivot» → «Импорт Excel». Файл: колонка A — город, далее колонки по классам строительства. Импорт предваряется превью и позволяет выбрать, создавать ли отсутствующие города, перезаписывать ли существующие тарифы и удалять ли нулевые значения.

### Настройки по умолчанию

Раздел «Настройки расчёта» хранит резервные значения: они применяются, когда у города не задано своё переопределение. Активным считается набор с `is_active = True` — используется первый такой.

| Параметр | Значение по умолчанию |
|---|---|
| Коэф. очистки от инфляции | `0.900` |
| Норма площади на жителя, м² | `30.00` |
| Норматив ДОО на 1000 жителей | `65.00` |
| Норматив СОШ на 1000 жителей | `135.00` |
| Отделка White Box, жилое, ₽/м² | `15000.00` |
| Отделка White Box, гостиница, ₽/м² | `20000.00` |
| Отделка черновая, жилое, ₽/м² | `5000.00` |
| Отделка черновая, гостиница, ₽/м² | `6000.00` |
| Отделка чистовая, жилое, ₽/м² | `25000.00` |
| Отделка чистовая, гостиница, ₽/м² | `40000.00` |

Если записи «Настройки расчёта» нет вовсе, `services.py` подставляет жёсткие константы: норма площади `30.00`, ДОО `65.00`, СОШ `135.00` и коэффициент очистки `0.900`. Порог этажности для множителя (`30` этажей → `1.25`) задан только в коде и не редактируется из админки.

### Формулы расчёта

```
# Площади
apartments_area = total_area × apartments_area_ratio
rest_area       = total_area − apartments_area

# Множитель этажности
floor_multiplier = 1.25 при floors ≥ 30, иначе 1

# Базовая стоимость
base_cost = rest_area × price_per_sqm × floor_multiplier
          + apartments_area × (price_per_sqm + finish_rate)

# Инфляция: 3 периода 30 % / 40 % / 30 %, длительность — из справочника сроков
inflation_amount = Σ (spend_месяца × rate_месяца)
construction_cost = base_cost + inflation_amount

# Социальная нагрузка
residents  = ceil(apartments_area / sqm_per_resident)
doo_seats  = ceil(residents × 0.001 × doo_per_1000)
sosh_seats = ceil(residents × 0.001 × sosh_per_1000)
doo_cost   = doo_seats  × price_per_seat
sosh_cost  = sosh_seats × price_per_seat

# Паркинг
ground_parking_cost = ground_parking_spaces × cost_per_space

# Статьи расходов
amount = ceil(construction_cost × percent / 100)
```

Срок строительства интерполируется по справочнику «Сроки строительства» (ключ — общая площадь). Расчёт ведётся в `Decimal`; денежные величины округляются до копеек, статьи расходов — вверх (`ROUND_CEILING`).

### Миграции

| Миграция | Содержимое |
|---|---|
| `0001_initial` | базовые справочники: города, назначения, классы, себестоимость, сроки, инфляция, соцнормы, паркинг, настройки |
| `0002_construction_duration_area` | ключ сроков переведён на площадь |
| `0003_purpose_allowed_classes` | связь «назначение → доступные классы» |
| `0004_seed_demo` | демо-справочники: 29 городов, 23 класса строительства, тарифы, сроки |
| `0005_social_norms` | демо-нормативы социальной нагрузки |
| `0006_costitem` | статьи расходов на строительство |
| `0007_seed_costitem` | демо-статьи расходов |
| `0008_monthly_inflation` | модель помесячной инфляции |
| `0009_seed_monthly_inflation` | 128 месяцев инфляции |
| `0010_finishing` | отделка: тарифы по городам, дефолты, флаг `is_social` |
| `0011_monthly_inflation_rate_precision` | точность ставки инфляции `decimal_places` 4 → 7 |

Сид-миграции идемпотентны и заполняют демо-данные автоматически при первом `migrate`. `0011` расширяет только дробную часть: целая часть остаётся 2 знака, потолок — `99.9999999`. Существующие 4-значные значения сохраняются без изменений.

### Тесты

```bash
python manage.py collectstatic --noinput     # обязательно перед тестами, см. ниже
python manage.py test calc.tests -v 2
```

44 теста в 5 модулях:

| Модуль | Тестов | Покрытие |
|---|---|---|
| `test_monthlyinflation_import` | 11 | шапка опциональна, upsert, дубли месяца, откат, права, битый файл, расширение |
| `test_monthlyinflation_export` | 7 | сортировка, пустая таблица, заголовки, round-trip, права |
| `test_monthlyinflation_precision` | 11 | 7 знаков, границы формата, совместимость с 4-значными данными |
| `test_costrate_pivot_import` | 6 | сохранение конечных нулей, превью, применение |
| `test_costrate_pivot_export` | 9 | порядок городов и классов, пустые ячейки, заголовки выгрузки |

> `collectstatic` перед тестами нужен из-за `CompressedManifestStaticFilesStorage`: без манифеста тесты, рендерящие страницы админки, падают на `Missing staticfiles manifest entry`. Это относится к любым admin-тестам в проекте.

### Развёртывание

1. Склонировать репозиторий и заполнить `.env` (обязательно `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`).
2. Положить конфиг [`nginx/construction-platform.conf`](nginx/construction-platform.conf) в `/etc/nginx/sites-enabled/` и выпустить сертификат Let's Encrypt для своего домена.
3. Поднять приложение:

```bash
docker compose up -d --build
# или обновление существующего деплоя:
sh deploy.sh
```

nginx терминирует TLS и проксирует на `127.0.0.1:8080`; лимит размера тела запроса — 20 МБ. Миграции и `collectstatic` выполняются автоматически при старте контейнера.

### Известные ограничения

- `python manage.py makemigrations --check` показывает расхождение по полю `calc.CostItem.id`: миграция `0006_costitem` объявляет `id` как `AutoField`, тогда как в настройках `DEFAULT_AUTO_FIELD = BigAutoField`. Расхождение предсуществующее (воспроизводится на чистом `main`) и к текущей функциональности не относится; осознанно не «лечится» миграцией.
- Фикстура `calc/fixtures/demo.json` несовместима с сид-миграциями: справочники классов строительства и городов уже созданы миграцией `0004_seed_demo`, поэтому `loaddata` падает на `UNIQUE constraint failed: calc_buildingclass.name`. Актуальные демо-данные поставляются миграциями; фикстуру не используем.
- Имя выгружаемого файла — только ASCII намеренно, чтобы `Content-Disposition` не требовал RFC 5987.
- Подземный паркинг учитывается как флаг и отдельной стоимостью не оценён.
- Хранение истории расчётов не реализовано: страница «История» — заглушка.
- Аутентификация калькулятора не предусмотрена — расчёт открыт всем, ограничения только в админке.
- Эндпоинт `/api/purpose-meta/<purpose_id>/` реализован и доступен, но фронтенд его не вызывает: подпись площади и доступность отделки приходят из серверного рендера (атрибуты `data-category` на опциях назначения). Фактически мёртвый код.
- Флаг «Наземный отдельностоящий паркинг» не передаётся в `calculate()`: он только требует заполнить количество машиномест. Стоимость считается исключительно как `машиноместа × тариф города`.
- Тариф на подземный паркинг отсутствует: флаг учитывается как признак, стоимость не оценивается.
- `dump.md` — снимок исходников (`services.py`, `views.py`, `models.py`) для подачи ИИ-ассистентам. Он не обновляется с июня 2026 и не знает о моделях и модулях, добавленных позже; актуальны только сами исходники. В `.gitignore` для него опечатка (`dumb.md` вместо `dump.md`).
- `calc/fixtures/demo.json` остаётся в репозитории, хотя не используется: демо-данные ставит миграция `0004_seed_demo`. Файл расходится с ней по первичным ключам.

### Участие в разработке

1. Форк и ветка от `main`: `git checkout -b feature/краткое-описание`.
2. Стиль кода — по существующим файлам: двойные кавычки, `snake_case`, комментарии по-русски, логика расчётов — в `services*.py`, представления — тонкие.
3. Новые зависимости — только по согласованию, с фиксацией версии в `requirements.txt`.
4. Миграции — `python manage.py makemigrations`; проверка `python manage.py check` без новых ошибок.
5. Тесты — `python manage.py test calc.tests` зелёные; на новую функциональность — новые тесты.
6. Pull request с описанием: что изменено, зачем, как проверено.

### Безопасность

Секреты не хранятся в репозитории — только в `.env` (в `.gitignore` и `.dockerignore`). Не публикуйте `SECRET_KEY`, содержимое `.env`, доступы к БД и дампы данных. Об уязвимостях сообщайте приватно мейнтейнеру репозитория, не открывая публичный issue.

### Третьи стороны и лицензии

В репозитории лежат вендоренные компоненты, у каждого своя лицензия — она не покрывается лицензией проекта:

| Компонент | Где | Лицензия |
|---|---|---|
| Tom Select 2.4.3 | `calc/static/calc/vendor/` | Apache License 2.0 (заголовок сохранён в файлах) |
| Шрифты SB Sans Text / SB Sans Display | `calc/static/calc/fonts/` | © ParaType, 2019, «All rights reserved» — см. предупреждение ниже |
| Favicon и иконки PWA | `calc/static/calc/*.png`, `favicon.*` | Сгенерированы в nano banana (Google Gemini); распространяются под лицензией MIT в составе проекта |

> **Шрифты требуют внимания при публикации.** Заголовки файлов сообщают `Copyright © ParaType, 2019. All rights reserved.` — это не свободная лицензия. Для распространения проекта под MIT нужно либо получить на шрифты явное разрешение правообладателя, либо заменить их на шрифты с открытой лицензией (например, SIL OFL). Шрифты — единственный компонент, который формально конфликтует с MIT для всего репозитория.

### Лицензия

Проект распространяется под лицензией [MIT](LICENSE). Вы можете свободно использовать, изменять и распространять код, в том числе в коммерческих целях, при условии сохранения текста лицензии и уведомления об авторских правах.

[⬆ Наверх](#express-construction-expertise)