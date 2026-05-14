# -*- coding: utf-8 -*-
"""Configurable issue type for maintenance tickets.

Replaces the hard-coded ``x_ticket_type`` Selection field.  Lodges can
add/rename/archive types (Plumbing → Plumbing & Sewer, add "Septic", etc.)
without code changes.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MaintenanceIssueType(models.Model):
    """A named category for what a maintenance ticket is about."""
    _name = "maintenance.issue.type"
    _description = "Maintenance Issue Type"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        help="Short stable identifier used by automations and "
             "legacy reports.  Safe to leave blank — uniqueness is "
             "only enforced when a code is set.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(
        help="Color for kanban/list badges (0–11).",
    )
    note = fields.Text(string="Description")

    # Python-level "partial unique" — a Postgres unique CONSTRAINT
    # can't carry a WHERE clause (only unique INDEXes can), so we
    # check it in Python instead.  Trade-off: a tiny race window
    # under concurrent inserts where two empty-code rows could slip
    # in — acceptable for a config table edited by humans, and the
    # name field is required so duplicates are easy to spot.
    @api.constrains("code")
    def _check_code_unique(self):
        for rec in self:
            if not rec.code:
                continue
            duplicate = self.search_count([
                ("code", "=", rec.code),
                ("id", "!=", rec.id),
            ])
            if duplicate:
                raise ValidationError(_(
                    "Issue Type code %(code)r is already used. "
                    "Codes must be unique when set.",
                    code=rec.code,
                ))
