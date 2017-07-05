# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Slobodni Programi d.o.o. (<http://slobodni-programi.com>).
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
from openerp.models import FIELDS_TO_PGTYPES, LOG_ACCESS_COLUMNS  # MetaModel,  Model, TransientModel, AbstractModel
from openerp.osv import fields
from openerp.osv.orm import BaseModel, Model, MAGIC_COLUMNS, except_orm

import types
import openerp.tools as tools

import logging
_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

Model._sequence = 'ir_serial_id_seq'

for sub_class in Model.__subclasses__():
    sub_class._sequence = 'ir_serial_id_seq' #  if sub_class._transient

from openerp.addons.base.ir.ir_actions import *
ir_actions_act_client._sequence = 'ir_serial_id_seq'
ir_actions_report_xml._sequence = 'ir_serial_id_seq'
ir_actions_act_window._sequence = 'ir_serial_id_seq'
ir_actions_act_url._sequence = 'ir_serial_id_seq'
ir_actions_server._sequence = 'ir_serial_id_seq'
ir_server_object_lines._sequence = 'ir_serial_id_seq'

FIELDS_TO_PGTYPES[fields.integer] = 'int8'  # DECOD.IO
FIELDS_TO_PGTYPES[fields.many2one] = 'int8'  # DECOD.IO

#TODO changed in v8
"""
#LOG_ACCESS_COLUMNS['create_uid'] = "BIGINT REFERENCES res_users ON DELETE RESTRICT"
#LOG_ACCESS_COLUMNS['create_date'] = "TIMESTAMP without time zone DEFAULT (now() AT TIME ZONE 'UTC')"
#LOG_ACCESS_COLUMNS['write_uid'] = "BIGINT REFERENCES res_users ON DELETE RESTRICT"
#LOG_ACCESS_COLUMNS['write_date'] = "TIMESTAMP without time zone"
"""


def MixIn(pyClass, mixInClass, makeAncestor=0):
    if makeAncestor:
        if mixInClass not in pyClass.__bases__:
            pyClass.__bases__ = (mixInClass,) + pyClass.__bases__
    else:
        # Recursively traverse the mix-in ancestor classes in order to support inheritance
        baseClasses = list(mixInClass.__bases__)
        baseClasses.reverse()
        for baseClass in baseClasses:
            MixIn(pyClass, baseClass)
        # Install the mix-in methods into the class
        for name in dir(mixInClass):
            if not name.startswith('__'):  # skip private members
                member = getattr(mixInClass, name)
                if type(member) is types.MethodType:
                    member = member.im_func
                setattr(pyClass, name, member)


class BaseModelExtend(object):

    def get_related_fields_values(self, cr, uid, fields_ids, context=None):  # DECOD.IO NEW
        res = {}
        for related_field in fields_ids.keys():
            related_id = fields_ids[related_field]
            field_path = related_field.split('.', 1)
            model_field = field_path[0]
            field_path = field_path[1]
            model2 = self._columns[model_field]._obj  # __contains__(self, name):
            Model2 = self.pool.get(model2)
            value = False
            if related_id:
                value = Model2.browse(cr, uid, related_id, context=context)
                for field in field_path.split('.'):
                    if value[field] is None:
                        value = False
                        break
                    value = value[field]
            res[related_field] = {'value': value or False}
        return res

    def ids2sql_values(self):
        ids_as_table = '),('.join(str(e) for e in self._ids)
        if len(ids_as_table) > 1:
            ids_as_table = '(  ' + ids_as_table + '  )'
        else:
            ids_as_table = '(NULL::bigint)'
        return ids_as_table

    def update_from_dict(self, values):
        for name, value in values.iteritems():  # Update record self[0] with values
            if name in self._columns:  # _fields:
                self[name] = value


    def _sql_sequence_exist(self, seq_name):
       sql = "SELECT exists(SELECT 1 FROM pg_class where relname = %s )"
       self._cr.execute(sql, (seq_name, ))
       return self._cr.fetchall()[0][0]


old_init = BaseModel.__init__
def new_init(self, pool, cr):
    cls = type(self)
    if not cls._sequence:
        #original cls._sequence = cls._table + '_id_seq'
        cls._sequence = 'ir_serial_id_seq'  # KGB don't mess with __init__
    old_init(self, pool, cr)
BaseModel.__init__ = new_init

