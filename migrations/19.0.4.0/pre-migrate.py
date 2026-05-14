# -*- coding: utf-8 -*-
"""Pre-migration for 19.0.4.0 — move x_photo_1..5 image data to
ir.attachment records on the maintenance.request, then drop the columns.

Running this in *pre-migration* (rather than post-) means the columns
still exist when we read them, but the new view definition referencing
the removed fields hasn't loaded yet.
"""
import base64
import logging

_logger = logging.getLogger(__name__)

PHOTO_COLS = ["x_photo_1", "x_photo_2", "x_photo_3", "x_photo_4", "x_photo_5"]


def migrate(cr, version):
    if not version:
        return

    # Discover which photo columns actually exist on the table.
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'maintenance_request'
           AND column_name = ANY(%s)
        """,
        (PHOTO_COLS,),
    )
    existing = [r[0] for r in cr.fetchall()]
    if not existing:
        _logger.info("elksmaintenance 19.0.4.0: no legacy photo cols, skip.")
        return

    select_cols = ", ".join(existing)
    cr.execute(
        f"SELECT id, {select_cols} FROM maintenance_request "
        f"WHERE {' OR '.join(c + ' IS NOT NULL' for c in existing)}"
    )
    rows = cr.fetchall()
    _logger.info(
        "elksmaintenance 19.0.4.0: migrating photos on %s ticket(s)",
        len(rows),
    )

    for row in rows:
        request_id = row[0]
        for idx, col in enumerate(existing, start=1):
            data = row[idx]
            if not data:
                continue
            # Image fields store base64-encoded bytes already; ir.attachment
            # expects the same encoding when using raw INSERT.
            cr.execute(
                """
                INSERT INTO ir_attachment
                    (name, res_model, res_id, type, mimetype,
                     datas, create_date, write_date)
                VALUES
                    (%s, 'maintenance.request', %s, 'binary', 'image/png',
                     %s, NOW(), NOW())
                """,
                (f"{col}.png", request_id, data),
            )

    # Drop the obsolete columns.
    for col in existing:
        cr.execute(
            f'ALTER TABLE maintenance_request DROP COLUMN IF EXISTS "{col}"'
        )
    _logger.info(
        "elksmaintenance 19.0.4.0: dropped legacy photo columns %s",
        existing,
    )
