/**
 * Populates the Location and Issue Type <select> dropdowns on any
 * page that contains a maintenance.request form (built-in form snippet
 * or our custom "Maintenance Form" snippet).
 *
 * Selects fields by their ``name`` attribute (which Odoo's HTML
 * sanitizer never strips) so this works even if a custom website
 * theme drops the ``data-elks-dynamic-options`` markers.
 */
(function () {
    "use strict";

    const LOG = "[elksmaintenance]";

    // Top-level marker so we can see in DevTools that the file was
    // at least *loaded* by the asset bundler, even if init() never runs.
    console.log(`${LOG} script loaded at`, new Date().toISOString());

    // Map: <select name="..."> → JSON endpoint + placeholder text.
    const FIELDS = [
        {
            name: "x_location_id",
            url: "/maintenance/locations.json",
            placeholder: "— Select a location —",
            label: "Location",
        },
        {
            name: "x_ticket_type",
            url: "/maintenance/issue-types.json",
            placeholder: "— Select an issue type —",
            label: "Issue Type",
        },
    ];

    function findMaintenanceForm() {
        // Find the form whose `data-model_name="maintenance.request"`
        // OR any form containing an x_location_id or x_ticket_type
        // select.  We restrict the search to that form so we don't
        // accidentally hit a Contact form's "name" field.
        const formByModel = document.querySelector(
            "form[data-model_name='maintenance.request']"
        );
        if (formByModel) {
            return formByModel;
        }
        const formByField =
            document.querySelector("select[name='x_location_id']")
            || document.querySelector("select[name='x_ticket_type']");
        if (formByField && formByField.form) {
            return formByField.form;
        }
        return null;
    }

    async function populate(selectEl, field) {
        const previouslySelected = selectEl.value;
        selectEl.disabled = true;

        let records = [];
        try {
            const response = await fetch(field.url, {
                method: "GET",
                headers: { Accept: "application/json" },
                credentials: "same-origin",
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            records = await response.json();
            console.log(
                `${LOG} ${field.label}: loaded ${records.length} record(s) from ${field.url}`
            );
        } catch (e) {
            console.warn(
                `${LOG} ${field.label}: fetch failed (${field.url}):`,
                e
            );
            selectEl.disabled = false;
            return;
        }

        selectEl.innerHTML = "";
        const placeholderOpt = document.createElement("option");
        placeholderOpt.value = "";
        placeholderOpt.textContent = field.placeholder;
        selectEl.appendChild(placeholderOpt);

        for (const rec of records) {
            const opt = document.createElement("option");
            opt.value = String(rec.id);
            opt.textContent = rec.name;
            selectEl.appendChild(opt);
        }

        if (
            previouslySelected &&
            records.some(
                (r) => String(r.id) === String(previouslySelected)
            )
        ) {
            selectEl.value = previouslySelected;
        }

        selectEl.disabled = false;
    }

    function init() {
        console.log(`${LOG} init: scanning DOM`);
        const form = findMaintenanceForm();
        if (!form) {
            console.log(`${LOG} init: no maintenance.request form on this page`);
            return;
        }
        console.log(`${LOG} init: found maintenance form`, form);

        for (const field of FIELDS) {
            const selectEl = form.querySelector(
                `select[name="${field.name}"]`
            );
            if (selectEl) {
                console.log(`${LOG} init: populating ${field.label}`);
                populate(selectEl, field);
            } else {
                console.log(
                    `${LOG} init: no <select name="${field.name}"> in form — skipping`
                );
            }
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }
})();
