# Dump

## Tree

```
calc/static/calc/app.js
calc/static/calc/cost_pivot.js
calc/templates/calc/form.html
```

### `calc/static/calc/app.js`

```
// Тема
(function () {
    const KEY = "theme";
    const root = document.body;
    const saved = localStorage.getItem(KEY);
    if (saved === "dark") root.classList.add("theme-dark");

    const btn = document.querySelector("[data-theme-toggle]");
    if (btn) {
        const sync = () => {
            const dark = root.classList.contains("theme-dark");
            btn.textContent = dark ? "☀" : "☾";
            btn.setAttribute("aria-label", dark ? "Светлая тема" : "Тёмная тема");
        };
        sync();
        btn.addEventListener("click", () => {
            root.classList.toggle("theme-dark");
            localStorage.setItem(KEY, root.classList.contains("theme-dark") ? "dark" : "light");
            sync();
        });
    }
})();

// Зависимое поле «Машиноместа»
(function () {
    const trigger = document.querySelector('[name="ground_parking"]');
    const target = document.querySelector('[data-depends-on="ground_parking"]');
    if (!trigger || !target) return;
    const sync = () => target.classList.toggle("hidden", !trigger.checked);
    sync();
    trigger.addEventListener("change", sync);
})();

// Tom Select на всех селектах формы — устойчивая инициализация
(function () {
    // Маппинг placeholder-ов по name. Если name нет в карте — используется label поля.
    const PLACEHOLDERS = {
        city: "Выберите город",
        purpose: "Выберите назначение",
        building_class: "Выберите класс",
    };

    function getPlaceholder(el) {
        if (PLACEHOLDERS[el.name]) return PLACEHOLDERS[el.name];
        // fallback: попробуем подтянуть из <label>
        const id = el.id;
        if (id) {
            const label = document.querySelector(`label[for="${id}"]`);
            if (label) return "Выберите: " + label.textContent.trim().toLowerCase();
        }
        return "Выберите…";
    }

    function stripEmptyOption(el) {
        [...el.options].forEach((opt) => {
            if (opt.value === "") opt.remove();
        });
    }

    function initTomSelect() {
        if (typeof TomSelect === "undefined") {
            console.warn("[calc] TomSelect не загружен");
            return;
        }

        const selects = document.querySelectorAll("select.select, form select");
        console.log("[calc] Tom Select: найдено селектов =", selects.length);

        selects.forEach((el) => {
            if (el.tomselect) return;

            const placeholder = getPlaceholder(el);
            stripEmptyOption(el);

            new TomSelect(el, {
                create: false,
                allowEmptyOption: false,
                maxOptions: 500,
                placeholder: placeholder,
                controlInput: el.options.length > 6
                    ? '<input type="text" autocomplete="off" placeholder="Поиск…">'
                    : null,
                render: {
                    no_results: () => '<div class="no-results">Ничего не найдено</div>',
                    option: (data, escape) => `<div>${escape(data.text)}</div>`,
                },
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initTomSelect);
    } else {
        setTimeout(initTomSelect, 0);
    }
})();
```

### `calc/static/calc/cost_pivot.js`

