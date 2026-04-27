# -*- coding: utf-8 -*-
"""Adds a building square-footage setting used for cost-per-sq-ft reporting."""
import datetime

from odoo import api, fields, models


class ElksLodgeSettings(models.Model):
    _inherit = "elks.lodge.settings"

    x_total_sq_ft = fields.Integer(
        "Total Lodge Sq Ft", default=45000,
        help="Total square footage of the lodge building(s). "
             "Used to compute cost per square foot on the maintenance dashboard.",
    )

    x_maintenance_cost_ytd = fields.Monetary(
        "Maintenance Cost YTD",
        compute="_compute_maintenance_cost",
        currency_field='currency_id',
    )
    x_maintenance_cost_per_sqft_ytd = fields.Float(
        "Cost per Sq Ft (YTD)",
        compute="_compute_maintenance_cost",
        digits=(16, 2),
    )
    x_deferred_backlog_total = fields.Monetary(
        "Deferred Backlog Total",
        compute="_compute_maintenance_cost",
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id,
    )

    def action_open_trustee_dashboard(self):
        """Open (or create) the lodge-settings singleton on the dashboard view."""
        settings = self.search([], limit=1)
        if not settings:
            settings = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trustee Dashboard',
            'res_model': 'elks.lodge.settings',
            'res_id': settings.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'elksmaintenance.view_elks_lodge_settings_dashboard'
            ).id,
            'target': 'current',
        }

    def _compute_maintenance_cost(self):
        Request = self.env['maintenance.request']
        today = datetime.date.today()
        # Elks fiscal year: Apr 1 – Mar 31
        if today.month >= 4:
            fy_start = datetime.date(today.year, 4, 1)
        else:
            fy_start = datetime.date(today.year - 1, 4, 1)

        for rec in self:
            completed = Request.search([
                ('stage_id.done', '=', True),
                ('x_actual_cost', '>', 0),
                ('close_date', '>=', fy_start),
            ])
            ytd = sum(completed.mapped('x_actual_cost'))
            rec.x_maintenance_cost_ytd = ytd
            sqft = rec.x_total_sq_ft or 1
            rec.x_maintenance_cost_per_sqft_ytd = ytd / sqft

            backlog = Request.search([
                ('x_request_type', '=', 'deferred'),
                ('stage_id.done', '=', False),
            ])
            rec.x_deferred_backlog_total = sum(backlog.mapped('x_estimated_cost'))
