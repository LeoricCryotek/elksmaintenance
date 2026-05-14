# -*- coding: utf-8 -*-
"""Pre-migration for 19.0.7.0 — preserve legacy x_ticket_type values
before Odoo recreates the column as an integer FK.

The field changes from a Selection (varchar) to a Many2one to the new
``maintenance.issue.type`` model.  Odoo's ORM will drop the old varchar
column and create a new int column with the same name during the
schema update.  We need to:

  1. Copy the old varchar values to a temporary column.
  2. Drop the old column so the ORM creates the new int one cleanly.
  3. The post-migration script then maps codes → issue-type IDs.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        SELECT data_type
          FROM information_schema.columns
         WHERE table_name = 'maintenance_request'
           AND column_name = 'x_ticket_type'
        """
    )
    row = cr.fetchone()
    if not row:
        _logger.info(
            "elksmaintenance 19.0.7.0: no x_ticket_type column, skip."
        )
        return

    data_type = row[0]
    if data_type == "integer":
        _logger.info(
            "elksmaintenance 19.0.7.0: x_ticket_type already int (FK), skip."
        )
        return

    # Stash existing varchar values to a temp column.
    _logger.info(
        "elksmaintenance 19.0.7.0: stashing legacy x_ticket_type values "
        "(data_type=%s) to x_ticket_type_legacy.", data_type,
    )
    cr.execute(
        """
        ALTER TABLE maintenance_request
            ADD COLUMN IF NOT EXISTS x_ticket_type_legacy VARCHAR
        """
    )
    cr.execute(
        """
        UPDATE maintenance_request
           SET x_ticket_type_legacy = x_ticket_type
         WHERE x_ticket_type IS NOT NULL
        """
    )
    cr.execute(
        'ALTER TABLE maintenance_request DROP COLUMN x_ticket_type'
    )
    _logger.info(
        "elksmaintenance 19.0.7.0: x_ticket_type column dropped; "
        "ORM will recreate as int FK."
    )
