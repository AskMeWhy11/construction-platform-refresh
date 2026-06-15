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

// ── Отделка (только жилое / гостиница) + лейбл площади ──
(function () {
    const purposeSel = document.querySelector('[name="purpose"]');
    const finishBlock = document.querySelector("[data-finish-block]");
    const finishOpts = document.querySelector("[data-finish-options]");
    const finishCustom = document.querySelector("[data-finish-custom]");
    const enableCb = document.getElementById("id_finish_enabled");
    const areaLabel = document.querySelector("[data-area-label]");
    if (!purposeSel) return;

    const AREA_DEFAULT = areaLabel ? areaLabel.textContent : "";

    function selectedCategory() {
        const opt = purposeSel.options[purposeSel.selectedIndex];
        return opt ? (opt.dataset.category || "") : "";
    }

    function syncFinishOptions() {
        if (!finishOpts) return;
        const on = enableCb && enableCb.checked && !finishBlock.classList.contains("hidden");
        finishOpts.classList.toggle("hidden", !on);
        if (on) syncCustom();
        else if (finishCustom) finishCustom.classList.add("hidden");
    }

    function syncCustom() {
        if (!finishCustom) return;
        const checked = document.querySelector('input[name="finish_type"]:checked');
        finishCustom.classList.toggle("hidden", !checked || checked.value !== "designer");
    }

    function syncPurpose() {
        const cat = selectedCategory();
        const finishEnabled = cat === "residential" || cat === "hotel";

        if (finishBlock) {
            finishBlock.classList.toggle("hidden", !finishEnabled);
            if (!finishEnabled && enableCb) enableCb.checked = false;
        }
        if (areaLabel) {
            areaLabel.textContent =
                cat === "hotel" ? "Площадь номерного фонда, м²" : AREA_DEFAULT;
        }
        syncFinishOptions();
    }

    purposeSel.addEventListener("change", syncPurpose);
    if (enableCb) enableCb.addEventListener("change", syncFinishOptions);
    document.querySelectorAll('input[name="finish_type"]').forEach((r) =>
        r.addEventListener("change", syncCustom)
    );

    syncPurpose();
})();