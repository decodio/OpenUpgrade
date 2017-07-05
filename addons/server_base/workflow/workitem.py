import logging
import openerp.workflow.instance

from openerp.workflow.helpers import Session
from openerp.workflow.helpers import Record
#from openerp.workflow.helpers import WorkflowActivity

logger = logging.getLogger(__name__)

#import openerp
#from openerp.tools.safe_eval import safe_eval as eval
#from openerp.workflow.workitem import WorkflowItem
import openerp.workflow.workitem
from  openerp.workflow.workitem import WorkflowItem

class WorkflowItemOverride(object):

    @classmethod
    def create_override(cls, session, record, activity, instance_id, stack):
        assert isinstance(session, Session)
        assert isinstance(record, Record)
        assert isinstance(activity, dict)
        assert isinstance(instance_id, (long, int))
        assert isinstance(stack, list)

        cr = session.cr
         # DECOD.IO- db_uid cr.execute("select nextval('wkf_workitem_id_seq')")
        cr.execute("select nextval('ir_serial_id_seq')")  # DECOD.IO+ db_uid
        id_new = cr.fetchone()[0]
        cr.execute("insert into wkf_workitem (id,act_id,inst_id,state) values (%s,%s,%s,'active')", (id_new, activity['id'], instance_id))
        cr.execute('select * from wkf_workitem where id=%s',(id_new,))
        work_item_values = cr.dictfetchone()
        logger.info('Created workflow item in activity %s',
                    activity['id'],
                    extra={'ident': (session.uid, record.model, record.id)})

        workflow_item = WorkflowItem(session, record, work_item_values)
        workflow_item.process(stack=stack)

    def process(self, signal=None, force_running=False, stack=None):
        assert isinstance(force_running, bool)
        assert stack is not None

        cr = self.session.cr

        cr.execute('select * from wkf_activity where id=%s', (self.workitem['act_id'],))
        activity = cr.dictfetchone()

        triggers = False
        if self.workitem['state'] == 'active':
            triggers = True
            if not self._execute(activity, stack):
                return False

        if force_running or self.workitem['state'] == 'complete':
            ok = self._split_test(activity['split_mode'], signal, stack)
            triggers = triggers and not ok

        if triggers:
            cr.execute('select * from wkf_transition where act_from=%s', (self.workitem['act_id'],))
            for trans in cr.dictfetchall():
                if trans['trigger_model']:
                    ids = self.wkf_expr_eval_expr(trans['trigger_expr_id'])
                    for res_id in ids:
                        # DECOD.IO- cr.execute('select nextval(\'wkf_triggers_id_seq\')')
                        cr.execute("select nextval('ir_serial_id_seq')")  # DECOD.IO+ db_uid
                        id =cr.fetchone()[0]
                        cr.execute('insert into wkf_triggers (model,res_id,instance_id,workitem_id,id) values (%s,%s,%s,%s,%s)', (trans['trigger_model'],res_id, self.workitem['inst_id'], self.workitem['id'], id))

        return True
