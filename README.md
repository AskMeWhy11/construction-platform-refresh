<<<<<<< HEAD
# Экспресс-стройэкспертиза

Мини-сервис: пользователь вводит параметры объекта → получает расчёт сроков, стоимости и социалки.
Все справочники (себестоимость, сроки, инфляция, нормативы, паркинг) редактируются через Django Admin.

## Запуск

```bash
python -m venv .venv
source .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py loaddata calc/fixtures/demo.json
python manage.py createsuperuser
python manage.py runserver
```

- Калькулятор: http://127.0.0.1:8000/
- Админка: http://127.0.0.1:8000/admin/

## Что редактируется в админке

| Раздел | Назначение |
|---|---|
| Города | Локации (выпадающий список в форме) |
| Функциональные назначения | + доля площади квартир |
| Классы строительства | Эконом / Комфорт / Бизнес / Премиум |
| **Себестоимость (таблица)** | ₽/м² по (город × назначение × класс) |
| Сроки строительства | Месяцы по (назначение × класс × этажность) |
| Инфляция | Активная ставка (напр. 0.0732) |
| Нормативы социалки | м²/место и стоимость места ДОО/СОШ |
| Наземный паркинг (тарифы) | ₽ за машиноместо по городу |
| Настройки расчёта | Коэф. очистки от инфляции (по умолч. 0.9) |

## Формулы

```
base       = total_area * price_per_sqm * clean_coef
inflation  = base * inflation_rate
cost_total = base + inflation

DOO_seats  = ceil(total_area / 65)
DOO_cost   = DOO_seats * cost_per_doo_seat
SOSH_seats = ceil(total_area / 50)
SOSH_cost  = SOSH_seats * cost_per_school_seat

parking_cost = ground_parking_spaces * cost_per_space (по городу)
```

## Загрузка реальной таблицы себестоимости

Варианты:
1. Через админку → раздел «Себестоимость» → «Добавить».
2. Заменить `calc/fixtures/demo.json` своими данными и `loaddata`.
3. (по запросу) добавить импорт из CSV/XLSX.
```

**Запуск:**
```bash
pip install -r requirements.txt && python manage.py migrate && python manage.py loaddata calc/fixtures/demo.json && python manage.py createsuperuser && python manage.py runserver
```

---

**Что готово:**
- Форма ввода со всеми 7 полями ТЗ.
- Расчёт по формулам ТЗ (срок, стоимость, инфляция, ДОО, СОШ, наземный паркинг, площадь квартир).
- Админка с редактируемыми таблицами: **себестоимость**, сроки, инфляция, нормативы соц., тарифы паркинга, настройки, справочники.
- Демо-фикстура для мгновенного старта.

**Что осталось / зависит от тебя:**
1. Дай реальную **таблицу себестоимости** (xlsx/csv) — заменю фикстуру или сделаю импорт-команду.
2. Если **подземный паркинг** должен иметь стоимость (₽/м² или ₽/мм) — скажи формулу, добавлю модель `UndergroundParkingRate` и расчёт.
3. Если сроки нужно считать иначе (по площади, а не этажам) — поменяю модель `ConstructionDuration`.
=======
# construction-platform-refresh
>>>>>>> 96b5717be76c8d0266414349650a45d1cf2b24de
