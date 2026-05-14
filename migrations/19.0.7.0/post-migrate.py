# -*- coding: utf-8 -*-
"""Post-migration for 19.0.7.0 — map legacy x_ticket_type codes onto
the new maintenance.issue.type records, then drop the temp column.

By the time this runs, the seed data file has already created the
8 default issue types, each with a stable ``code`` that matches the
old Selection key (repair, safety, electrical, plumbing, hvac,
cleaning, exterior, other).
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Only run if the legacy temp column is present (set by pre-migrate).
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'maintenance_request'
           AND column_name = 'x_ticket_type_legacy'
        """
    )
    if not cr.fetchone():
        _logger.info(
            "elksmaintenance 19.0.7.0 post: no legacy column, skip."
        )
        return

    # Map: legacy code → maintenance.issue.type.id
    cr.execute("SELECT id, code FROM maintenance_issue_type")
    type_by_code = {row[1]: row[0] for row in cr.fetchall() if row[1]}
    if not type_by_code:
        _logger.warning(
            "elksmaintenance 19.0.7.0 post: no maintenance_issue_type "
            "rows found — seed data may not have loaded.  "
            "Skipping x_ticket_type backfill; tickets will be left blank."
        )
    else:
        for code, type_id in type_by_code.items():
            cr.execute(
                """
                UPDATE maintenance_request
                   SET x_ticket_type = %s
                 WHERE x_ticket_type_legacy = %s
                """,
                (type_id, code),
            )
            _logger.info(
                "elksmaintenance 19.0.7.0 post: backfilled "
                "x_ticket_type=%s for code=%r (%s rows)",
                type_id, code, cr.rowcount,
            )

    # Drop the legacy column — data is now migrated.
    cr.execute(
        'ALTER TABLE maintenance_request '
        'DROP COLUMN IF EXISTS x_ticket_type_legacy'
    )
    _logger.info(
        "elksmaintenance 19.0.7.0 post: dropped x_ticket_type_legacy."
    )
