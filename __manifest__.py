# -*- coding: utf-8 -*-
{
    "name": "Elks Lodge Maintenance Tickets",
    "version": "19.0.2.2",
    "category": "Operations/Maintenance",
    "summary": "Helpdesk-style maintenance ticket system with photo uploads, "
               "public submission form, and Trustee meeting reports.",
    "description": """
Elks Lodge Maintenance Tickets
================================

A helpdesk-style maintenance ticketing system for Elks Lodge Trustees.

Features
--------
* Submit maintenance tickets with title, description, location, and photos
* Public website form for members to submit tickets without Odoo login
* Kanban board for Trustees to triage, assign, and resolve tickets
* Photo gallery on each ticket for before/after documentation
* Meeting-ready PDF report: open count, closed count, ticket detail list
* Elks-branded report header with lodge logos
""",
    "author": "Danny Santiago",
    "website": "https://dannysantiago.info",
    "license": "LGPL-3",
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
        "views/maintenance_request_views.xml",
        "views/elksmaintenance_menus.xml",
        "views/website_ticket_templates.xml",
        "report/maintenance_meeting_report.xml",
    ],
    "installable": True,
    "application": True,
    "pre_init_hook": "_pre_init_cleanup",
}
