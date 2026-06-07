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