```
(function () {
    const wrap = document.querySelector(".cp-wrap");
    if (!wrap) return;

    const SAVE_URL = wrap.dataset.saveUrl;
    const ADD_CITY_URL = wrap.dataset.addCityUrl;

    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

    const $search = document.getElementById("cp-search");
    const $tbody = document.getElementById("cp-tbody");
    const $saveBtn = document.getElementById("cp-save");
    const $reloadBtn = document.getElementById("cp-reload");
    const $addCityBtn = document.getElementById("cp-add-city");
    const $status = document.getElementById("cp-status");
    const $citiesCount = document.getElementById("cp-cities-count");

    // ---- Поиск ----
    $search.addEventListener("input", () => {
        const q = $search.value.trim().toLowerCase();
        let visible = 0;
        $tbody.querySelectorAll("tr").forEach(tr => {
            const name = tr.dataset.cityName || "";
            const show = !q || name.includes(q);
            tr.classList.toggle("cp-hidden", !show);
            if (show) visible++;
        });
        $citiesCount.textContent = visible;
    });

    // ---- Dirty tracking ----
    function normalize(v) {
        if (v === null || v === undefined) return "";
        return String(v).replace(",", ".").replace(/\s+/g, "").trim();
    }
    function isDirty(input) {
        return normalize(input.value) !== normalize(input.dataset.original);
    }
    function refreshSaveBtn() {
        const dirty = $tbody.querySelectorAll(".cp-cell.cp-dirty").length;
        $saveBtn.disabled = dirty === 0;
        $saveBtn.textContent = dirty ? `💾 Сохранить (${dirty})` : "💾 Сохранить";
    }

    $tbody.addEventListener("input", e => {
        if (!e.target.classList.contains("cp-cell")) return;
        const inp = e.target;
        inp.classList.remove("cp-error");
        inp.classList.toggle("cp-dirty", isDirty(inp));
        refreshSaveBtn();
        setStatus("");
    });

    $tbody.addEventListener("focus", e => {
        if (e.target.classList.contains("cp-cell")) e.target.select();
    }, true);

    // ---- Сохранение ----
    function setStatus(msg, kind) {
        $status.textContent = msg;
        $status.className = "cp-status" + (kind ? " " + kind : "");
    }

    $saveBtn.addEventListener("click", async () => {
        const dirty = Array.from($tbody.querySelectorAll(".cp-cell.cp-dirty"));
        if (!dirty.length) return;

        const changes = dirty.map(inp => ({
            city_id: parseInt(inp.dataset.cityId, 10),
            class_id: parseInt(inp.dataset.classId, 10),
            value: normalize(inp.value),
        }));

        $saveBtn.disabled = true;
        setStatus("Сохранение...");

        try {
            const resp = await fetch(SAVE_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({
                    changes,
                }),
            });
            const data = await resp.json();
            if (!resp.ok || !data.ok) {
                throw new Error(data.error || "Ошибка сохранения");
            }

            // Помечаем ошибочные ячейки
            const errMap = new Map();
            (data.errors || []).forEach(e => {
                errMap.set(`${e.city_id}:${e.class_id}`, e.error);
            });

            dirty.forEach(inp => {
                const key = `${inp.dataset.cityId}:${inp.dataset.classId}`;
                if (errMap.has(key)) {
                    inp.classList.add("cp-error");
                    inp.classList.remove("cp-dirty");
                } else {
                    inp.dataset.original = normalize(inp.value) || "0.00";
                    inp.classList.remove("cp-dirty");
                }
            });

            const errCount = (data.errors || []).length;
            if (errCount) {
                setStatus(`Сохранено: ${data.saved}, удалено: ${data.deleted}, ошибок: ${errCount}`, "err");
            } else {
                setStatus(`✓ Сохранено: ${data.saved}, удалено: ${data.deleted}`, "ok");
            }
        } catch (err) {
            setStatus("✗ " + err.message, "err");
        } finally {
            refreshSaveBtn();
        }
    });

    // ---- Обновить ----
    $reloadBtn.addEventListener("click", () => {
        const dirty = $tbody.querySelectorAll(".cp-cell.cp-dirty").length;
        if (dirty && !confirm(`Несохранённых изменений: ${dirty}. Сбросить?`)) return;
        window.location.reload();
    });

    // ---- Добавить город ----
    $addCityBtn.addEventListener("click", async () => {
        const name = prompt("Название города:");
        if (!name || !name.trim()) return;

        const fd = new FormData();
        fd.append("name", name.trim());

        try {
            const resp = await fetch(ADD_CITY_URL, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: fd,
            });
            const data = await resp.json();
            if (!resp.ok || !data.ok) {
                throw new Error(data.error || "Ошибка");
            }
            if (!data.created) {
                alert(`Город «${data.name}» уже существует.`);
                return;
            }
            // Перезагружаем — простейший способ получить актуальные строки.
            window.location.reload();
        } catch (err) {
            alert("Не удалось добавить город: " + err.message);
        }
    });

    // ---- Навигация Enter / стрелками ----
    $tbody.addEventListener("keydown", e => {
        if (!e.target.classList.contains("cp-cell")) return;
        const cell = e.target;
        const td = cell.closest("td");
        const tr = cell.closest("tr");
        const tdIndex = Array.from(tr.children).indexOf(td);

        let targetTr = null;
        if (e.key === "Enter" || e.key === "ArrowDown") {
            e.preventDefault();
            targetTr = tr.nextElementSibling;
            while (targetTr && targetTr.classList.contains("cp-hidden")) targetTr = targetTr.nextElementSibling;
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            targetTr = tr.previousElementSibling;
            while (targetTr && targetTr.classList.contains("cp-hidden")) targetTr = targetTr.previousElementSibling;
        } else if (e.key === "ArrowRight" && cell.selectionStart === cell.value.length) {
            const next = td.nextElementSibling?.querySelector(".cp-cell");
            if (next) { e.preventDefault(); next.focus(); }
            return;
        } else if (e.key === "ArrowLeft" && cell.selectionStart === 0) {
            const prev = td.previousElementSibling?.querySelector(".cp-cell");
            if (prev) { e.preventDefault(); prev.focus(); }
            return;
        } else {
            return;
        }

        if (targetTr) {
            const next = targetTr.children[tdIndex]?.querySelector(".cp-cell");
            if (next) next.focus();
        }
    });

    // ---- Защита от случайного ухода ----
    window.addEventListener("beforeunload", e => {
        if ($tbody.querySelectorAll(".cp-cell.cp-dirty").length) {
            e.preventDefault();
            e.returnValue = "";
        }
    });

        // ==================== Импорт Excel ====================
    const IMPORT_PREVIEW_URL = wrap.dataset.importPreviewUrl;
    const IMPORT_APPLY_URL = wrap.dataset.importApplyUrl;

    const $importBtn = document.getElementById("cp-import");
    const $fileInput = document.getElementById("cp-file");
    const $modal = document.getElementById("cp-import-modal");
    const $modalClose = document.getElementById("cp-import-close");
    const $modalCancel = document.getElementById("cp-import-cancel");
    const $modalApply = document.getElementById("cp-import-apply");
    const $loader = document.getElementById("cp-import-loader");
    const $content = document.getElementById("cp-import-content");
    const $errorBox = document.getElementById("cp-import-error");
    const $summary = document.getElementById("cp-import-summary");
    const $warnings = document.getElementById("cp-import-warnings");
    const $previewTable = document.getElementById("cp-preview-table");
    const $optCreate = document.getElementById("cp-opt-create-cities");
    const $optOverwrite = document.getElementById("cp-opt-overwrite");
    const $optClear = document.getElementById("cp-opt-clear-zeros");

    let parsedData = null;

    function showModal() {
        $modal.classList.remove("cp-hidden");
    }
    function hideModal() {
        $modal.classList.add("cp-hidden");
        parsedData = null;
        $fileInput.value = "";
        $loader.classList.remove("cp-hidden");
        $content.classList.add("cp-hidden");
        $errorBox.classList.add("cp-hidden");
        $modalApply.disabled = true;
    }

    function showError(msg) {
        $loader.classList.add("cp-hidden");
        $content.classList.add("cp-hidden");
        $errorBox.classList.remove("cp-hidden");
        $errorBox.textContent = msg;
    }

    function renderPreview(parsed) {
        parsedData = parsed;

        // Summary
        const s = parsed.summary || {};
        $summary.innerHTML = `
            <span>Строк: <b>${s.rows || 0}</b></span>
            <span>Распознано ячеек: <b>${s.matched_cells || 0}</b></span>
            <span>Неизвестных ячеек: <b>${s.unknown_cells || 0}</b></span>
            <span>Ошибок: <b>${s.error_cells || 0}</b></span>
        `;

        // Warnings
        const warns = [];
        if (parsed.unknown_cities && parsed.unknown_cities.length) {
            warns.push(`<div class="cp-warn-block">
                <b>Города не найдены в БД (${parsed.unknown_cities.length}):</b>
                ${parsed.unknown_cities.map(escapeHtml).join(", ")}
                <br><small>Будут созданы, если включена опция «Создавать отсутствующие города».</small>
            </div>`);
        }
        if (parsed.unknown_classes && parsed.unknown_classes.length) {
            warns.push(`<div class="cp-warn-block">
                <b>Классы не найдены в БД (${parsed.unknown_classes.length}):</b>
                ${parsed.unknown_classes.map(escapeHtml).join(", ")}
                <br><small>Колонки с этими названиями будут пропущены. Добавьте классы вручную, если нужно.</small>
            </div>`);
        }
        $warnings.innerHTML = warns.join("");

        // Preview table
        const headers = parsed.headers || [];
        const rows = parsed.rows || [];

        let html = "<thead><tr><th>Город</th>";
        headers.forEach(h => {
            const cls = h.class_id ? "" : ' style="color:#c0392b"';
            html += `<th${cls}>${escapeHtml(h.name)}${h.class_id ? "" : " ⚠"}</th>`;
        });
        html += "</tr></thead><tbody>";

        rows.forEach(row => {
            const rowCls = row.city_id ? "" : "cp-row-unknown";
            html += `<tr class="${rowCls}"><td>${escapeHtml(row.city_name)}</td>`;
            row.cells.forEach(cell => {
                if (cell.error) {
                    html += `<td class="cp-cell-err" title="${escapeHtml(cell.error)}">err</td>`;
                } else if (!cell.value) {
                    html += `<td class="cp-cell-skip">—</td>`;
                } else if (!cell.class_id) {
                    html += `<td class="cp-cell-skip" title="Класс не найден">${escapeHtml(cell.value)}</td>`;
                } else {
                    const isNew = !row.city_id;
                    html += `<td class="${isNew ? "cp-cell-new" : "cp-cell-update"}">${escapeHtml(cell.value)}</td>`;
                }
            });
            html += "</tr>";
        });
        html += "</tbody>";
        $previewTable.innerHTML = html;

        $loader.classList.add("cp-hidden");
        $content.classList.remove("cp-hidden");
        $errorBox.classList.add("cp-hidden");
        $modalApply.disabled = false;
    }

    function escapeHtml(s) {
        if (s === null || s === undefined) return "";
        return String(s)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    $importBtn.addEventListener("click", () => {
        const dirty = $tbody.querySelectorAll(".cp-cell.cp-dirty").length;
        if (dirty && !confirm(`Несохранённых изменений: ${dirty}. Продолжить импорт?`)) return;
        $fileInput.click();
    });

    $fileInput.addEventListener("change", async () => {
        const file = $fileInput.files[0];
        if (!file) return;

        showModal();

        const fd = new FormData();
        fd.append("file", file);

        try {
            const resp = await fetch(IMPORT_PREVIEW_URL, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: fd,
            });
            const data = await resp.json();
            if (!resp.ok || !data.ok) {
                showError(data.error || "Ошибка чтения файла.");
                return;
            }
            renderPreview(data.parsed);
        } catch (err) {
            showError("Ошибка сети: " + err.message);
        }
    });

    $modalClose.addEventListener("click", hideModal);
    $modalCancel.addEventListener("click", hideModal);
    $modal.addEventListener("click", e => {
        if (e.target === $modal) hideModal();
    });

    $modalApply.addEventListener("click", async () => {
        if (!parsedData) return;

        $modalApply.disabled = true;
        $modalApply.textContent = "Применение...";

        try {
            const resp = await fetch(IMPORT_APPLY_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({
                    parsed: parsedData,
                    create_missing_cities: $optCreate.checked,
                    overwrite: $optOverwrite.checked,
                    clear_zeros: $optClear.checked,
                }),
            });
            const data = await resp.json();
            if (!resp.ok || !data.ok) {
                showError(data.error || "Ошибка применения.");
                $modalApply.disabled = false;
                $modalApply.textContent = "Применить";
                return;
            }

            const errCount = (data.errors || []).length;
            const msg = `Готово. Создано городов: ${data.created_cities}, ` +
                        `сохранено тарифов: ${data.saved}, ` +
                        `удалено: ${data.deleted}, ` +
                        `пропущено: ${data.skipped}` +
                        (errCount ? `, ошибок: ${errCount}` : "");
            alert(msg);
            window.location.reload();
        } catch (err) {
            showError("Ошибка сети: " + err.message);
            $modalApply.disabled = false;
            $modalApply.textContent = "Применить";
        }
    });
})();
```

