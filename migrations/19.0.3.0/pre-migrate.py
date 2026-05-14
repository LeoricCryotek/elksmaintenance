# -*- coding: utf-8 -*-
"""Pre-migration: remap old stages before new stage data loads.

Old stages → new mapping:
  - stage_waiting  → stage_in_progress
  - stage_resolved → stage_done
  - stage_cancelled → stage_done
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    _logger.info("elksmaintenance 19.0.3.0: remapping old stages")

    # Get old stage XML IDs
    cr.execute("""
        SELECT imd.name, imd.res_id
        FROM ir_model_data imd
        WHERE imd.module = 'elksmaintenance'
          AND imd.model = 'maintenance.stage'
          AND imd.name IN (
              'stage_waiting', 'stage_resolved', 'stage_cancelled',
              'stage_in_progress', 'stage_done'
          )
    """)
    stage_map = dict(cr.fetchall())

    in_progress_id = stage_map.get("stage_in_progress")

    # Remap waiting → in_progress
    waiting_id = stage_map.get("stage_waiting")
    if waiting_id and in_progress_id:
        cr.execute(
            "UPDATE maintenance_request SET stage_id = %s WHERE stage_id = %s",
            (in_progress_id, waiting_id),
        )
        _logger.info("Remapped %d tickets from Waiting → In Progress", cr.rowcount)

    # Rename stage_resolved → stage_done (will be overwritten by data file)
    resolved_id = stage_map.get("stage_resolved")
    if resolved_id:
        # Update the XML ID so stage_done points here
        cr.execute(
            "UPDATE ir_model_data SET name = 'stage_done' "
            "WHERE module = 'elksmaintenance' AND name = 'stage_resolved'"
        )
        cr.execute(
            "UPDATE maintenance_stage SET name = '{\"en_US\": \"Done\"}', sequence = 4 WHERE id = %s",
            (resolved_id,),
        )
        _logger.info("Renamed stage_resolved → stage_done (id=%s)", resolved_id)

    # Move cancelled tickets to done, then delete cancelled stage
    cancelled_id = stage_map.get("stage_cancelled")
    done_id = resolved_id or stage_map.get("stage_done")
    if cancelled_id and done_id:
        cr.execute(
            "UPDATE maintenance_request SET stage_id = %s WHERE stage_id = %s",
            (done_id, cancelled_id),
        )
        _logger.info("Remapped %d cancelled tickets → Done", cr.rowcount)
        cr.execute(
            "DELETE FROM ir_model_data WHERE module = 'elksmaintenance' "
            "AND name = 'stage_cancelled'"
        )
        cr.execute("DELETE FROM maintenance_stage WHERE id = %s", (cancelled_id,))

    # Delete old stage_waiting
    if waiting_id:
        cr.execute(
            "DELETE FROM ir_model_data WHERE module = 'elksmaintenance' "
            "AND name = 'stage_waiting'"
        )
        cr.execute("DELETE FROM maintenance_stage WHERE id = %s", (waiting_id,))
