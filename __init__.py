# -*- coding: utf-8 -*-
import logging
from . import models
from . import controllers
from . import wizard

_logger = logging.getLogger(__name__)


def _pre_init_cleanup(env):
    """Remove stale ir.ui.view records referencing methods that no longer
    exist on ``maintenance.request`` in Odoo 19.

    Runs as ``pre_init_hook`` (fires on both install and upgrade) so the
    stale record is gone before Odoo tries to validate the combined view.
    """
    # Odoo 19 pre_init_hook receives an Environment object
    env.cr.execute("""
        DELETE FROM ir_ui_view
        WHERE model = 'maintenance.request'
          AND arch_db::text LIKE '%%action_recalculate_priority%%'
        RETURNING id, name
    """)
    for vid, vname in env.cr.fetchall():
        _logger.info("Removed stale maintenance view id=%s name=%s", vid, vname)