### `calc/templates/calc/form.html`

```
{% extends "calc/base.html" %}

{% block title %}Калькулятор — СтройКалькулятор{% endblock %}

{% block content %}
<section class="hero">
    <p class="hero-eyebrow">Калькулятор</p>
    <h1 class="hero-title">Расчёт стоимости строительства</h1>
    <p class="hero-sub">
        Параметрический расчёт на базе нормативных стоимостей,
        классов строительства и поправочных коэффициентов.
    </p>
</section>

<div class="split">
    {# ── Левая карточка: форма ─────────────────────────────────────── #}
    <form method="post" class="card" novalidate>
        {% csrf_token %}
        <h2 class="card-title">Параметры проекта</h2>

        {% if error %}
        <div class="alert alert-error">{{ error }}</div>
        {% endif %}

        <div class="field">
            <label class="label" for="{{ form.city.id_for_label }}">{{ form.city.label }}</label>
            {{ form.city }}
            {{ form.city.errors }}
        </div>

        <div class="field">
            <label class="label" for="{{ form.purpose.id_for_label }}">{{ form.purpose.label }}</label>
            {{ form.purpose }}
            {{ form.purpose.errors }}
        </div>

        <div class="field">
            <label class="label" for="{{ form.building_class.id_for_label }}">{{ form.building_class.label }}</label>
            <div data-classes-field data-url-template="{% url 'calc:classes_for_purpose' 0 %}">
                {{ form.building_class }}
            </div>
            {{ form.building_class.errors }}
        </div>

        <div class="field-row">
            <div class="field">
                <label class="label" for="{{ form.floors.id_for_label }}">{{ form.floors.label }}</label>
                {{ form.floors }}
                {{ form.floors.errors }}
            </div>
            <div class="field">
                <label class="label" for="{{ form.total_area.id_for_label }}">{{ form.total_area.label }}</label>
                {{ form.total_area }}
                {{ form.total_area.errors }}
            </div>
        </div>

        <div class="field">
            <label class="checkbox-row">
                {{ form.underground_parking }}
                <span>{{ form.underground_parking.label }}</span>
            </label>
            {{ form.underground_parking.errors }}
        </div>

        <div class="field">
            <label class="checkbox-row">
                {{ form.ground_parking }}
                <span>{{ form.ground_parking.label }}</span>
            </label>
            {{ form.ground_parking.errors }}
        </div>

        <div class="field {% if not form.ground_parking.value %}hidden{% endif %}" data-depends-on="ground_parking">
            <label class="label" for="{{ form.ground_parking_spaces.id_for_label }}">
                {{ form.ground_parking_spaces.label }}
            </label>
            {{ form.ground_parking_spaces }}
            {{ form.ground_parking_spaces.errors }}
        </div>

        <button type="submit" class="btn btn-primary">Рассчитать проект</button>
    </form>

    {# ── Правая карточка: результаты ──────────────────────────────── #}
    <div class="card">
        <h2 class="card-title">Результат расчёта</h2>

        {% if result %}
        {# Hero — итоговая стоимость строительства #}
        <div class="result-hero">
            <p class="result-hero-label">Стоимость строительства</p>
            <p class="result-hero-value">
                {{ result.construction_cost|floatformat:0 }}<span class="suffix">₽</span>
            </p>
            <div class="result-hero-meta">
                <div>
                    Цена за м²
                    <b>{{ result.price_per_sqm|floatformat:0 }} ₽</b>
                </div>
                <div>
                    Площадь
                    <b>{{ result.total_area|floatformat:2 }} м²</b>
                </div>
                {% if result.duration_months %}
                <div>
                    Срок строительства
                    <b>{{ result.duration_months }} мес.</b>
                </div>
                {% endif %}
            </div>
        </div>

        {# Базовые показатели #}
        <div class="result-section">
            <h3 class="result-section-title">Структура стоимости</h3>
            <div class="result-grid result-grid-3">
                <div class="result-item">
                    <div class="result-item-label">Базовая стоимость</div>
                    <div class="result-item-value">
                        {{ result.base_cost|floatformat:0 }}<span class="suffix">₽</span>
                    </div>
                </div>
                <div class="result-item">
                    <div class="result-item-label">Инфляция</div>
                    <div class="result-item-value">
                        {{ result.inflation_amount|floatformat:0 }}<span class="suffix">₽</span>
                    </div>
                </div>
                <div class="result-item">
                    <div class="result-item-label">Площадь квартир</div>
                    <div class="result-item-value">
                        {{ result.apartments_area|floatformat:0 }}<span class="suffix">м²</span>
                    </div>
                </div>
            </div>
        </div>

        {# Коэффициенты #}
        <div class="result-section">
            <h3 class="result-section-title">Коэффициенты</h3>
            <div class="result-grid">
                <div class="result-item">
                    <div class="result-item-label">Очистка от инфляции</div>
                    <div class="result-item-value">{{ result.clean_coef|floatformat:3 }}</div>
                </div>
                <div class="result-item">
                    <div class="result-item-label">Ставка инфляции</div>
                    <div class="result-item-value">{{ result.inflation_rate|floatformat:4 }}</div>
                </div>
            </div>
        </div>

        {# Соцобъекты #}
        {% if result.doo_seats or result.sosh_seats %}
        <div class="result-section">
            <h3 class="result-section-title">Социальная инфраструктура</h3>
            <div class="result-grid">
                {% if result.doo_seats %}
                <div class="result-item">
                    <div class="result-item-label">ДОО — мест</div>
                    <div class="result-item-value">
                        {{ result.doo_seats }}
                        <span class="suffix">{{ result.doo_cost|floatformat:0 }} ₽</span>
                    </div>
                </div>
                {% endif %}
                {% if result.sosh_seats %}
                <div class="result-item">
                    <div class="result-item-label">СОШ — мест</div>
                    <div class="result-item-value">
                        {{ result.sosh_seats }}
                        <span class="suffix">{{ result.sosh_cost|floatformat:0 }} ₽</span>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {# Паркинг #}
        {% if result.underground_parking or result.ground_parking_spaces %}
        <div class="result-section">
            <h3 class="result-section-title">Паркинг</h3>
            <div class="result-grid">
                {% if result.underground_parking %}
                <div class="result-item">
                    <div class="result-item-label">Подземный</div>
                    <div class="result-item-value">да</div>
                </div>
                {% endif %}
                {% if result.ground_parking_spaces %}
                <div class="result-item">
                    <div class="result-item-label">Наземный · {{ result.ground_parking_spaces }} м/м</div>
                    <div class="result-item-value">
                        {{ result.ground_parking_cost|floatformat:0 }}<span class="suffix">₽</span>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% else %}
        <div class="result-empty">
            <div class="result-empty-icon">∑</div>
            <p class="result-empty-title">Здесь появится расчёт</p>
            <p class="result-empty-sub">
                Заполните параметры слева и нажмите «Рассчитать проект».
            </p>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script>
(function () {
    const purposeEl = document.querySelector('[name="purpose"]');
    const wrapper = document.querySelector('[data-classes-field]');
    if (!purposeEl || !wrapper) return;

    const classEl = wrapper.querySelector('select[name="building_class"]');
    const urlTemplate = wrapper.dataset.urlTemplate;  // .../api/classes/0/

    function tsOf(el) { return el.tomselect || null; }

    async function loadClasses(purposeId, preserve) {
        const ts = tsOf(classEl);
        if (!purposeId) {
            if (ts) {
                ts.clear();
                ts.clearOptions();
            } else {
                classEl.innerHTML = '<option value="">———</option>';
            }
            return;
        }
        const url = urlTemplate.replace(/\/0\/?$/, '/' + purposeId + '/');
        const resp = await fetch(url, { headers: { 'Accept': 'application/json' } });
        if (!resp.ok) return;
        const data = await resp.json();

        const current = preserve ? (ts ? ts.getValue() : classEl.value) : '';

        if (ts) {
            ts.clear(true);
            ts.clearOptions();
            ts.addOption(data.classes.map(c => ({ value: String(c.id), text: c.name })));
            ts.refreshOptions(false);
            if (current && data.classes.some(c => String(c.id) === String(current))) {
                ts.setValue(current, true);
            }
        } else {
            classEl.innerHTML = '<option value="">———</option>';
            for (const c of data.classes) {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name;
                if (String(c.id) === String(current)) opt.selected = true;
                classEl.appendChild(opt);
            }
        }
    }

    // Слушаем как нативное change, так и Tom Select-овское
    purposeEl.addEventListener('change', () => loadClasses(purposeEl.value, false));

    // Догрузка при восстановлении формы
    const initialPurpose = purposeEl.value;
    if (initialPurpose && classEl.options.length <= 1) {
        loadClasses(initialPurpose, true);
    }
})();
</script>
{% endblock %}
```
