# -*- coding: utf-8 -*-
"""Public website controller for maintenance ticket submission."""

import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MaintenanceWebsite(http.Controller):
    """Public-facing maintenance ticket submission form."""

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
            "x_ticket_type": post.get("ticket_type", "repair"),
            "x_location_detail": post.get("location_detail", "").strip(),
        }

        # Location dropdown
        location_id = post.get("location_id")
        if location_id:
            try:
                vals["x_location_id"] = int(location_id)
            except (ValueError, TypeError):
                pass

        # Process up to 5 photo uploads
        for i in range(1, 6):
            photo_field = f"photo_{i}"
            photo_file = post.get(photo_field)
            if photo_file:
                try:
                    data = photo_file.read()
                    if data:
                        vals[f"x_photo_{i}"] = base64.b64encode(data)
                except Exception:
                    _logger.warning(
                        "Could not process uploaded photo %s", photo_field
                    )

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

        _logger.info(
            "Public maintenance ticket created: #%s '%s' by %s",
            ticket.id, ticket.name, vals.get("x_submitter_name", "anonymous"),
        )

        return request.render(
            "elksmaintenance.website_ticket_thanks",
            {"ticket": ticket},
        )
