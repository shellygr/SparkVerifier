from z3 import Or, Not, sat, unsat, And

from WrapperClass import _to_BoxedZ3Int
from tools import debug


def makeTuple(elm):
    if not isinstance(elm, tuple):
        return (elm,)
    return elm

def genAtLeastOneInequal(lhsVars, rhsVars, formula):
    # If several variables should be equal, then need to find a satisfying assignment where at least one is not equal.
    if isinstance(lhsVars, tuple) and len(lhsVars)==1:
        lhsVars = lhsVars[0]

    if isinstance(rhsVars, tuple) and len(rhsVars)==1:
        rhsVars = rhsVars[0]

    if (type(lhsVars)==tuple):
        debug("lhsVars: %s len l %d, rhsVars: %s len r %d", lhsVars, len(lhsVars), rhsVars, len(rhsVars))
        for lhsVar, rhsVar in zip(lhsVars, rhsVars):
            debug("%s, %s, %s, %s", lhsVar, type(lhsVar), rhsVar, type(rhsVar))
            formula = Or(formula,genAtLeastOneInequal(lhsVar, rhsVar, False))
            debug("NoAgg Equivalence formula: %s", str(formula))


        return formula
    else:
        debug("%s, %s", lhsVars, lhsVars.__class__.__name__)
        debug("%s, %s", rhsVars, rhsVars.__class__.__name__)
        lhsVars = _to_BoxedZ3Int(lhsVars)
        return Or(formula, Not(lhsVars == rhsVars))

def gen_sub_var(core, index):
    return "%s_%d" % (core, index)

def normalizeTuple(tup):
    if isinstance(tup, tuple) and len(tup) == 1:
        return tup[0]
    else:
        return tup

def getConjunctionOfEquals(series1, series2, formula):
    if isinstance(series1, tuple) and len(series1)==1:
        series1 = series1[0]

    if isinstance(series2, tuple) and len(series2)==1:
        series2 = series2[0]

    if isinstance(series1, tuple) and isinstance(series2, tuple):
        for eq1,eq2 in zip(series1, series2):
            formula = And(formula, getConjunctionOfEquals(eq1, eq2, True))

        return formula
    else:
        return And(formula, series1==series2)


def getAllBottoms(ser, formula, bot):
    if type(ser) == tuple:
        for elm in ser:
            formula = And(formula, getAllBottoms(elm, True, bot))
        return formula
    else:
        return And(formula, ser == bot)


def solverResult(solver):
    debug("Solver: %s", solver)
    # Solve - if UNSAT, equivalent.
    result = solver.check()
    debug("%s", solver.sexpr())
    debug("Solver result = %s", result)
    if result == sat:
        print '\033[91m'+ "Not equivalent! Model: %s" % (solver.model()) + '\033[0m'
        return False
    else:
        if result == unsat:
            debug("Core: %s", solver.unsat_core())
            print '\033[94m' + "Equivalent!" + '\033[0m'
            return True
        else:
            print "Unknown: %s" % (result)


