
from z3 import Solver, Int, simplify, Implies, sat, unsat, Not, And, If, Or

class Agg1Checker():
    def __init__(self):
        self.foldNestingLevel = 0

    def inputCb(self, rdd):
        debug("Agg1Checker: foldNestingLevel in input is %d", self.foldNestingLevel)
        return self.foldNestingLevel == 1

    def mapCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD'])

    def filterCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD'])

    def cartesianCb(self, rdd):
        annotations = rdd.getAnnotations()
        if self.foldNestingLevel != 1:
            return False

        currentFoldNestingLevel = self.foldNestingLevel # Keep for checking the level of the other element in the cartesian product
        if not self.walk(annotations['RDD']):
            return False

        self.foldNestingLevel = currentFoldNestingLevel # Reset back to old nesting level before cartesian, and check the other element
        return self.walk(annotations['Paired'])

    def foldCb(self, rdd):
        annotations = rdd.getAnnotations()
        self.foldNestingLevel = self.foldNestingLevel + 1
        return self.walk(annotations['RDD'])

    def foldByKeyCb(self, rdd):
        annotations = rdd.getAnnotations()
        self.foldNestingLevel = self.foldNestingLevel + 2 # FoldByKey will fail the Agg1Checker
        return self.walk(annotations['RDD'])

    def applyCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD'])

def isAgg1(rdd):
    walker = Agg1Checker()
    return walker.walk(rdd)

class Agg1EquivalenceChecker:
    def check(self, rdd1, rdd2):
        if (not isAgg1(rdd1) and not isAgg1(rdd2)):
            print "Not Agg1 instance: rdd1=%s, rdd2=%s" % (isAgg1(rdd1), isAgg1(rdd2))
            return "Not Agg1 instance"

        if RddWalker.isApply(rdd1):
            g1 = rdd1.getAppliedFunction() # TODO: Multiple composed functions?
            rdd1 = rdd1.getAnnotations()['RDD']
        else:
            g1 = idFunc

        if RddWalker.isApply(rdd2):
            g2 = rdd2.getAppliedFunction()
            rdd2 = rdd2.getAnnotations()['RDD']
        else:
            g2 = idFunc

        foldTerm1 = rdd1.getFoldTerm()
        foldTerm2 = rdd2.getFoldTerm()

        debug("FVs: %s, %s, %s, %s", rdd1.fv, foldTerm1.fv, rdd2.fv, foldTerm2.fv)
        if foldTerm1.fv != foldTerm2.fv:
            return "Not equivalent"

        # Create solver
        solver = Solver()

        # Create z3 constants for all free variables. Assuming all are ints
        coreVars = GenCoreVars(foldTerm1, solver.ctx)
        self.vars = {}
        for coreVar in coreVars:
            self.vars[coreVar] = tuple([BoxedZ3IntVar(name) for name in foldTerm1.fv if name.find(coreVar)==0])
            debug("filling vars dict in key %s with %s", coreVar, self.vars[coreVar])

        bot = Bot()
        self.vars['bot'] = bot

        # TODO: In all procedures - input vars are not bottom
        for name in coreVars:
            for i in range(0,len(self.vars[name])):
                solver.add(Not(self.vars[name][i] == bot))

        i1 = rdd1.getAnnotations()['initVal']
        i2 = rdd2.getAnnotations()['initVal']

        # Introduce variables for the intermediate values
        lhsIntermediate = BoxedZ3IntVarNonBot('lhsIntermediate', solver) # TODO: multiple variables if fold function returns a tuple
        rhsIntermediate = BoxedZ3IntVarNonBot('rhsIntermediate', solver)

        self.vars['lhsIntermediate'] = lhsIntermediate
        self.vars['rhsIntermediate'] = rhsIntermediate

        lNextElem, lNextDependentVars = make_term(foldTerm1, solver, self.vars)
        rNextElem, rNextElemDependentVars = make_term(foldTerm2, solver, self.vars)

        foldFunction1 = rdd1.getAnnotations()['UDF']
        foldFunction2 = rdd2.getAnnotations()['UDF']

        lhApp = UDFParser.substituteInFunc(foldFunction1, (lhsIntermediate, lNextElem), solver, self.vars)
        rhApp = UDFParser.substituteInFunc(foldFunction2, (rhsIntermediate, rNextElem), solver, self.vars)

        debug("lhApp=%s",lhApp)
        debug("rhApp=%s",rhApp)

        reallNextElemVar = BoxedZ3IntVar('reallNextElemVar')
        realrNextElemVar = BoxedZ3IntVar('realrNextElemVar')
        self.vars['reallNextElemVar'] = reallNextElemVar
        self.vars['realrNextElemVar'] = realrNextElemVar

        lNextElem = makeTuple(lNextElem)
        if not isinstance(rNextElem, tuple):
            rNextElem = (rNextElem,)

        # Update the apps to be: if lNextElem is bot, then lhApp=lhsIntermediate, otherwise leave as is
        solver.add(If(Or([lSub == bot for lSub in lNextElem]),reallNextElemVar==lhsIntermediate,reallNextElemVar==lhApp))
        solver.add(If(Or([rSub == bot for rSub in rNextElem]),realrNextElemVar==rhsIntermediate,realrNextElemVar==rhApp))

        gInit1App = UDFParser.substituteInFunc(g1, i1, solver, self.vars)
        gInit2App = UDFParser.substituteInFunc(g2, i2, solver, self.vars)

        glInter = UDFParser.substituteInFunc(g1, lhsIntermediate, solver, self.vars)
        grInter = UDFParser.substituteInFunc(g2, rhsIntermediate, solver, self.vars)
        glApp = UDFParser.substituteInFunc(g1, reallNextElemVar, solver, self.vars)
        grApp = UDFParser.substituteInFunc(g2, realrNextElemVar, solver, self.vars)

        # use convertTermToZ3 to get the induction claim
        debug("glInter=%s, grInter=%s, glApp=%s, grApp=%s", glInter, grInter, glApp, grApp)
        debug("Types: glInter=%s, grInter=%s, glApp=%s, grApp=%s", type(glInter), type(grInter), type(glApp), type(grApp))
        debug("g1(lhsIntermediate)==g2(rhsIntermediate) = %s", glInter == grInter)
        debug("g1(glApp)==g2(grApp) = %s", glApp == grApp)

        # Equality of init and induction implication should be valid. So their negation should be unsatisfiable
        formula = Not(And(gInit1App==gInit2App,
                          Implies((glInter == grInter),
                              glApp==grApp)))
        debug("Induction step formula: %s", formula)
        solver.add(formula)

        return solverResult(solver)