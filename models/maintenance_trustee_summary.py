# -*- coding: utf-8 -*-
"""Read-only summary model for the Trustee Dashboard kanban.

Aggregates open / closed counts, total hours, and average time-to-close
per (trustee, lodge year) so the dashboard kanban can render one tile
per trustee with stat widgets — without each card running its own
read_group on the maintenance ticket table.

Stored as a Postgres VIEW (``_auto = False``), recomputed live on each
query.  Cheap because ``maintenance_request.x_trustee_id``,
``x_is_closed``, and ``x_lodge_year`` are all indexed and stored.
"""
from odoo import fields, models, tools


class TrusteeMaintenanceSummary(models.Model):
    _name = "elks.maintenance.trustee.summary"
    _description = "Maintenance — Trustee Summary"
    _auto = False
    _rec_name = "trustee_id"
    _order = "open_count desc, trustee_id"

    trustee_id = fields.Many2one("res.partner", string="Trustee", readonly=True)
    lodge_year = fields.Char(readonly=True)
    open_count = fields.Integer("Open Tickets", readonly=True)
    closed_count = fields.Integer("Closed Tickets", readonly=True)
    total_count = fields.Integer("Total Tickets", readonly=True)
    close_rate = fields.Float(
        "Close Rate (%)", readonly=True,
        help="Percentage of tickets the trustee has closed this lodge year.",
    )
    total_hours = fields.Float("Hours Logged", readonly=True)
    avg_resolution_days = fields.Float(
        "Avg Days to Close", readonly=True,
        help="Average wall-clock days between request_date and "
             "x_resolution_date across closed tickets.",
    )

    def init(self):
        # Odoo 19 deprecated ``self._cr`` — use ``self.env.cr``.
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY mr.x_trustee_id, mr.x_lodge_year
                    ) AS id,
                    mr.x_trustee_id AS trustee_id,
                    mr.x_lodge_year AS lodge_year,
                    COUNT(*) FILTER (WHERE NOT mr.x_is_closed) AS open_count,
                    COUNT(*) FILTER (WHERE mr.x_is_closed) AS closed_count,
                    COUNT(*) AS total_count,
                    CASE WHEN COUNT(*) = 0 THEN 0
                         ELSE 100.0 *
                              COUNT(*) FILTER (WHERE mr.x_is_closed)
                              / COUNT(*)
                    END AS close_rate,
                    COALESCE(SUM(mr.x_total_hours), 0) AS total_hours,
                    AVG(
                        EXTRACT(EPOCH FROM
                            (mr.x_resolution_date::timestamp
                             - mr.request_date::timestamp)
                        ) / 86400.0
                    ) FILTER (
                        WHERE mr.x_is_closed
                          AND mr.x_resolution_date IS NOT NULL
                          AND mr.request_date IS NOT NULL
                    ) AS avg_resolution_days
                FROM maintenance_request mr
                WHERE mr.x_trustee_id IS NOT NULL
                  AND mr.x_lodge_year IS NOT NULL
                GROUP BY mr.x_trustee_id, mr.x_lodge_year
            )
            """
        )
