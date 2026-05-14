# -*- coding: utf-8 -*-
"""Wizard shown when closing a maintenance ticket.

Lets the user confirm/adjust total hours before the ticket moves
to Done and charity volunteer hours are created.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CloseTicketWizard(models.TransientModel):
    _name = "elks.close.ticket.wizard"
    _description = "Close Maintenance Ticket"

    request_id = fields.Many2one(
        "maintenance.request", string="Ticket",
        required=True, readonly=True,
    )
    done_stage_id = fields.Many2one(
        "maintenance.stage", string="Done Stage",
        required=True, readonly=True,
    )

    # Pre-filled from logged hours; user can adjust
    hours = fields.Float(
        "Total Hours Worked",
        help="Pre-filled from hour log entries. Adjust if needed.",
    )
    resolution_notes = fields.Html(
        "Resolution Notes",
        help="What was done to resolve the issue?",
    )
    create_charity_hours = fields.Boolean(
        "Create Charity Volunteer Hours",
        default=True,
        help="Automatically create volunteer hour entries under "
             "charity category 9999 (Categories Not Covered).",
    )

    def action_confirm_close(self):
        """Close the ticket, optionally create charity hours."""
        self.ensure_one()
        ticket = self.request_id

        # If user adjusted total hours and there are no logged lines,
        # create a single summary line
        if self.hours > 0 and not ticket.x_hour_line_ids:
            worker = ticket.x_trustee_id or self.env.user.partner_id
            self.env["elks.maintenance.hour"].create({
                "request_id": ticket.id,
                "worker_id": worker.id,
                "date": fields.Date.today(),
                "hours": self.hours,
                "description": _("Hours logged at close"),
            })
        elif self.hours > 0 and ticket.x_hour_line_ids:
            # If adjusted hours differ from logged total, add a
            # correction line for the difference
            logged = sum(ticket.x_hour_line_ids.mapped("hours"))
            diff = self.hours - logged
            if abs(diff) > 0.01:
                worker = ticket.x_trustee_id or self.env.user.partner_id
                self.env["elks.maintenance.hour"].create({
                    "request_id": ticket.id,
                    "worker_id": worker.id,
                    "date": fields.Date.today(),
                    "hours": diff,
                    "description": _("Hours adjustment at close"),
                })

        # Update resolution notes if provided
        if self.resolution_notes:
            ticket.x_resolution_notes = self.resolution_notes

        # Move to done stage (triggers write() → sets resolution date)
        ticket.stage_id = self.done_stage_id

        # Create charity hours
        if self.create_charity_hours and ticket.x_hour_line_ids:
            ticket._create_charity_hours()

        return {"type": "ir.actions.act_window_close"}
