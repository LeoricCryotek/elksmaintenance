# -*- coding: utf-8 -*-
"""Pre-migration for 19.0.7.1 - purge orphan ir.ui.view rows that still
reference the legacy x_photo_1..5 image fields on maintenance.request.

Why this is needed
==================
The 19.0.4.0 migration moved photo data into ir.attachment chatter
records and dropped the underlying ``x_photo_1..5`` columns on
``maintenance_request``. It updated the XML-owned view records too -
but any view row created in the DB by Odoo Studio (or by an earlier
revision of this module whose XML ID is now gone) was left in place
with the dead field references baked into its ``arch_db``.

Symptom on later upgrades: when ANY module (e.g. elkspurchase) loads
a view inheriting ``maintenance.hr_equipment_request_view_form``,
Odoo validates the combined inheritance tree, walks the orphan view,
and aborts with::

    Field "x_photo_1" does not exist in model "maintenance.request"

The traceback points at whichever inheriting module was last loaded
(elkspurchase, in our case), but the offending node lives in the
orphan view row, not in any module's XML.

Fix
===
Delete every ir.ui.view record whose ``model = 'maintenance.request'``
and whose ``arch_db`` references one of the dead photo field names.
We also delete the matching ``ir.model.data`` rows so Odoo doesn't
try to re-create the deleted XML ID on a later load.

The deletion is idempotent (safe to re-run; deletes nothing if there
are no matches). Records are logged before deletion so the lodge has
an audit trail in the server log.
"""
import logging

_logger = logging.getLogger(__name__)

DEAD_FIELDS = ("x_photo_1", "x_photo_2", "x_photo_3", "x_photo_4", "x_photo_5")


def migrate(cr, version):
    if not version:
        # Fresh install - nothing to purge.
        return

    # Find any view row that still references the dead photo fields.
    # Use ILIKE so we catch both <field name="x_photo_1"> and any other
    # textual occurrence (e.g. domain= expressions, invisible= attrs).
    like_clauses = " OR ".join(
        ["arch_db ILIKE %s"] * len(DEAD_FIELDS)
    )
    params = [f"%{name}%" for name in DEAD_FIELDS]
    cr.execute(
        f"""
        SELECT id, name, key, model, inherit_id
          FROM ir_ui_view
         WHERE model = 'maintenance.request'
           AND ({like_clauses})
        """,
        params,
    )
    rows = cr.fetchall()
    if not rows:
        _logger.info(
            "elksmaintenance 19.0.7.1: no orphan x_photo_* view rows, skip."
        )
        return

    _logger.warning(
        "elksmaintenance 19.0.7.1: purging %s orphan view row(s) that "
        "reference the dead x_photo_1..5 fields:", len(rows),
    )
    for row in rows:
        view_id, name, key, model, inherit_id = row
        _logger.warning(
            "  - ir.ui.view id=%s name=%r key=%r model=%s inherit_id=%s",
            view_id, name, key, model, inherit_id,
        )

    view_ids = tuple(r[0] for r in rows)

    # Drop the ir.model.data first so we don't leave dangling rows.
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE model = 'ir.ui.view'
           AND res_id IN %s
        """,
        (view_ids,),
    )
    _logger.info(
        "elksmaintenance 19.0.7.1: removed %s ir.model.data row(s).",
        cr.rowcount,
    )

    cr.execute(
        "DELETE FROM ir_ui_view WHERE id IN %s",
        (view_ids,),
    )
    _logger.info(
        "elksmaintenance 19.0.7.1: purged %s ir.ui.view row(s).",
        cr.rowcount,
    )
