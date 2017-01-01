import ast
import inspect
from z3 import Solver

import Globals
from UDFParser import getSource, createProgramEnv
from tools import debug


def verifySignature(r1, r2):
    # Get all inputs from r1, r2
    r1AppName = r1.getAppName()
    r2AppName = r2.getAppName()

    r1Inputs = Globals.inputs[r1AppName]
    r2Inputs = Globals.inputs[r2AppName]

    # Check types of all inputs (we don't need to check actual inputs, it's assumed it's the same input)
    for i1, i2 in zip(r1Inputs, r2Inputs):
        t1 = Globals.repr[i1]['type']
        t2 = Globals.repr[i2]['type']

        if t1 != t2:
            return False

    return True
    # Return type is not checked
    # TODO: an example with fold or without folds where the types differ (int vs. boolean, or int x int vs. int)

class FuncDbBuilder(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        debug("Adding func name %s with above src", node.name)
        Globals.funcs[node.name] = node

def fillAllFuncs(p):
    module = inspect.getmodule(p)
    debug("Module of function %s is %s", p, module)
    src = getSource(module)
    parsedSrc = ast.parse(src)
    FuncDbBuilder().visit(parsedSrc)



def verifyEquivalence(p1, p2, *rdds):
    print("")

    fillAllFuncs(p1)
    fillAllFuncs(p2)

    solver = Solver()
    vars = set()

    result1 = createProgramEnv(p1, "p1", *rdds)
    result2 = createProgramEnv(p2, "p2", *rdds)
    # result1 = p1(*rdds)
    # result2 = p2(*rdds)
    debug("Checking equivalence: %s <--> %s", p1.__name__, p2.__name__)
    # TODO: Return this
    """
    if isinstance(result1, tuple):
        formulate1 = [formulate(sub) for sub in result1]
    else:
        formulate1 = formulate(result1)

    if isinstance(result2, tuple):
        formulate2 = [formulate(sub) for sub in result2]
    else:
        formulate2 = formulate(result2)

    print("Checking equivalence: %s <--> %s" % (formulate1, formulate2))
    """

    debug("result1: %s, result2: %s", result1,result2)
    # p1, p2 are functions receiving one or more RDDs (fetched/parallelized by the functions themselves).

    from SparkZ3.Simulator.AbsSolver import verifyEquivalenceOfSymbolicResults
    areEquivalent = verifyEquivalenceOfSymbolicResults(result1, result2)
    if areEquivalent:
        return "equivalent"
    else:
        return "Not equivalent"

def verifyEquivalenceMult(p1, p2, *rdds):
    print("")

    fillAllFuncs(p1)
    fillAllFuncs(p2)

    result1 = p1(*rdds)
    result2 = p2(*rdds)
    debug("Checking equivalence: %s <--> %s", p1.__name__, p2.__name__)
    # TODO: Return this
    """
    if isinstance(result1, tuple):
        formulate1 = [formulate(sub) for sub in result1]
    else:
        formulate1 = formulate(result1)

    if isinstance(result2, tuple):
        formulate2 = [formulate(sub) for sub in result2]
    else:
        formulate2 = formulate(result2)

    print("Checking equivalence: %s <--> %s" % (formulate1, formulate2))
    """

    debug("result1: %s, result2: %s", result1,result2)
    # p1, p2 are functions receiving one or more RDDs (fetched/parallelized by the functions themselves).

    from SparkZ3.Simulator.AbsSolver import verifyEquivalenceOfSymbolicResultsMult
    areEquivalent = verifyEquivalenceOfSymbolicResultsMult(result1, result2)
    if areEquivalent:
        return "equivalent"
    else:
        return "Not equivalent"

