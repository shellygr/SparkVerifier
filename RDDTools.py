from z3 import Int

import Globals
from tools import debug


def GenCoreVarsSet(aSet, ctx=None):
    return set([elm[0:elm.index('_')] for elm in aSet])

def GenCoreVars(rdd, ctx=None):
    return GenCoreVarsSet(rdd.fv)

def fvOf(rdd):
    return rdd.fv

def namesToVars(dict, names):
    # print names
    if type(names) == tuple:
        return tuple(map(lambda x: dict[x], names))
    return dict[names]

def gen_name(op):
    Globals.index += 1
    name = "%s%d" % (op, Globals.index)
    # debug("%s", name)
    return name