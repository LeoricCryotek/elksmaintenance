# -*- coding: utf-8 -*-
"""Lodge location model for maintenance tickets."""

from odoo import fields, models


class MaintenanceLocation(models.Model):
    """A named area within the lodge building.

    Used as a simple dropdown on maintenance tickets so Trustees
    can quickly filter and sort issues by location.
    """
    _name = "maintenance.location"
    _description = "Lodge Location"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Text(string="Description")
