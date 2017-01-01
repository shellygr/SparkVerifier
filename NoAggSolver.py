from z3 import Solver, sat, unsat, Not, Int, Or
from z3util import get_vars


class NoAggChecker(RddWalker):
    def inputCb(self, rdd):
        return False

    def mapCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD'])

    def filterCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD'])

    def cartesianCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD']) or self.walk(annotations['Paired'])

    def foldCb(self, rdd):
        annotations = rdd.getAnnotations()
        return True

    def foldByKeyCb(self, rdd):
        return True

    def applyCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD'])

def isNoAgg(rdd):
    # Checks if has "fold\foldByKey" in annotations somewhere
    walker = NoAggChecker()
    return not walker.walk(rdd)


def noAggEquivalenceTest(rdd1, rdd2):
    # Check belongs to class:
    if (not isNoAgg(rdd1) or not isNoAgg(rdd2)):
        print "Not noAgg instance"
        return "Not applicable"

    # Compare FVs
    if rdd1.fv != rdd2.fv:
        return "Not equivalent"

    # Create solver
    solver = Solver()

    # Create z3 constants for all free variables. Assuming all are ints
    coreVars = GenCoreVars(rdd1, solver.ctx)
    vars = {}
    for coreVar in coreVars:
        vars[coreVar] = tuple([Int(name) for name in rdd1.fv if name.find(coreVar) == 0])
        debug("filling vars dict in key %s with %s", coreVar, vars[coreVar])

    bot = Bot()
    vars['bot'] = bot

    # Create LHS
    lhsVars, lhsDependentVars = make_term(rdd1, solver, vars)

    # Create RHS
    rhsVars, rhsDependentVars = make_term(rdd2, solver, vars)

    debug("LHS %s -> %s", formulate(rdd1), lhsVars)
    debug("RHS %s -> %s", formulate(rdd2), rhsVars)

    # Create the formula that should be UNSAT
    # Should be created recursively: for every tuple, add pairwise equality.
    debug("Type of lhsVars = %s, rhsVars = %s", type(lhsVars), type(rhsVars))
    formula = genAtLeastOneInequal(lhsVars, rhsVars, False)

    debug("Dependent variables: %s", Globals.dependentVariables)
    debug("Equivalence formula: %s", str(formula))

    # Add the formula
    solver.add(formula)

    return solverResult(solver)
