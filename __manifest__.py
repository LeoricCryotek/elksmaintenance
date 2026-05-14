# -*- coding: utf-8 -*-
{
    "name": "Elks Lodge Maintenance Tickets",
    "version": "19.0.8.0",
    "category": "Operations/Maintenance",
    "summary": "Helpdesk-style maintenance ticket system with trustee assignment, "
               "hour tracking, charity integration, and public submission form.",
    "description": """
Elks Lodge Maintenance Tickets
================================

A helpdesk-style maintenance ticketing system for Elks Lodge Trustees.

Features
--------
* Submit maintenance tickets with title, description, location, and photos
* Public website form for members to submit tickets without Odoo login
* Trustee assignment with primary owner and volunteer helpers
* Hour logging per volunteer per date on each ticket
* Close ticket wizard with total hours confirmation
* Auto-creates charity volunteer hours (category 9999) on ticket close
* Kanban board with stages: New → Assigned → In Progress → Done
* Photo gallery on each ticket for before/after documentation
* Meeting-ready PDF report: open count, closed count, ticket detail list
* Elks-branded report header with lodge logos
""",
    "author": "Danny Santiago",
    "website": "https://dannysantiago.info",
    "license": "LGPL-3",
    # Hard dependencies — only the Odoo modules we cannot run without.
    # Other Elks modules light up integrations at runtime via defensive
    # `if 'model.name' in self.env:` checks and `env.ref(..., raise_if_not_found=False)`.
    # This keeps elksmaintenance installable on a bare Odoo.sh / Odoo Cloud
    # instance without the rest of the lodge stack.
    "depends": [
        "base",
        "mail",
        "maintenance",
        "website",
    ],
    "data": [
        "security/elksmaintenance_groups.xml",
        "security/ir.model.access.csv",
        "data/maintenance_stage_data.xml",
        "data/maintenance_location_data.xml",
        "data/maintenance_issue_type_data.xml",
        "data/website_form_data.xml",
        "views/maintenance_issue_type_views.xml",
        "views/maintenance_request_views.xml",
        "views/maintenance_dashboard_views.xml",
        "views/elksmaintenance_menus.xml",
        "views/website_ticket_templates.xml",
        "views/maintenance_form_snippet.xml",
        "report/maintenance_meeting_report.xml",
    ],
    "assets": {
        # Frontend (public website) assets — keep this minimal:
        # one tiny interaction that populates the Location dropdown
        # on the public Maintenance Form snippet at page-load time.
        "web.assets_frontend": [
            "elksmaintenance/static/src/js/maintenance_form_location.js",
        ],
    },
    "installable": True,
    "application": True,
    "pre_init_hook": "_pre_init_cleanup",
}
