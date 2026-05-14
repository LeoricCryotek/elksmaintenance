# -*- coding: utf-8 -*-
# Issue types must register before maintenance_request so the model
# exists when x_ticket_type's many2one resolves its comodel.
from . import maintenance_issue_type
from . import maintenance_location
from . import maintenance_request
from . import maintenance_hour
# Summary SQL view comes last — depends on maintenance_request columns.
from . import maintenance_trustee_summary
