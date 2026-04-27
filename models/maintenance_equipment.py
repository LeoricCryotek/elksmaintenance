# -*- coding: utf-8 -*-
"""Extends ``maintenance.equipment`` with Elks-specific asset fields.

Adds:
 * Hierarchy (parent / child equipment)
 * Square footage (for cost-per-sq-ft tracking)
 * Asset class (Building / System / Component)
 * Condition rating (1-5)
 * Links back to deferred maintenance requests for quick navigation
"""
from odoo import api, fields, models


ASSET_CLASS = [
    ('building', 'Building'),
    ('area', 'Area / Zone'),
    ('system', 'System'),
    ('component', 'Component'),
    ('equipment', 'Equipment'),
]

CONDITION = [
    ('1', '1 - Excellent'),
    ('2', '2 - Good'),
    ('3', '3 - Fair'),
    ('4', '4 - Poor'),
    ('5', '5 - Failing / At Risk'),
]


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    # Hierarchy
    parent_equipment_id = fields.Many2one(
        "maintenance.equipment", string="Parent Asset",
        ondelete="set null", index=True,
        help="The asset this item belongs to in the building hierarchy. "
             "Example: 'Women's South Bathroom' → parent is 'Main Floor'. "
             "Setting a parent lets deferred maintenance costs roll up "
             "to the parent area, and builds the Full Path breadcrumb. "
             "Leave blank for top-level assets like the building itself.",
    )
    child_equipment_ids = fields.One2many(
        "maintenance.equipment", "parent_equipment_id",
        string="Sub-Assets",
        help="Assets nested under this one. For an area like a bathroom, "
             "sub-assets might include fixtures, plumbing, lighting, etc. "
             "Each sub-asset's deferred maintenance backlog rolls up to "
             "this parent in the Deferred Maintenance Summary section.",
    )

    # Elks-specific
    x_asset_class = fields.Selection(
        ASSET_CLASS, string="Asset Class", default='component', index=True,
        help="How this asset fits in the building hierarchy. Use 'Building' "
             "for the lodge itself, 'Area / Zone' for rooms and spaces like "
             "bathrooms or the ballroom, 'System' for HVAC / plumbing / "
             "electrical, 'Component' for individual parts of a system, and "
             "'Equipment' for standalone items like appliances or furniture. "
             "This drives how reports group assets and how deferred costs "
             "roll up to parent areas.",
    )
    x_sq_ft = fields.Integer(
        "Square Footage",
        help="The floor area this asset covers, in square feet. Used in the "
             "Trustee Dashboard to compute maintenance cost per square foot. "
             "For rooms/zones, enter the actual room area. For systems or "
             "components, leave at 0 — the parent area's footage is used "
             "for cost-per-sqft calculations instead.",
    )
    x_condition = fields.Selection(
        CONDITION, string="Condition", default='3',
        help="Current physical condition on a 1–5 scale:\n"
             "  1 – Excellent: New or like-new, no work needed\n"
             "  2 – Good: Minor wear, cosmetic only\n"
             "  3 – Fair: Working but showing age, plan maintenance\n"
             "  4 – Poor: Functional issues, needs attention soon\n"
             "  5 – Failing / At Risk: Broken or dangerous, urgent\n\n"
             "Items rated 4 or 5 appear in the 'Poor / Failing' filter "
             "and are flagged for Trustee review. Update this after each "
             "inspection. Not every asset needs a condition — areas like "
             "bathrooms can stay at the default '3 – Fair' and use the "
             "condition of their child components instead.",
    )
    x_last_inspection_date = fields.Date(
        "Last Inspection",
        help="Date this asset was last visually inspected or assessed. "
             "Helps Trustees identify assets that haven't been reviewed "
             "recently. A monthly cron job can flag overdue inspections.",
    )
    x_replacement_cost = fields.Monetary(
        "Replacement Cost",
        currency_field='currency_id',
        help="Estimated cost to fully replace this asset today. Used in "
             "capital planning reports to prioritize spending. For areas "
             "like bathrooms, this would be a full renovation cost. For "
             "equipment, it's the purchase + install cost. Enter $0 if "
             "not applicable (e.g., the building shell itself).",
    )
    x_install_date = fields.Date(
        "Installation Date",
        help="When this asset was originally installed or the room was "
             "last renovated. Combined with Expected Life to estimate "
             "when replacement is due. Leave blank if unknown.",
    )
    x_expected_life_years = fields.Integer(
        "Expected Life (Years)",
        help="How many years this asset should last from installation. "
             "Examples: Roof = 25, HVAC = 15, Carpet = 7, Paint = 5. "
             "When Install Date + Expected Life < today, the asset is "
             "past its useful life and should be reviewed for replacement. "
             "Leave at 0 for areas/zones that don't have a lifespan.",
    )

    # Override base maintenance fields with useful tooltips
    expected_mtbf = fields.Integer(
        string="Expected Mean Time Between Failure",
        help="How many days you expect this asset to operate between "
             "breakdowns, based on manufacturer specs or experience. "
             "Example: an HVAC unit might average 365 days between "
             "failures. For rooms/areas this doesn't apply — leave at 0. "
             "The system uses this to estimate when the next failure "
             "might occur (Last Failure Date + this value).",
    )
    mtbf = fields.Integer(
        compute="_compute_maintenance_request",
        string="Actual MTBF",
        help="The actual average number of days between corrective "
             "maintenance requests for this asset, computed automatically "
             "from your maintenance history. A declining number means the "
             "asset is breaking down more frequently — consider replacement. "
             "Only counts completed corrective (repair) requests.",
    )
    mttr = fields.Integer(
        compute="_compute_maintenance_request",
        string="Mean Time To Repair",
        help="Average number of days from when a repair is reported to "
             "when it's marked complete. Computed from your maintenance "
             "history. A high number may indicate slow vendor response, "
             "parts availability issues, or low priority assignments.",
    )
    estimated_next_failure = fields.Date(
        compute="_compute_maintenance_request",
        string="Estimated Next Failure",
        help="Predicted date of the next breakdown, calculated as: "
             "Latest Failure Date + Actual MTBF. This is a rough guide — "
             "use it to schedule preventative maintenance before the "
             "predicted failure. Shows nothing if there's no failure "
             "history yet.",
    )
    latest_failure_date = fields.Date(
        compute="_compute_maintenance_request",
        string="Latest Failure",
        help="The most recent date a corrective maintenance request was "
             "filed for this asset. Computed from your maintenance "
             "history. If blank, no repair has been logged yet.",
    )

    # Aggregates
    x_deferred_request_count = fields.Integer(
        "Deferred Work Count",
        compute="_compute_deferred_totals",
        help="Number of open 'Deferred Maintenance' requests linked to "
             "this asset that haven't been completed or cancelled yet. "
             "Click 'View Deferred Work' to see and manage them.",
    )
    x_deferred_backlog_amount = fields.Monetary(
        "Deferred Backlog $",
        compute="_compute_deferred_totals",
        currency_field='currency_id',
        help="Total estimated cost of all open deferred maintenance "
             "requests for this asset. This rolls up to the Trustee "
             "Dashboard's overall Deferred Backlog figure. Use this to "
             "see how much deferred work is piling up on a single asset.",
    )

    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id,
    )

    # Breadcrumb-style name for hierarchy display.
    # recursive=True tells Odoo this compute reads its own model via the
    # parent chain, which would otherwise trigger a dependency warning.
    full_path = fields.Char(
        "Full Path", compute="_compute_full_path", store=True,
        recursive=True,
    )

    @api.depends("name", "parent_equipment_id",
                 "parent_equipment_id.full_path")
    def _compute_full_path(self):
        for rec in self:
            if rec.parent_equipment_id and rec.parent_equipment_id.full_path:
                rec.full_path = f"{rec.parent_equipment_id.full_path} / {rec.name or ''}"
            else:
                rec.full_path = rec.name or ''

    def _compute_deferred_totals(self):
        Request = self.env['maintenance.request']
        for rec in self:
            requests = Request.search([
                ('equipment_id', '=', rec.id),
                ('x_request_type', '=', 'deferred'),
                ('stage_id.done', '=', False),
            ])
            rec.x_deferred_request_count = len(requests)
            rec.x_deferred_backlog_amount = sum(
                requests.mapped('x_estimated_cost')
            )

    def action_view_deferred_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f"Deferred Work: {self.name}",
            'res_model': 'maintenance.request',
            'view_mode': 'list,kanban,form,pivot,graph',
            'domain': [
                ('equipment_id', '=', self.id),
                ('x_request_type', '=', 'deferred'),
            ],
            'context': {'default_equipment_id': self.id},
        }
