# -*- coding: utf-8 -*-
"""Public website controller for maintenance ticket submission."""

import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MaintenanceWebsite(http.Controller):
    """Public-facing maintenance ticket submission form."""

    # ------------------------------------------------------------------
    # JSON endpoint used by the website Form snippet to populate the
    # Location dropdown at page-load time.  This makes the dropdown
    # always reflect the current Lodge Locations list — adding/removing
    # locations via the config page is visible on the form immediately,
    # no editor save required.
    # ------------------------------------------------------------------
    @http.route(
        "/maintenance/locations.json",
        type="http",
        auth="public",
        website=False,
        methods=["GET"],
        csrf=False,
    )
    def maintenance_locations_json(self, **kw):
        return self._render_dynamic_options_json("maintenance.location")

    @http.route(
        "/maintenance/issue-types.json",
        type="http",
        auth="public",
        website=False,
        methods=["GET"],
        csrf=False,
    )
    def maintenance_issue_types_json(self, **kw):
        return self._render_dynamic_options_json("maintenance.issue.type")

    def _render_dynamic_options_json(self, model_name):
        """Shared helper for the public dropdown-data endpoints."""
        import json
        records = (
            request.env[model_name]
            .sudo()
            .search([("active", "=", True)], order="sequence, name")
        )
        payload = [{"id": rec.id, "name": rec.name} for rec in records]
        return request.make_response(
            json.dumps(payload),
            headers=[
                ("Content-Type", "application/json"),
                # Light caching — config records rarely change minute-to-
                # minute but should refresh within a few seconds of any edit.
                ("Cache-Control", "public, max-age=30"),
            ],
        )

    # ------------------------------------------------------------------
    # Thank-you redirect target for the website Form builder.
    # When using Odoo's drag-drop Form widget, set the form's
    # On Success → URL to /maintenance/thanks (no query string needed —
    # the route is publicly accessible and self-renders).
    # ------------------------------------------------------------------
    @http.route(
        "/maintenance/thanks",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def maintenance_thanks(self, **kw):
        """Generic thank-you page for any maintenance ticket submission,
        including those routed through Odoo's website Form builder."""
        return request.render(
            "elksmaintenance.website_ticket_thanks",
            {"ticket": None},
        )

    @http.route(
        "/maintenance",
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def maintenance_form(self, **kw):
        """Render the public ticket submission form."""
        locations = (
            request.env["maintenance.location"]
            .sudo()
            .search([("active", "=", True)], order="sequence, name")
        )
        return request.render(
            "elksmaintenance.website_ticket_form",
            {"locations": locations},
        )

    @http.route(
        "/maintenance/submit",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def maintenance_submit(self, **post):
        """Process the submitted maintenance ticket."""
        vals = {
            "name": post.get("name", "").strip() or "Maintenance Request",
            "description": post.get("description", "").strip(),
            "x_submitter_name": post.get("submitter_name", "").strip(),
            "x_submitter_email": post.get("submitter_email", "").strip(),
            "x_submitter_phone": post.get("submitter_phone", "").strip(),
            # Legacy /maintenance/submit form: accept either a numeric
            # issue-type id or a legacy code like 'repair'.
            **(
                {"x_ticket_type": int(post["ticket_type"])}
                if (post.get("ticket_type") or "").isdigit()
                else (
                    {"x_ticket_type":
                        request.env.ref(
                            "elksmaintenance.maintenance_issue_type_"
                            + (post.get("ticket_type") or "repair"),
                            raise_if_not_found=False,
                        ).id
                     if request.env.ref(
                            "elksmaintenance.maintenance_issue_type_"
                            + (post.get("ticket_type") or "repair"),
                            raise_if_not_found=False,
                        ) else False}
                )
            ),
            "x_location_detail": post.get("location_detail", "").strip(),
        }

        # Location dropdown
        location_id = post.get("location_id")
        if location_id:
            try:
                vals["x_location_id"] = int(location_id)
            except (ValueError, TypeError):
                pass

        # Collect photo uploads to attach after ticket creation.
        # As of v19.0.4.0 photos are stored as ir.attachment records on
        # the ticket (chatter), so any number can be uploaded — we still
        # accept the legacy photo_1..photo_5 form field names, plus a
        # repeating "photos" field for the new HTML form.
        uploaded_files = []
        for i in range(1, 11):
            f = post.get(f"photo_{i}")
            if f:
                uploaded_files.append(f)
        # Support multi-file <input name="photos" multiple>
        for f in request.httprequest.files.getlist("photos"):
            if f:
                uploaded_files.append(f)

        # Assign to first active maintenance team if available
        team = (
            request.env["maintenance.team"]
            .sudo()
            .search([], limit=1)
        )
        if team:
            vals["maintenance_team_id"] = team.id

        ticket = (
            request.env["maintenance.request"]
            .sudo()
            .create(vals)
        )

        # Attach uploaded photos to the ticket
        Attachment = request.env["ir.attachment"].sudo()
        for f in uploaded_files:
            try:
                data = f.read()
                if not data:
                    continue
                Attachment.create({
                    "name": getattr(f, "filename", "photo.png") or "photo.png",
                    "res_model": "maintenance.request",
                    "res_id": ticket.id,
                    "type": "binary",
                    "datas": base64.b64encode(data),
                    "mimetype": getattr(f, "mimetype", None) or "image/png",
                })
            except Exception:
                _logger.warning(
                    "Could not attach uploaded photo %s to ticket %s",
                    getattr(f, "filename", "?"), ticket.id,
                )

        _logger.info(
            "Public maintenance ticket created: #%s '%s' by %s",
            ticket.id, ticket.name, vals.get("x_submitter_name", "anonymous"),
        )

        return request.render(
            "elksmaintenance.website_ticket_thanks",
            {"ticket": ticket},
        )
