# -*- coding: utf-8 -*-
"""Remove stale ir.ui.view records referencing ``x_request_type``.

A previous version of elksmaintenance used ``x_request_type`` which was
later renamed to ``x_ticket_type``.  The old inherited view records are
still in the database and cause validation errors because the field no
longer exists on ``maintenance.request``.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE model = 'maintenance.request'
          AND arch_db::text LIKE '%%x_request_type%%'
        RETURNING id, name
    """)
    for vid, vname in cr.fetchall():
        _logger.info("Removed stale maintenance view id=%s name=%s", vid, vname)
