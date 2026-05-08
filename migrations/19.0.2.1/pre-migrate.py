# -*- coding: utf-8 -*-
"""Remove stale ir.ui.view records referencing ``action_recalculate_priority``.

This method does not exist on ``maintenance.request`` in Odoo 19.  A leftover
view record from a previous Odoo version causes view-validation errors that
block every module inheriting the maintenance form (e.g. elkspurchase).

Running as a *pre*-migration ensures the stale record is gone before the ORM
tries to validate the combined view tree.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE model = 'maintenance.request'
          AND arch_db::text LIKE '%%action_recalculate_priority%%'
        RETURNING id, name
    """)
    for vid, vname in cr.fetchall():
        _logger.info("Removed stale maintenance view id=%s name=%s", vid, vname)
