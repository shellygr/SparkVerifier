from z3 import Int

import Globals
from RDDTools import gen_name
from SolverTools import gen_sub_var
from RDD import RDD
from tools import debug


class SparkContext(object):
    def __init__(self, appName):
        self.appName = appName

    def parallelize(self, param):
        paramType = None
        if isinstance(param, list):
            p1 = param[0]
            if isinstance(p1, int):
                # Regular Int rdd
                arity = 1
                paramType = int
            else:
                if isinstance(p1, tuple):
                    arity = len(p1)
                    if isinstance(p1[0], int):
                        paramType = int
        else:
            print "Error! Assuming arity = 1"
            arity = 1

        debug("Input RDD arity = %d, type = %s", arity, paramType)

        # gen name
        name = gen_name("x")

        # gen RDD
        rdd = RDD(name, paramType, arity)

        # gen sub names according to arity: x1-1,...x1-n
        names = [gen_sub_var(name, i) for i in range(1,arity+1)]

        # add self as free variable
        rdd.fv = rdd.fv.union(set(names))

        rdd.vars = tuple([Int(name) for name in rdd.fv])

        # add to inputs
        Globals.input_rdds[name] = rdd

        return rdd