# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import openerp.modules
from openerp.modules import db, graph, loading, migration, module, registry

from openerp.modules.loading import load_modules

from openerp.modules.module import get_modules, get_modules_with_version, \
    load_information_from_description_file, get_module_resource, get_module_path, \
    initialize_sys_path, load_openerp_module, init_module_models, adapt_version

import logging
_logger = logging.getLogger(__name__)


def initialize_override(cr):
    """ Initialize a database with for the ORM.

    This executes base/base.sql, creates the ir_module_categories (taken
    from each module descriptor file), and creates the ir_module_module
    and ir_model_data entries.

    """
    f = openerp.modules.get_module_resource('server_base', 'base.sql')  # DECOD.IO db_uid
    if not f:
        m = "File not found: 'base.sql' (provided by module 'server_base')."  # DECOD.IO db_uid
        _logger.critical(m)
        raise IOError(m)
    base_sql_file = openerp.tools.misc.file_open(f)
    try:
        cr.execute(base_sql_file.read())
        cr.commit()
    finally:
        base_sql_file.close()

    for i in openerp.modules.get_modules():
        mod_path = openerp.modules.get_module_path(i)
        if not mod_path:
            continue

        # This will raise an exception if no/unreadable descriptor file.
        info = openerp.modules.load_information_from_description_file(i)

        if not info:
            continue
        categories = info['category'].split('/')
        # DECOD.IO category_id = create_categories(cr, categories)  # DECOD.IO db_uid
        category_id = openerp.modules.db.create_categories(cr, categories)  # DECOD.IO db_uid

        if info['installable']:
            state = 'uninstalled'
        else:
            state = 'uninstallable'

        cr.execute('INSERT INTO ir_module_module \
                (author, website, name, shortdesc, description, \
                    category_id, auto_install, state, web, license, application, icon, sequence, summary) \
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id', (
            info['author'],
            info['website'], i, info['name'],
            info['description'], category_id,
            info['auto_install'], state,
            info['web'],
            info['license'],
            info['application'], info['icon'],
            info['sequence'], info['summary']))
        id = cr.fetchone()[0]
        cr.execute('INSERT INTO ir_model_data \
            (name,model,module, res_id, noupdate) VALUES (%s,%s,%s,%s,%s)', (
                'module_'+i, 'ir.module.module', 'base', id, True))
        dependencies = info['depends']
        for d in dependencies:
            cr.execute('INSERT INTO ir_module_module_dependency \
                    (module_id,name) VALUES (%s, %s)', (id, d))

    # Install recursively all auto-installing modules
    while True:
        cr.execute("""SELECT m.name FROM ir_module_module m WHERE m.auto_install AND state != 'to install'
                      AND NOT EXISTS (
                          SELECT 1 FROM ir_module_module_dependency d JOIN ir_module_module mdep ON (d.name = mdep.name)
                                   WHERE d.module_id = m.id AND mdep.state != 'to install'
                      )""")
        to_auto_install = [x[0] for x in cr.fetchall()]
        if not to_auto_install: break
        cr.execute("""UPDATE ir_module_module SET state='to install' WHERE name in %s""", (tuple(to_auto_install),))

    cr.commit()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
