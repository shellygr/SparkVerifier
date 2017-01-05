from z3 import Solver, Int, simplify, Implies, sat, unsat, Not, And, Exists, ForAll, Or, If, set_param


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
        self.foldNestingLevel = self.foldNestingLevel + 2 # Fold by key will fail the checker
        return self.walk(annotations['RDD'])


    def applyCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD'])

class AggPair1SyncClassDefChecker:
    def check(self, rdd1, rdd2):
        # tools.DEBUG = False
        # First, check both are agg1
        if not isAgg1(rdd1) or not isAgg1(rdd2):
            return False

        # Peel a possible apply function operation on the fold
        if RddWalker.isApply(rdd1):
            rdd1 = rdd1.getAnnotations()['RDD']

        if RddWalker.isApply(rdd2):
            rdd2 = rdd2.getAnnotations()['RDD']

        # Then, check free variables
        foldTerm1 = rdd1.getFoldTerm()
        foldTerm2 = rdd2.getFoldTerm()

        debug("FVs: %s, %s, %s, %s", rdd1.fv, foldTerm1.fv, rdd2.fv, foldTerm2.fv)
        if foldTerm1.fv != foldTerm2.fv:
            return False

        # Now create a solver and check the semantic property

        # Create solver
        solver = Solver()

        # Create z3 constants for all free variables. Assuming all are ints
        coreVars = GenCoreVars(foldTerm1, solver.ctx)
        self.vars = {}
        for coreVar in coreVars:
            debug("For coreVar %s creating %s", coreVar, [name for name in foldTerm1.fv if name.find(coreVar)==0])
            self.vars[coreVar] = tuple([Int(name) for name in foldTerm1.fv if name.find(coreVar)==0])
            debug("filling vars dict in key %s with %s", coreVar, self.vars[coreVar])

        bot = Bot()
        self.vars['bot'] = bot

        i1 = rdd1.getAnnotations()['initVal']
        i2 = rdd2.getAnnotations()['initVal']

        foldFunction1 = rdd1.getAnnotations()['UDF']
        foldFunction2 = rdd2.getAnnotations()['UDF']


        elem1, dep1 = make_term(foldTerm1, solver, self.vars)
        elem2, dep2 = make_term(foldTerm2, solver, self.vars)
        elem1 = makeTuple(elem1)
        elem2 = makeTuple(elem2)
        firstApp1 = UDFParser.substituteInFunc(foldFunction1, (i1, normalizeTuple(elem1)), solver, self.vars)
        firstApp2 = UDFParser.substituteInFunc(foldFunction2, (i2, normalizeTuple(elem2)), solver, self.vars)

        print " DONE WITH FIRST ARG "
        elem1b, dep1b = make_term(foldTerm1, solver, self.vars, True)
        elem2b, dep2b = make_term(foldTerm2, solver, self.vars, False)
        elem1b = makeTuple(elem1b)
        elem2b = makeTuple(elem2b)
        secondApp1 = UDFParser.substituteInFunc(foldFunction1, (firstApp1, normalizeTuple(elem1b)), solver, self.vars)
        secondApp2 = UDFParser.substituteInFunc(foldFunction2, (firstApp2, normalizeTuple(elem2b)), solver, self.vars)

        print " DONE WITH SECOND ARG "
        elem1s, dep1s = make_term(foldTerm1, solver, self.vars, True)
        elem2s, dep2s = make_term(foldTerm2, solver, self.vars, False)
        elem1s = makeTuple(elem1s)
        elem2s = makeTuple(elem2s)
        shrinked1 = UDFParser.substituteInFunc(foldFunction1, (i1, normalizeTuple(elem1s)), solver, self.vars)
        shrinked2 = UDFParser.substituteInFunc(foldFunction2, (i2, normalizeTuple(elem2s)), solver, self.vars)
        print " DONE WITH THE SHRINKED ARG "





        # Need to allocate 3 variables, currently int (TODO: Support not only ints)
        # lFirstArg = normalizeTuple(tuple([BoxedZ3IntVarNonBot('lFirstArg_%d'%i, solver) for i in range(len(elem1))])) # TODO: multiple variables if fold function returns a tuple
        # lSecondArg = normalizeTuple(tuple([BoxedZ3IntVarNonBot('lSecondArg_%d'%i, solver) for i in range(len(elem1b))]))
        #
        # rFirstArg = normalizeTuple(tuple([BoxedZ3IntVarNonBot('rFirstArg_%d'%i, solver) for i in range(len(elem2))]))
        # rSecondArg = normalizeTuple(tuple([BoxedZ3IntVarNonBot('rSecondArg_%d'%i, solver) for i in range(len(elem2b))]))
        # lShrinkArg = normalizeTuple(tuple([BoxedZ3IntVarNonBot('lShrinkArg_%d'%i, solver) for i in range(len(elem1s))]))
        # rShrinkArg = normalizeTuple(tuple([BoxedZ3IntVarNonBot('rShrinkArg_%d'%i, solver) for i in range(len(elem2s))]))

        # self.vars['lFirstArg'] = lFirstArg
        # self.vars['lSecondArg'] = lSecondArg
        # self.vars['rFirstArg'] = rFirstArg
        # self.vars['rSecondArg'] = rSecondArg
        # # self.vars['lShrinkArg'] = lShrinkArg
        # self.vars['rShrinkArg'] = rShrinkArg


        #
        # solver.add(getConjunctionOfEquals(lFirstArg,elem1,True))
        # solver.add(getConjunctionOfEquals(rFirstArg,elem2,True))
        # solver.add(getConjunctionOfEquals(lSecondArg,elem1b,True))
        # solver.add(getConjunctionOfEquals(rSecondArg,elem2b,True))
        # solver.add(getConjunctionOfEquals(lShrinkArg,elem1s,True))
        # solver.add(getConjunctionOfEquals(rShrinkArg,elem2s,True))

        def mapToValIfListOfBoxed(var):
            if isinstance(var, tuple):
                return map(lambda x: x.val, list(var))
            else:
                return var.val

        print Globals.newNames
        print map(lambda x: x.__class__.__name__, Globals.newNames)
        print map(lambda x: x.__class__.__name__, list(dep1s))

        forAllVars = list(dep1s)
        forAllVars.extend(Globals.newNames)
        # print list(dep1s)
        # print list(dep1s).append(Globals.newNames)
        print forAllVars

        # tools.DEBUG = False
        # The following should be unsatisfied for the programs to be AggPair1Sync
        formula = Exists(list(dep1), #mapToValIfListOfBoxed(lFirstArg),
                         Exists(list(dep1b), #mapToValIfListOfBoxed(rFirstArg),
                                # Exists(mapToValIfListOfBoxed(lSecondArg),
                                #        Exists(mapToValIfListOfBoxed(rSecondArg),
                                              ForAll(forAllVars, #mapToValIfListOfBoxed(lShrinkArg),
                                                     # ForAll(mapToValIfListOfBoxed(rShrinkArg),
                                                            Not(And(secondApp1==shrinked1,secondApp2==shrinked2)))))#)# ))
        solver.add(formula)

        debug("Solver: %s", solver)
        print solver
        # Solve - if UNSAT, programs are AggPair1Sync.
        result = solver.check()

        debug("Solver result = %s", result)
        if result == sat:
            print solver.sexpr()
            model = solver.model()
            print "Exists ", dep1, dep1b, ", ForAll ", forAllVars, " "#,
            print model.evaluate(secondApp1.val), model.evaluate(shrinked1.val), model.evaluate(secondApp2.val), model.evaluate(shrinked2.val)
            print("Model showing not AggPair1Sync %s", model)
            print secondApp1, shrinked1, secondApp2, shrinked2
            # print model[secondApp1]
            Globals.newNames = []

            return False
        else:
            if result == unsat:
                print "Programs are AggPair1Sync"
                Globals.newNames = []

                return True
            else:
                print "Unknown, assumes not AggPair1Sync: %s" % (result)
                Globals.newNames = []

                return False

