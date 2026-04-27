# -*- coding: utf-8 -*-
"""Extends ``maintenance.request`` with Trustee-oriented deferred
maintenance fields, budget sync, and audit trail."""
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError


REQUEST_TYPE = [
    ('repair', 'Repair'),
    ('preventative', 'Preventative'),
    ('deferred', 'Deferred Maintenance'),
    ('inspection', 'Inspection'),
    ('capital', 'Capital Project'),
]

RISK_TYPE = [
    ('safety', 'Safety'),
    ('revenue', 'Revenue Impact'),
    ('compliance', 'Compliance / Code'),
    ('operational', 'Operational'),
    ('cosmetic', 'Cosmetic'),
]

FUNDING_SOURCE = [
    ('trustees', 'Trustees / Operations'),
    ('house', 'House Committee'),
    ('capital', 'Capital Campaign'),
    ('grant', 'Grant'),
    ('insurance', 'Insurance'),
    ('other', 'Other'),
]


def _year_choices(self):
    """Selection callable for target year — 5 years back, 10 forward."""
    today = date.today()
    return [(str(y), str(y)) for y in range(today.year - 2, today.year + 11)]


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    x_request_type = fields.Selection(
        REQUEST_TYPE, string="Request Type", default='repair',
        required=True, tracking=True, index=True,
        help="Categorizes this work request:\n"
             "  • Repair — Something is broken and needs fixing now\n"
             "  • Preventative — Scheduled upkeep (filter changes, etc.)\n"
             "  • Deferred Maintenance — Known work postponed to a future "
             "budget year. These appear in the Deferred Backlog report and "
             "roll up to the Trustee Dashboard.\n"
             "  • Inspection — Walk-through or assessment, no repair work\n"
             "  • Capital Project — Major improvement or addition (new roof, "
             "renovation) tracked for capital planning\n\n"
             "Choose 'Deferred Maintenance' for any work the Trustees have "
             "acknowledged but not yet funded. The system auto-tags these "
             "and tracks them separately for Grand Lodge reporting.",
    )
    x_priority_score = fields.Integer(
        "Priority Score (1–15)", default=5, tracking=True, index=True,
        help="How urgently this work needs to happen, scored 1–15.\n"
             "  1–4: Low — cosmetic or far-future items\n"
             "  5–8: Medium — plan within 1–2 years\n"
             "  9–11: High — should be in this year's budget\n"
             "  12–15: Critical — safety/compliance, needs immediate action\n\n"
             "Scores 12+ automatically alert the Trustee team and create "
             "a follow-up activity. Use the 'Recalculate Priority' button "
             "to auto-score based on risk type, estimated cost, and how "
             "soon the target year is.",
    )
    x_estimated_cost = fields.Monetary(
        "Estimated Cost", currency_field='currency_id', tracking=True,
        help="Best estimate of what this work will cost. Get a contractor "
             "quote if possible. This drives the Deferred Backlog total on "
             "the Trustee Dashboard and is used in the priority scoring "
             "formula. When the item is approved, a draft budget entry is "
             "created in the FRS for this amount.",
    )
    x_actual_cost = fields.Monetary(
        "Actual Cost", currency_field='currency_id', tracking=True,
        help="What the work actually cost after completion. Enter this "
             "when the invoice is paid. The system computes a Variance "
             "(Actual minus Estimated) so Trustees can track budgeting "
             "accuracy over time. A reminder appears in chatter when an "
             "item is marked Complete without an actual cost.",
    )
    x_cost_variance = fields.Monetary(
        "Variance", compute="_compute_variance", store=True,
        currency_field='currency_id',
        help="Actual Cost minus Estimated Cost. A negative number means "
             "the work came in under budget. A positive number means it "
             "went over. Computed automatically — you cannot edit this.",
    )
    x_target_year = fields.Selection(
        selection=_year_choices,
        string="Target Year", index=True, tracking=True,
        help="The fiscal year (Apr–Mar) you plan to fund and complete "
             "this work. Used in the 5-Year Capital Plan report and the "
             "priority scoring formula. Items targeted for the current "
             "year score higher in priority. Items with no target year "
             "are flagged monthly as stale by the automated review job.",
    )
    x_risk_type = fields.Selection(
        RISK_TYPE, string="Risk Type", default='operational',
        index=True, tracking=True,
        help="What kind of risk this issue poses if left unaddressed:\n"
             "  • Safety — Could injure someone (tripping hazard, "
             "electrical, fire). Weights highest in priority scoring.\n"
             "  • Compliance / Code — Violates building code, ADA, fire "
             "marshal, or insurance requirements. Also weights highest.\n"
             "  • Revenue Impact — Affects the lodge's ability to earn "
             "(broken bar equipment, unusable rental space).\n"
             "  • Operational — Makes things harder but not dangerous "
             "(slow drain, sticky door).\n"
             "  • Cosmetic — Appearance only (peeling paint, stained "
             "ceiling tile). Lowest priority weight.\n\n"
             "When an item enters the Deferred Backlog, a color-coded "
             "tag matching this risk type is auto-applied.",
    )
    x_funding_source = fields.Selection(
        FUNDING_SOURCE, string="Funding Source", default='trustees',
        index=True, tracking=True,
        help="Where the money for this work will come from:\n"
             "  • Trustees / Operations — Normal operating budget\n"
             "  • House Committee — Funded by the House Committee budget\n"
             "  • Capital Campaign — Special fundraising drive\n"
             "  • Grant — ENF, state association, or external grant\n"
             "  • Insurance — Covered by an insurance claim\n"
             "  • Other — Donation, volunteer labor, etc.\n\n"
             "This is logged in the budget entry when approved and shows "
             "in the Capital Plan report for planning purposes.",
    )

    # Tags (separate from core category_id which is a read-only related
    # field from equipment).  Used for auto-tagging deferred items and
    # classifying by risk/category.
    x_tag_ids = fields.Many2many(
        'maintenance.equipment.category',
        'maintenance_request_tag_rel',
        'request_id', 'tag_id',
        string='Tags',
    )

    # FRS integration
    x_elks_account_id = fields.Many2one(
        "elks.account", string="GL Account",
        help="The Elks Uniform Chart of Accounts line this expense will "
             "be charged to. Only expense and fixed-asset accounts are "
             "shown. Common choices for maintenance:\n"
             "  • 39301 – Building Repairs\n"
             "  • 39302 – Equipment Repairs\n"
             "  • 39501 – Building Improvements (capital)\n\n"
             "Required before the system can auto-create a budget entry "
             "when the item moves to Approved. The department is pulled "
             "automatically from the account you choose.",
        domain="[('account_type', 'in', ['expense', 'fixed_asset'])]",
        tracking=True,
    )
    x_elks_department_id = fields.Many2one(
        "elks.department", string="Elks Department",
        related="x_elks_account_id.department_id", store=True,
        help="Auto-filled from the GL Account's department. This groups "
             "maintenance costs by department in the Capital Plan report "
             "(e.g., Building, House Committee, Lodge Room).",
    )
    x_analytic_entry_id = fields.Many2one(
        "elks.journal.entry", string="Budget Entry",
        readonly=True, copy=False,
        help="When a deferred item is moved to the 'Approved (Budgeted)' "
             "stage, the system auto-creates a draft journal entry in the "
             "FRS module. This entry debits the GL Account above and "
             "credits an offset liability or equity account. The entry "
             "stays in Draft until a Secretary posts it. Click 'View "
             "Budget Entry' to open it.",
    )

    # Display-friendly aggregates for the equipment hierarchy
    x_equipment_sq_ft = fields.Integer(
        related="equipment_id.x_sq_ft", store=True,
    )
    x_equipment_path = fields.Char(
        related="equipment_id.full_path", store=True,
        string="Asset Path",
    )

    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id,
    )

    # Stage helpers
    x_is_deferred_stage = fields.Boolean(
        compute="_compute_stage_flags", store=True, index=True,
    )
    x_is_approved_stage = fields.Boolean(
        compute="_compute_stage_flags", store=True, index=True,
    )

    @api.depends("stage_id", "stage_id.name")
    def _compute_stage_flags(self):
        for rec in self:
            stage_name = (rec.stage_id.name or '').lower()
            rec.x_is_deferred_stage = 'deferr' in stage_name or 'backlog' in stage_name
            rec.x_is_approved_stage = 'approv' in stage_name or 'budgeted' in stage_name

    @api.depends("x_estimated_cost", "x_actual_cost")
    def _compute_variance(self):
        for rec in self:
            rec.x_cost_variance = (rec.x_actual_cost or 0.0) - (rec.x_estimated_cost or 0.0)

    # -----------------------------------------------------------------
    # Write / stage transitions: handle auto-tag + budget sync
    # -----------------------------------------------------------------
    def write(self, vals):
        # Capture old stages for comparison
        old_stage_map = {r.id: r.stage_id for r in self}

        res = super().write(vals)

        if 'stage_id' in vals:
            for rec in self:
                old_stage = old_stage_map.get(rec.id)
                rec._handle_stage_transition(old_stage, rec.stage_id)

        # High priority alerting on changed priority
        if 'x_priority_score' in vals:
            for rec in self:
                if rec.x_priority_score and rec.x_priority_score >= 12:
                    rec._notify_high_priority()

        return res

    def _handle_stage_transition(self, old_stage, new_stage):
        """Called when stage_id changes.  Drives auto-tag + budget sync."""
        self.ensure_one()
        new_name = (new_stage.name or '').lower() if new_stage else ''

        # Auto-tag deferred items
        if 'deferr' in new_name or 'backlog' in new_name:
            tag = self.env.ref(
                'elksmaintenance.maintenance_tag_deferred',
                raise_if_not_found=False,
            )
            if tag and tag not in self.x_tag_ids:
                self.x_tag_ids = [(4, tag.id)]

            # Also add a risk-type tag for quick visual identification
            risk_tag_map = {
                'safety': 'elksmaintenance.maintenance_tag_safety',
                'compliance': 'elksmaintenance.maintenance_tag_compliance',
                'revenue': 'elksmaintenance.maintenance_tag_revenue',
                'cosmetic': 'elksmaintenance.maintenance_tag_cosmetic',
            }
            risk_tag_xmlid = risk_tag_map.get(self.x_risk_type)
            if risk_tag_xmlid:
                risk_tag = self.env.ref(risk_tag_xmlid, raise_if_not_found=False)
                if risk_tag and risk_tag not in self.x_tag_ids:
                    self.x_tag_ids = [(4, risk_tag.id)]

            self.message_post(
                body=(
                    f"<strong>Moved to Deferred Backlog</strong><br/>"
                    f"Estimated Cost: ${self.x_estimated_cost:,.2f}<br/>"
                    f"Priority: {self.x_priority_score}<br/>"
                    f"Target Year: {self.x_target_year or 'Unscheduled'}<br/>"
                    f"Risk: {dict(RISK_TYPE).get(self.x_risk_type, '')}"
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

        # Approval → create draft budget entry in elksfrs
        if ('approv' in new_name or 'budgeted' in new_name):
            self._create_budget_entry()

        # Completion → record actual cost reminder
        if new_stage and new_stage.done:
            if not self.x_actual_cost:
                self.message_post(
                    body=(
                        "<strong>Completed</strong> — please record the "
                        "actual cost for variance reporting."
                    ),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )

    def _notify_high_priority(self):
        """Post a chatter note (and activity) for high-priority items."""
        self.ensure_one()
        self.message_post(
            body=(
                f"<strong>⚠️ High Priority Alert</strong><br/>"
                f"Priority Score: {self.x_priority_score} (≥ 12)<br/>"
                f"Risk: {dict(RISK_TYPE).get(self.x_risk_type, '')}<br/>"
                f"Estimated Cost: ${self.x_estimated_cost:,.2f}<br/>"
                f"Trustees should review at the next meeting."
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        # Create an activity for the maintenance team lead
        try:
            team = self.maintenance_team_id
            user = team.team_leader_id if team else self.env.user
            if user:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=f"Review high-priority maintenance: {self.name}",
                    note=f"Priority {self.x_priority_score} — ${self.x_estimated_cost:,.2f}",
                    user_id=user.id,
                )
        except Exception:
            # Don't block the save if activity creation fails
            pass

    def _create_budget_entry(self):
        """When approved, create a draft analytic/budget entry in elksfrs.

        This is a DRAFT journal entry so the Trustees can review before
        posting.  It debits the chosen expense account and credits the
        default budget offset account (usually 29xxx Equity or an
        'Approved Maintenance Commitments' liability account).
        """
        self.ensure_one()

        if self.x_analytic_entry_id:
            # Already have an entry — don't duplicate
            return

        if not self.x_estimated_cost or self.x_estimated_cost <= 0:
            self.message_post(
                body=(
                    "<strong>Approved</strong> — no budget entry created: "
                    "estimated cost is $0."
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            return

        if not self.x_elks_account_id:
            self.message_post(
                body=(
                    "<strong>Approved</strong> — cannot create budget "
                    "entry: no GL Account is set on this item."
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            return

        Account = self.env['elks.account']
        JournalEntry = self.env['elks.journal.entry']

        # Find an offset account: prefer an "Approved Maintenance Commitments"
        # liability, fall back to a generic equity/retained earnings account.
        offset = Account.search([
            ('name', 'ilike', 'maintenance commit'),
        ], limit=1)
        if not offset:
            offset = Account.search([
                ('account_type', '=', 'liability'),
            ], limit=1)
        if not offset:
            offset = Account.search([
                ('account_type', '=', 'equity'),
            ], limit=1)

        if not offset:
            self.message_post(
                body=(
                    "<strong>Approved</strong> — no offset account found "
                    "for budget entry. Please set one up in elks.account."
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            return

        entry_vals = {
            'date': fields.Date.context_today(self),
            'memo': (
                f"Budget commitment: {self.name} "
                f"(Maintenance #{self.id})"
            ),
            'line_ids': [
                (0, 0, {
                    'account_id': self.x_elks_account_id.id,
                    'debit': self.x_estimated_cost,
                    'credit': 0.0,
                    'memo': f"Approved maintenance: {self.name}",
                }),
                (0, 0, {
                    'account_id': offset.id,
                    'debit': 0.0,
                    'credit': self.x_estimated_cost,
                    'memo': f"Offset: {self.name}",
                }),
            ],
        }
        entry = JournalEntry.create(entry_vals)
        self.x_analytic_entry_id = entry.id

        self.message_post(
            body=(
                f"<strong>Approved & Budgeted</strong><br/>"
                f"Draft budget entry <a href='#' data-oe-model='elks.journal.entry' "
                f"data-oe-id='{entry.id}'>{entry.entry_number}</a> created.<br/>"
                f"Amount: ${self.x_estimated_cost:,.2f}<br/>"
                f"GL: {self.x_elks_account_id.code} {self.x_elks_account_id.name}<br/>"
                f"Offset: {offset.code} {offset.name}<br/>"
                f"Funding: {dict(FUNDING_SOURCE).get(self.x_funding_source, '')}"
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

    # -----------------------------------------------------------------
    # Quick actions
    # -----------------------------------------------------------------
    def action_view_budget_entry(self):
        self.ensure_one()
        if not self.x_analytic_entry_id:
            raise UserError(_("No budget entry exists for this item."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'elks.journal.entry',
            'res_id': self.x_analytic_entry_id.id,
            'view_mode': 'form',
        }

    @api.model
    def _cron_flag_stale_deferred(self):
        """Monthly scheduled job: flag deferred items with missing or
        past target years, and remind the Trustee team."""
        today = date.today()
        # No target year → stale
        stale = self.search([
            ('x_request_type', '=', 'deferred'),
            ('x_is_deferred_stage', '=', True),
            '|',
            ('x_target_year', '=', False),
            ('x_target_year', '<', str(today.year)),
        ])
        for rec in stale:
            rec.message_post(
                body=(
                    "<strong>Monthly review reminder</strong><br/>"
                    "This deferred item has no target year set or the "
                    "target year has passed. Please re-prioritize or "
                    "advance to Approved."
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_recalculate_priority(self):
        """Simple priority formula:
        risk(3/2/1) + cost-band(1-5) + age-band(1-5)."""
        risk_weight = {
            'safety': 3, 'compliance': 3,
            'revenue': 2, 'operational': 2,
            'cosmetic': 1,
        }
        for rec in self:
            r = risk_weight.get(rec.x_risk_type, 1)
            cost = rec.x_estimated_cost or 0
            if cost >= 50000:
                c = 5
            elif cost >= 25000:
                c = 4
            elif cost >= 10000:
                c = 3
            elif cost >= 2500:
                c = 2
            else:
                c = 1
            # Age band from target year
            try:
                ty = int(rec.x_target_year) if rec.x_target_year else 0
                yrs_out = ty - date.today().year
                if yrs_out <= 0:
                    a = 5
                elif yrs_out == 1:
                    a = 4
                elif yrs_out == 2:
                    a = 3
                elif yrs_out == 3:
                    a = 2
                else:
                    a = 1
            except (ValueError, TypeError):
                a = 3
            score = min(15, max(1, r * 2 + c + a))
            rec.x_priority_score = score
