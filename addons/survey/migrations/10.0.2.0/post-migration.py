# -*- coding: utf-8 -*-
# Copyright 2017 Eficent <http://www.eficent.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate(use_env=False)
def migrate(cr, version):
    openupgrade.load_data(
        cr, 'survey', 'migrations/10.0.2.0/noupdate_changes.xml',
    )
