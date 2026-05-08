# -*- coding: utf-8 -*-
"""Extend maintenance.request as a helpdesk-style ticket with photos."""

import logging
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class MaintenanceRequest(models.Model):
    """Helpdesk-style maintenance ticket with photo attachments.

    Adds location tracking, multiple photos, submitter info,
    and resolution notes to the base maintenance request.
    """
    _inherit = "maintenance.request"

    # ------------------------------------------------------------------
    # Ticket fields
    # ------------------------------------------------------------------
    x_location_id = fields.Many2one(
        "maintenance.location",
        string="Location",
        help="Where in the lodge is the issue?",
    )
    x_location_detail = fields.Char(
        string="Location Detail",
        help="Additional location info, e.g. 'south wall near exit sign'.",
    )
    x_ticket_type = fields.Selection(
        [
            ("repair", "Repair Needed"),
            ("safety", "Safety Hazard"),
            ("cleaning", "Cleaning / Janitorial"),
            ("electrical", "Electrical"),
            ("plumbing", "Plumbing"),
            ("hvac", "HVAC / Climate"),
            ("exterior", "Exterior / Grounds"),
            ("other", "Other"),
        ],
        string="Issue Type",
        default="repair",
    )

    # Photo attachments — up to 5 images displayed inline
    x_photo_1 = fields.Image(
        string="Photo 1",
        max_width=1920,
        max_height=1920,
    )
    x_photo_2 = fields.Image(
        string="Photo 2",
        max_width=1920,
        max_height=1920,
    )
    x_photo_3 = fields.Image(
        string="Photo 3",
        max_width=1920,
        max_height=1920,
    )
    x_photo_4 = fields.Image(
        string="Photo 4",
        max_width=1920,
        max_height=1920,
    )
    x_photo_5 = fields.Image(
        string="Photo 5",
        max_width=1920,
        max_height=1920,
    )

    # Submitter (for public submissions without Odoo login)
    x_submitter_name = fields.Char(
        string="Submitted By",
        help="Name of the person who reported the issue.",
    )
    x_submitter_email = fields.Char(
        string="Submitter Email",
    )
    x_submitter_phone = fields.Char(
        string="Submitter Phone",
    )

    # Resolution
    x_resolution_notes = fields.Html(
        string="Resolution Notes",
        help="What was done to resolve the issue.",
    )
    x_resolution_date = fields.Date(
        string="Resolved Date",
        readonly=True,
        copy=False,
    )
    x_estimated_cost = fields.Monetary(
        string="Estimated Cost",
        currency_field="x_currency_id",
    )
    x_actual_cost = fields.Monetary(
        string="Actual Cost",
        currency_field="x_currency_id",
    )
    x_currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )

    # ------------------------------------------------------------------
    # Stage transition — auto-set resolution date
    # ------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        if "stage_id" in vals:
            stage = self.env["maintenance.stage"].browse(vals["stage_id"])
            if stage.done:
                for rec in self:
                    if not rec.x_resolution_date:
                        rec.x_resolution_date = fields.Date.today()
        return res