# Assumes input is AggPair1Sync
class AggPair1SyncEquivalenceChecker:
    def check(self, rdd1, rdd2):
        # set_param('smtlib2-compliant',True)
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

        if foldTerm1.fv != foldTerm2.fv:
            return "Not equivalent"

        # Create solver
        solver = Solver()

        # Create z3 constants for all free variables. Assuming all are ints
        coreVars = GenCoreVars(foldTerm1, solver.ctx)
        self.vars = {}
        for coreVar in coreVars:
            self.vars[coreVar] = tuple([BoxedZ3IntVar(name) for name in foldTerm1.fv if name.find(coreVar)==0])

        bot = Bot()
        self.vars['bot'] = bot

        i1 = rdd1.getAnnotations()['initVal']
        i2 = rdd2.getAnnotations()['initVal']

        foldFunction1 = rdd1.getAnnotations()['UDF']
        foldFunction2 = rdd2.getAnnotations()['UDF']

        elem1, dep1 = make_term(foldTerm1, solver, self.vars)
        elem2, dep2 = make_term(foldTerm2, solver, self.vars)

        # reallNextElemVar = tuple([BoxedZ3IntVar('reallNextElemVar_%d'%i for i in range(1,len(i1)+1))])
        # realrNextElemVar = tuple([BoxedZ3IntVar('realrNextElemVar_%d'%i for i in range(1,len(i1)+1))])
        # self.vars['reallNextElemVar'] = reallNextElemVar
        # self.vars['realrNextElemVar'] = realrNextElemVar
        #
        # solver.add(If(Or([lSub == bot for lSub in makeTuple(elem1)]),
        #               And([lSub==i1Sub for lSub,i1Sub in zip(reallNextElemVar,i1)]),
        #               And([lSub==i1Sub for lSub,i1Sub in zip(reallNextElemVar,makeTuple(elem1))])))
        # solver.add(If(Or([rSub == bot for rSub in makeTuple(elem2)]),
        #               And([rSub==i2Sub for rSub,i2Sub in zip(realrNextElemVar,makeTuple(i2))]),
        #               And([rSub==i2Sub for rSub,i2Sub in zip(realrNextElemVar,makeTuple(elem2))])))
        #
        # print i1, reallNextElemVar
        #
        firstApp1 = UDFParser.substituteInFunc(foldFunction1, (i1, elem1), solver, self.vars)
        firstApp2 = UDFParser.substituteInFunc(foldFunction2, (i2, elem2), solver, self.vars)

        gInit1App = UDFParser.substituteInFunc(g1, i1, solver, self.vars)
        gInit2App = UDFParser.substituteInFunc(g2, i2, solver, self.vars)

        glApp = UDFParser.substituteInFunc(g1, firstApp1, solver, self.vars)
        grApp = UDFParser.substituteInFunc(g2, firstApp2, solver, self.vars)

        # Equality of init and induction implication should be valid. So their negation should be unsatisfiable
        formula = Not(And(gInit1App==gInit2App,
                              glApp==grApp))
        debug("Induction step (reduced for AggPair1Sync case) formula: %s", formula)
        solver.add(formula)

        return solverResult(solver)