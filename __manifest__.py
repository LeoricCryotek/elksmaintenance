# -*- coding: utf-8 -*-
{
    "name": "Elks Lodge Maintenance & Deferred Capital Planning",
    "version": "19.0.1.0",
    "category": "Operations/Maintenance",
    "summary": "Asset hierarchy, deferred maintenance backlog, capital planning, "
               "and Trustee dashboard for Elks Lodges.",
    "description": """
Elks Lodge Maintenance System
==============================

Extends Odoo's Maintenance app with features specifically designed for
Elks Lodge Trustees to manage building maintenance, deferred work, and
capital planning.

Features
--------
* Asset hierarchy (Building → System → Component) with square footage
* Deferred Maintenance request type with priority score (1-15)
* Risk type (Safety / Revenue / Cosmetic) and Funding Source tracking
* Target Year for capital planning
* Custom stages: Identified → Evaluating → Deferred → Approved → In Progress → Completed
* Automatic budget sync: Approved items create draft analytic entries in elksfrs
* Trustee dashboard with backlog totals, 5-year capital plan pivot,
  cost per square foot, and priority heatmap
* Automations: auto-tag deferred items, email alerts for high-priority
""",
    "author": "Danny Santiago",
    "website": "https://dannysantiago.info",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "maintenance",
        "elksfrs",
    ],
    "data": [
        "security/elksmaintenance_groups.xml",
        "security/ir.model.access.csv",
        "data/maintenance_stage_data.xml",
        "data/maintenance_tag_data.xml",
        "data/maintenance_automation_data.xml",
        "views/maintenance_equipment_views.xml",
        "views/maintenance_request_views.xml",
        "views/maintenance_dashboard_views.xml",
        "report/deferred_backlog_report.xml",
        "report/capital_plan_report.xml",
        "report/priority_heatmap_report.xml",
        "report/cost_per_sqft_report.xml",
        "report/open_vs_completed_report.xml",
        "views/elksmaintenance_menus.xml",
    ],
    "installable": True,
    "application": True,
}
