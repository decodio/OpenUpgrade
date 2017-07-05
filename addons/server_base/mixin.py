# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Function MixIn copied from:
#    http://www.daniweb.com/software-development/python/threads/183491/subclassing-class-instance
#    ljmixin.py copied from http://www.linuxjournal.com/node/4540/print
#    offers a MixIn function to dynamically mix classes a run time.
##############################################################################
import types


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

# Owerride openerp.modules.db.initialize()
# to use base.sql featuring one sequence for all tables
from .modules.db import initialize_override
import openerp
openerp.modules.db.initialize = initialize_override

from openerp.osv.orm import BaseModel
from .osv.orm import BaseModelExtend, BaseModelOverride
MixIn(BaseModel, BaseModelExtend, makeAncestor=0)
MixIn(BaseModel, BaseModelOverride, makeAncestor=0)

from openerp.workflow.workitem import WorkflowItem
from .workflow.workitem import WorkflowItemOverride
MixIn(WorkflowItem, WorkflowItemOverride, makeAncestor=0)
WorkflowItem.create = WorkflowItemOverride.create_override
