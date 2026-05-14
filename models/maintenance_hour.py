# -*- coding: utf-8 -*-
"""Hour logging for maintenance tickets.

Each line records hours worked by a volunteer/trustee on a specific date,
enabling both log-as-you-go tracking and a close-time total.
"""
from odoo import api, fields, models


class MaintenanceHour(models.Model):
    _name = "elks.maintenance.hour"
    _description = "Maintenance Ticket Hours"
    _order = "date desc, id desc"

    request_id = fields.Many2one(
        "maintenance.request", string="Ticket",
        required=True, ondelete="cascade", index=True,
    )
    worker_id = fields.Many2one(
        "res.partner", string="Volunteer",
        required=True, index=True,
        help="The person who performed the work.",
    )
    date = fields.Date(
        "Date", required=True, default=fields.Date.context_today,
    )
    hours = fields.Float(
        "Hours", required=True, default=0.0,
    )
    description = fields.Char(
        "Work Description",
        help="Brief note of what was done.",
    )
    request_stage_id = fields.Many2one(
        related="request_id.stage_id", string="Ticket Stage",
        store=True, readonly=True,
    )