class BaseModelOverride(object):


    '''
    @classmethod
    def _inherits_reload_src(cls):
        """ Recompute the _inherit_fields mapping on each _inherits'd child model."""
        if not cls._sequence:   # DECOD.IO db_uid
            cls._sequence = 'ir_serial_id_seq'  # KGB don't mess with __init__
        for model in cls.pool.values():
            if cls._name in model._inherits:
                model._inherits_reload()
    '''
    def create_audit_triger(self):
        if self._model._transient:
            return False
        if self._table.startswith(("wkf_", "im_chat_",)):
            return False

        if self._name in ['bus_bus', 'ir_sequence', 'osv_memory_autovacuum',
                         ]:
            return False
        return True

    def _create_table(self, cr):
        if self._model._transient:
            cr.execute("""CREATE TABLE "%s"
                        (id SERIAL NOT NULL, PRIMARY KEY(id))
                        WITHOUT OIDS""" % (self._table,))  # ORIG
        else:
            cr.execute("""CREATE TABLE "%s"
                       (id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
                        PRIMARY KEY(id))  WITHOUT OIDS
                    """ % (self._table,))  # DECOD.IO db_uid

        if self.create_audit_triger() and 1==2: # TODO audit infrastructure
            cr.execute("""CREATE TRIGGER "%s"
                       AFTER INSERT OR UPDATE OR DELETE ON "%s"
                         FOR EACH ROW EXECUTE PROCEDURE oe_audit()
                    """ % (self._table+'_audit', self._table))  # DECOD.IO db_uid if self._log_access:
        cr.execute(("COMMENT ON TABLE \"%s\" IS %%s" % self._table), (self._description,))
        _schema.debug("Table '%s': created", self._table)

    def _m2m_raise_or_create_relation(self, cr, f):
        """ Create the table for the relation if necessary.
        Return ``True`` if the relation had to be created.
        """
        m2m_tbl, col1, col2 = f._sql_names(self)
        # do not create relations for custom fields as they do not belong to a module
        # they will be automatically removed when dropping the corresponding ir.model.field
        if not f.string.startswith('x_'):
            self._save_relation_table(cr, m2m_tbl)
        cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (m2m_tbl,))
        if not cr.dictfetchall():
            if f._obj not in self.pool:
                raise except_orm('Programming Error', 'Many2Many destination model does not exist: `%s`' % (f._obj,))
            dest_model = self.pool[f._obj]
            ref = dest_model._table
            # ORIG: cr.execute('CREATE TABLE "%s" ("%s" INTEGER NOT NULL, "%s" INTEGER NOT NULL, UNIQUE("%s","%s"))' % (m2m_tbl, col1, col2, col1, col2))
            cr.execute("""CREATE TABLE "%s" ("%s" BIGINT NOT NULL, "%s" BIGINT NOT NULL, UNIQUE("%s","%s"))
                       """ % (m2m_tbl, col1, col2, col1, col2))  # DECOD.IO db_uid
            #cr.execute("""CREATE TRIGGER "%s"
            #               AFTER INSERT OR UPDATE OR DELETE ON "%s"
            #                 FOR EACH ROW EXECUTE PROCEDURE oe_audit()
            #           """ % (self._table+'_audit', self._table))  # DECOD.IO db_uid

            # create foreign key references with ondelete=cascade, unless the targets are SQL views
            cr.execute("SELECT relkind FROM pg_class WHERE relkind IN ('v') AND relname=%s", (ref,))
            if not cr.fetchall():
                self._m2o_add_foreign_key_unchecked(m2m_tbl, col2, dest_model, 'cascade')
            cr.execute("SELECT relkind FROM pg_class WHERE relkind IN ('v') AND relname=%s", (self._table,))
            if not cr.fetchall():
                self._m2o_add_foreign_key_unchecked(m2m_tbl, col1, self, 'cascade')

            cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (m2m_tbl, col1, m2m_tbl, col1))
            cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (m2m_tbl, col2, m2m_tbl, col2))
            cr.execute("COMMENT ON TABLE \"%s\" IS 'RELATION BETWEEN %s AND %s'" % (m2m_tbl, self._table, ref))
            cr.commit()
            _schema.debug("Create table '%s': m2m relation between '%s' and '%s'", m2m_tbl, self._table, ref)
            return True

    def _create_parent_columns(self, cr):
        cr.execute('ALTER TABLE "%s" ADD COLUMN "parent_left" BIGINT' % (self._table,))   # DECOD.IO db_uid
        cr.execute('ALTER TABLE "%s" ADD COLUMN "parent_right" BIGINT' % (self._table,))  # DECOD.IO db_uid
        if 'parent_left' not in self._columns:
            _logger.error('create a column parent_left on object %s: fields.integer(\'Left Parent\', select=1)',
                          self._table)
            _schema.debug("Table '%s': added column '%s' with definition=%s",
                self._table, 'parent_left', 'INTEGER')
        elif not self._columns['parent_left'].select:
            _logger.error('parent_left column on object %s must be indexed! Add select=1 to the field definition)',
                          self._table)
        if 'parent_right' not in self._columns:
            _logger.error('create a column parent_right on object %s: fields.integer(\'Right Parent\', select=1)',
                          self._table)
            _schema.debug("Table '%s': added column '%s' with definition=%s",
                self._table, 'parent_right', 'INTEGER')
        elif not self._columns['parent_right'].select:
            _logger.error('parent_right column on object %s must be indexed! Add select=1 to the field definition)',
                          self._table)
        if self._columns[self._parent_name].ondelete not in ('cascade', 'restrict'):
            _logger.error("The column %s on object %s must be set as ondelete='cascade' or 'restrict'",
                          self._parent_name, self._name)

        cr.commit()

    def _auto_end(self, cr, context=None):  # Called after _auto_init chance ti fix integer to bigINT
        """ Create the foreign keys recorded by _auto_init. """
        for t, k, r, d in self._foreign_keys:
            cr.execute('ALTER TABLE "%s" ADD FOREIGN KEY ("%s") REFERENCES "%s" ON DELETE %s' % (t, k, r, d))
            self._save_constraint(cr, "%s_%s_fkey" % (t, k), 'f', False)
        cr.commit()
        del self._foreign_keys

    def _field_create(self, cr, context=None):  # # DECOD.IO OVERRIDE db_uid  nextval setval
        """ Create entries in ir_model_fields for all the model's fields.

        If necessary, also create an entry in ir_model, and if called from the
        modules loading scheme (by receiving 'module' in the context), also
        create entries in ir_model_data (for the model and the fields).

        - create an entry in ir_model (if there is not already one),
        - create an entry in ir_model_data (if there is not already one, and if
          'module' is in the context),
        - update ir_model_fields with the fields found in _columns
          (TODO there is some redundancy as _columns is updated from
          ir_model_fields in __init__).

        """
        if context is None:
            context = {}
        cr.execute("SELECT id FROM ir_model WHERE model=%s", (self._name,))
        if not cr.rowcount:
            # ORIG: cr.execute('SELECT nextval(%s)', ('ir_model_id_seq',))
            cr.execute('SELECT nextval(%s)', ('ir_serial_id_seq',))  # DECOD.IO db_uid
            model_id = cr.fetchone()[0]
            cr.execute("INSERT INTO ir_model (id,model, name, info,state) VALUES (%s, %s, %s, %s, %s)", (model_id, self._name, self._description, self.__doc__, 'base'))
        else:
            model_id = cr.fetchone()[0]
        if 'module' in context:
            name_id = 'model_'+self._name.replace('.', '_')
            cr.execute('select * from ir_model_data where name=%s and module=%s', (name_id, context['module']))
            if not cr.rowcount:
                cr.execute("INSERT INTO ir_model_data (name,date_init,date_update,module,model,res_id) VALUES (%s, (now() at time zone 'UTC'), (now() at time zone 'UTC'), %s, %s, %s)", \
                    (name_id, context['module'], 'ir.model', model_id)
                )

        cr.execute("SELECT * FROM ir_model_fields WHERE model=%s", (self._name,))
        cols = {}
        for rec in cr.dictfetchall():
            cols[rec['name']] = rec

        ir_model_fields_obj = self.pool.get('ir.model.fields')

        # sparse field should be created at the end, as it depends on its serialized field already existing
        model_fields = sorted(self._columns.items(), key=lambda x: 1 if x[1]._type == 'sparse' else 0)
        for (k, f) in model_fields:
            vals = {
                'model_id': model_id,
                'model': self._name,
                'name': k,
                'field_description': f.string,
                'ttype': f._type,
                'relation': f._obj or '',
                'select_level': tools.ustr(f.select or 0),
                'readonly': (f.readonly and 1) or 0,
                'required': (f.required and 1) or 0,
                'selectable': (f.selectable and 1) or 0,
                'translate': (f.translate and 1) or 0,
                'relation_field': f._fields_id if isinstance(f, fields.one2many) else '',
                'serialization_field_id': None,
            }
            if getattr(f, 'serialization_field', None):
                # resolve link to serialization_field if specified by name
                serialization_field_id = ir_model_fields_obj.search(cr, SUPERUSER_ID, [('model','=',vals['model']), ('name', '=', f.serialization_field)])
                if not serialization_field_id:
                    raise except_orm(_('Error'), _("Serialization field `%s` not found for sparse field `%s`!") % (f.serialization_field, k))
                vals['serialization_field_id'] = serialization_field_id[0]

            # When its a custom field,it does not contain f.select
            if context.get('field_state', 'base') == 'manual':
                if context.get('field_name', '') == k:
                    vals['select_level'] = context.get('select', '0')
                #setting value to let the problem NOT occur next time
                elif k in cols:
                    vals['select_level'] = cols[k]['select_level']

            if k not in cols:
                # ORIG: cr.execute('select nextval(%s)', ('ir_model_fields_id_seq',))
                cr.execute('select nextval(%s)', ('ir_serial_id_seq',))  # DECOD.IO db_uid
                id = cr.fetchone()[0]
                vals['id'] = id
                cr.execute("""INSERT INTO ir_model_fields (
                    id, model_id, model, name, field_description, ttype,
                    relation,state,select_level,relation_field, translate, serialization_field_id
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )""", (
                    id, vals['model_id'], vals['model'], vals['name'], vals['field_description'], vals['ttype'],
                     vals['relation'], 'base',
                    vals['select_level'], vals['relation_field'], bool(vals['translate']), vals['serialization_field_id']
                ))
                if 'module' in context:
                    name1 = 'field_' + self._table + '_' + k
                    cr.execute("select name from ir_model_data where name=%s", (name1,))
                    if cr.fetchone():
                        name1 = name1 + "_" + str(id)
                    cr.execute("INSERT INTO ir_model_data (name,date_init,date_update,module,model,res_id) VALUES (%s, (now() at time zone 'UTC'), (now() at time zone 'UTC'), %s, %s, %s)", \
                        (name1, context['module'], 'ir.model.fields', id)
                    )
            else:
                for key, val in vals.items():
                    if cols[k][key] != vals[key]:
                        cr.execute('update ir_model_fields set field_description=%s where model=%s and name=%s', (vals['field_description'], vals['model'], vals['name']))
                        cr.execute("""UPDATE ir_model_fields SET
                            model_id=%s, field_description=%s, ttype=%s, relation=%s,
                            select_level=%s, readonly=%s ,required=%s, selectable=%s, relation_field=%s, translate=%s, serialization_field_id=%s
                        WHERE
                            model=%s AND name=%s""", (
                                vals['model_id'], vals['field_description'], vals['ttype'],
                                vals['relation'],
                                vals['select_level'], bool(vals['readonly']), bool(vals['required']), bool(vals['selectable']), vals['relation_field'], bool(vals['translate']), vals['serialization_field_id'], vals['model'], vals['name']
                            ))
                        break
        self.invalidate_cache(cr, SUPERUSER_ID)


    def _select_column_data(self, cr):

        # attlen is the number of bytes necessary to represent the type when
        # the type has a fixed size. If the type has a varying size attlen is
        # -1 and atttypmod is the size limit + 4, or -1 if there is no limit.

        # added schema name to query and rewritten sql to be more readable
        schema = 'public'
        cr.execute(
            """
                SELECT
                     c.relname
                    ,a.attname
                    ,a.attlen
                    ,a.atttypmod
                    ,a.attnotnull
                    ,a.atthasdef
                    ,t.typname
                    ,CASE WHEN a.attlen=-1 THEN (CASE WHEN a.atttypmod=-1 THEN 0
                                                      ELSE a.atttypmod-4 END)
                          ELSE a.attlen END as size
                FROM pg_type t
                JOIN pg_attribute a ON (a.atttypid=t.oid)
                JOIN pg_class c ON (c.oid=a.attrelid)
                JOIN pg_catalog.pg_namespace n ON (n.oid = c.relnamespace)
                WHERE 1 = 1
                AND n.nspname = %s
                AND c.relname = %s
            """, (schema, self._table))
        return dict(map(lambda x: (x['attname'], x), cr.dictfetchall()))
