# -*- coding: utf-8 -*-
"""Extend maintenance.request as a helpdesk-style ticket with photos,
trustee assignment, hour tracking, and charity hour integration.
"""

import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MaintenanceRequest(models.Model):
    """Helpdesk-style maintenance ticket with photo attachments,
    trustee/helper assignment, hour logging, and charity integration.
    """
    _inherit = "maintenance.request"

    # ------------------------------------------------------------------
    # Relabel base ``name`` field as "Title" — the base maintenance
    # module ships it as "Subjects" (plural typo), which is confusing
    # in the + Field picker of the website Form builder.
    # ------------------------------------------------------------------
    name = fields.Char(string="Title")

    # ------------------------------------------------------------------
    # Ticket fields
    # ------------------------------------------------------------------
    x_location_id = fields.Many2one(
        "maintenance.location",
        string="Location",
        index=True,
        tracking=True,
        help="Where in the lodge is the issue?",
    )
    x_location_detail = fields.Char(
        string="Location Detail",
        help="Additional location info, e.g. 'south wall near exit sign'.",
    )
    x_ticket_type = fields.Many2one(
        "maintenance.issue.type",
        string="Issue Type",
        ondelete="set null",
        index=True,
        tracking=True,
        default=lambda self: self.env.ref(
            "elksmaintenance.maintenance_issue_type_repair",
            raise_if_not_found=False,
        ),
        help="Pick from the lodge's configurable list of issue types. "
             "Manage the list under Maintenance → Configuration → "
             "Issue Types.",
    )

    # Photos are now stored as chatter attachments on each ticket
    # (unlimited count, drag-drop, gallery preview via mail.thread).
    # The legacy x_photo_1..5 fields were removed in v19.0.4.0; the
    # pre_init / migration hook ports any existing image data into
    # ir.attachment records linked to the ticket.

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
    # Trustee assignment
    # ------------------------------------------------------------------
    # Positions eligible to be the "Assigned Trustee" on a maintenance
    # ticket: full Board of Trustees plus the Exalted Ruler and Secretary
    # (per Danny's choice — lets the ER/Secretary close tickets too).
    _ELIGIBLE_TRUSTEE_POSITIONS = (
        "boardchair", "trustee1y", "trustee2y", "trustee3y",
        "trustee4y", "trustee5y", "exalted_ruler", "secretary",
    )

    x_eligible_trustee_ids = fields.Many2many(
        "res.partner",
        compute="_compute_eligible_trustee_ids",
        string="Eligible Trustees",
        help="Computed list of partners currently holding a Trustee, "
             "Exalted Ruler, or Secretary term for the current lodge year. "
             "Used to filter the Assigned Trustee dropdown.",
    )

    x_trustee_id = fields.Many2one(
        "res.partner", string="Assigned Trustee",
        tracking=True,
        index=True,
        domain="[('id', 'in', x_eligible_trustee_ids)]",
        help="Primary trustee responsible for this ticket. "
             "Only current trustees, the Exalted Ruler, and the Secretary "
             "are shown.",
    )
    x_helper_ids = fields.Many2many(
        "res.partner", "maintenance_request_helper_rel",
        "request_id", "partner_id",
        string="Helpers",
        help="Additional volunteers who helped with this ticket.",
    )

    @api.model
    def _current_lodge_year(self):
        """Return the current lodge year string, e.g. '2025-2026'.

        Lodge year runs April 1 – March 31 (Elks tradition).
        """
        import datetime
        today = fields.Date.context_today(self) or datetime.date.today()
        if today.month >= 4:
            return f"{today.year}-{today.year + 1}"
        return f"{today.year - 1}-{today.year}"

    @api.depends_context("uid")
    def _compute_eligible_trustee_ids(self):
        """Compute the eligible-trustee dropdown set.

        If elkscontacts is installed, restrict to current-year officer-term
        holders for the Trustee / Exalted Ruler / Secretary positions.
        If it's not installed, fall through and allow any partner — the
        feature degrades gracefully rather than crashing the form.
        """
        if "elks.officer.term" in self.env:
            Term = self.env["elks.officer.term"].sudo()
            terms = Term.search([
                ("position", "in", list(self._ELIGIBLE_TRUSTEE_POSITIONS)),
                ("lodge_year", "=", self._current_lodge_year()),
                ("active", "=", True),
            ])
            partner_ids = terms.mapped("partner_id").ids
        else:
            # elkscontacts not installed — no filtering, all partners eligible.
            partner_ids = self.env["res.partner"].sudo().search([]).ids
        for rec in self:
            rec.x_eligible_trustee_ids = [(6, 0, partner_ids)]

    # ------------------------------------------------------------------
    # Dashboard support — lodge year + open/closed status (stored so
    # the pivot view can group/filter quickly without recomputing).
    # ------------------------------------------------------------------
    x_lodge_year = fields.Char(
        string="Lodge Year",
        compute="_compute_x_lodge_year",
        store=True, index=True,
        help="Lodge year the ticket falls under, computed from "
             "request_date (April 1 – March 31).",
    )
    x_is_closed = fields.Boolean(
        string="Closed",
        compute="_compute_x_is_closed",
        store=True, index=True,
        help="True when the ticket's stage is marked Done.",
    )
    x_is_open = fields.Boolean(
        string="Open",
        compute="_compute_x_is_closed",
        store=True,
    )

    @api.depends("request_date")
    def _compute_x_lodge_year(self):
        for rec in self:
            d = rec.request_date
            if not d:
                rec.x_lodge_year = False
                continue
            if d.month >= 4:
                rec.x_lodge_year = f"{d.year}-{d.year + 1}"
            else:
                rec.x_lodge_year = f"{d.year - 1}-{d.year}"

    @api.depends("stage_id", "stage_id.done")
    def _compute_x_is_closed(self):
        for rec in self:
            rec.x_is_closed = bool(rec.stage_id and rec.stage_id.done)
            rec.x_is_open = not rec.x_is_closed

    # ------------------------------------------------------------------
    # Non-stored "current lodge year" flag — used to default-filter the
    # Trustee Dashboard.  Stored=False so we don't have to recompute
    # April 1 every year; searched via _search_is_current_lodge_year.
    # ------------------------------------------------------------------
    x_is_current_lodge_year = fields.Boolean(
        string="Current Lodge Year",
        compute="_compute_x_is_current_lodge_year",
        search="_search_x_is_current_lodge_year",
        help="True when the ticket falls in the current lodge year. "
             "Non-stored — evaluated at query time.",
    )

    def _compute_x_is_current_lodge_year(self):
        current = self._current_lodge_year()
        for rec in self:
            rec.x_is_current_lodge_year = (rec.x_lodge_year == current)

    def _search_x_is_current_lodge_year(self, operator, value):
        truthy = (operator == "=" and value) or (operator == "!=" and not value)
        target = self._current_lodge_year()
        return [("x_lodge_year", "=" if truthy else "!=", target)]

    # ------------------------------------------------------------------
    # Hour tracking
    # ------------------------------------------------------------------
    x_hour_line_ids = fields.One2many(
        "elks.maintenance.hour", "request_id",
        string="Hours Logged",
    )
    x_total_hours = fields.Float(
        "Total Hours", compute="_compute_total_hours",
        store=True,
    )

    @api.depends("x_hour_line_ids.hours")
    def _compute_total_hours(self):
        for rec in self:
            rec.x_total_hours = sum(rec.x_hour_line_ids.mapped("hours"))

    # ------------------------------------------------------------------
    # NOTE: ``x_elks_account_id`` (GL Account) used to live here, but the
    # comodel ``elks.account`` is defined in elksfrs, which would force
    # a hard dependency.  The field now lives in elkspurchase (which
    # depends on both elksmaintenance and elksfrs) so this module stays
    # installable on a vanilla Odoo instance.  Existing DB columns are
    # not dropped — elkspurchase re-attaches to them on install.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Auto-name on create — keeps website Form Builder happy.
    # The base maintenance.request.name is NOT NULL.  If a public form
    # doesn't include a Title field, the insert fails.  We derive a
    # sensible name from the description (or fall back to a generic
    # label) so the form builder can drop any combination of fields
    # and still produce a valid ticket.
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name"):
                continue
            description = (vals.get("description") or "").strip()
            # Strip HTML tags from the (Html) description
            plain = re.sub(r"<[^>]+>", " ", description)
            plain = re.sub(r"\s+", " ", plain).strip()
            if plain:
                vals["name"] = (plain[:57] + "...") if len(plain) > 60 else plain
            elif vals.get("x_submitter_name"):
                vals["name"] = _(
                    "Maintenance Request from %(name)s",
                    name=vals["x_submitter_name"],
                )
            else:
                vals["name"] = _("Maintenance Request")
        return super().create(vals_list)

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

    # ------------------------------------------------------------------
    # Close ticket action — opens wizard
    # ------------------------------------------------------------------
    def action_close_ticket(self):
        """Open the close ticket wizard to confirm hours and close."""
        self.ensure_one()
        done_stage = self.env["maintenance.stage"].search(
            [("done", "=", True)], limit=1, order="sequence"
        )
        if not done_stage:
            raise UserError(_(
                "No 'Done' stage is configured. "
                "Please add a stage with Done = True."
            ))
        return {
            "type": "ir.actions.act_window",
            "name": _("Close Ticket"),
            "res_model": "elks.close.ticket.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_id": self.id,
                "default_hours": self.x_total_hours,
                "default_done_stage_id": done_stage.id,
            },
        }

    # ------------------------------------------------------------------
    # Charity integration — create volunteer hours on close
    # ------------------------------------------------------------------
    def _create_charity_hours(self):
        """Create charity volunteer hour entries under category 9999
        for all hour lines on this ticket.

        Called by the close wizard after confirming hours.

        Gracefully no-ops when the optional ``elkscharity`` and/or
        ``hr`` / ``account`` modules aren't installed — the maintenance
        ticket closes normally and the charity-hour write is just
        skipped.  This is what lets elksmaintenance install standalone.
        """
        self.ensure_one()
        if not self.x_hour_line_ids:
            return

        # Optional-module guards.  All four are required for the full
        # charity-hours write; any missing means we silently skip.
        required_models = (
            "project.project", "project.task",
            "account.analytic.line", "hr.employee",
        )
        for model_name in required_models:
            if model_name not in self.env:
                _logger.info(
                    "Skipping charity hour creation for ticket %s — "
                    "model %s not installed.", self.name, model_name,
                )
                return
        if "x_is_charity_parent" not in self.env["project.project"]._fields:
            _logger.info(
                "Skipping charity hour creation for ticket %s — "
                "elkscharity not installed.", self.name,
            )
            return

        # Find the active charity project
        project = self.env["project.project"].search([
            ("x_is_charity_parent", "=", True),
            ("x_is_closed", "=", False),
        ], limit=1)
        if not project:
            _logger.warning(
                "No active charity project found — skipping charity "
                "hour creation for ticket %s", self.name,
            )
            return

        # Find or create the 9999 category task
        cat_9999 = self.env.ref(
            "elkscharity.cat_9999", raise_if_not_found=False,
        )
        if not cat_9999:
            _logger.warning(
                "Charity category 9999 not found — skipping charity "
                "hour creation for ticket %s", self.name,
            )
            return

        task = self.env["project.task"].search([
            ("project_id", "=", project.id),
            ("x_charity_category_id", "=", cat_9999.id),
        ], limit=1)
        if not task:
            task = self.env["project.task"].create({
                "name": cat_9999.name,
                "project_id": project.id,
                "x_charity_category_id": cat_9999.id,
            })

        # Create analytic lines for each hour entry.
        # NOTE: the old ``address_home_id`` field was removed from
        # hr.employee in Odoo 19 — only ``work_contact_id`` is reliable.
        AAL = self.env["account.analytic.line"]
        for hour_line in self.x_hour_line_ids:
            employee = self.env["hr.employee"].search([
                ("work_contact_id", "=", hour_line.worker_id.id),
            ], limit=1)
            if not employee:
                _logger.info(
                    "No employee record for partner %s — skipping "
                    "charity line for ticket %s",
                    hour_line.worker_id.name, self.name,
                )
                continue

            AAL.sudo().create({
                "name": _(
                    "Maintenance: %(ticket)s",
                    ticket=self.name or "Ticket",
                ),
                "project_id": project.id,
                "task_id": task.id,
                "employee_id": employee.id,
                "date": hour_line.date,
                "unit_amount": hour_line.hours,
            })

        self.message_post(
            body=_(
                "<b>Charity Hours Created</b><br/>"
                "%(count)s volunteer hour entries added to category "
                "9999 (Categories Not Covered).",
                count=len(self.x_hour_line_ids),
            ),
            subtype_xmlid="mail.mt_comment",
        )

    # ------------------------------------------------------------------
    # Website Form Builder integration
    # ------------------------------------------------------------------
    # The form-builder wiring is entirely data-driven in Odoo 19:
    #   data/website_form_data.xml flips
    #     ir.model.website_form_access = True   (model appears in Action
    #                                            dropdown)
    #     ir.model.fields.website_form_blacklisted = False  per field
    #     (handled by the ``formbuilder_whitelist`` function call)
    #
    # No Python override is needed.  Odoo's stock
    # ``ir.model._get_form_writable_fields()`` reads the blacklist flags
    # and returns the right set automatically.
