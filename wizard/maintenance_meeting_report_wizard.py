# -*- coding: utf-8 -*-
"""Wizard for Trustee meeting maintenance report."""

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class MaintenanceMeetingReportWizard(models.TransientModel):
    """Generate a meeting-ready PDF listing open and recently closed tickets."""
    _name = "maintenance.meeting.report.wizard"
    _description = "Maintenance Meeting Report Wizard"

    date_from = fields.Date(
        string="Period Start",
        required=True,
        default=lambda self: date.today().replace(day=1),
    )
    date_to = fields.Date(
        string="Period End",
        required=True,
        default=fields.Date.today,
    )

    def action_print_report(self):
        """Generate the HTML meeting report."""
        return self.env.ref(
            "elksmaintenance.action_report_meeting"
        ).report_action(self)

    def action_print_report_pdf(self):
        """Generate the PDF meeting report."""
        return self.env.ref(
            "elksmaintenance.action_report_meeting_pdf"
        ).report_action(self)

    def _get_report_data(self):
        """Gather ticket data for the report template.

        Returns a dict with:
        - open_tickets: all currently open tickets
        - closed_tickets: tickets closed within the date range
        - open_count: number of open tickets
        - closed_count: number of tickets closed this period
        """
        Request = self.env["maintenance.request"].sudo()
        Stage = self.env["maintenance.stage"].sudo()

        # Find done stages
        done_stages = Stage.search([("done", "=", True)])
        open_stages = Stage.search([("done", "=", False)])

        open_tickets = Request.search(
            [("stage_id", "in", open_stages.ids)],
            order="priority desc, request_date asc",
        )

        closed_tickets = Request.search(
            [
                ("stage_id", "in", done_stages.ids),
                ("close_date", ">=", self.date_from),
                ("close_date", "<=", self.date_to),
            ],
            order="close_date desc",
        )

        return {
            "open_tickets": open_tickets,
            "closed_tickets": closed_tickets,
            "open_count": len(open_tickets),
            "closed_count": len(closed_tickets),
        }
