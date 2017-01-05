import ast
import inspect
from z3 import Solver, sat, unsat, And, Implies, Not

import CallResult
import FoldResult
import Globals
from RDDTools import gen_name
from SolverTools import normalizeTuple
from SparkConverter import SparkConverter
from UDFParser import getSource, substituteInFuncDec
from WrapperClass import BoxedZ3IntVarNonBot, BoxedZ3Int
from tools import debug

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

class Verifier:
    def __init__(self, solver, vars):
        self.solver = solver
        self.vars = vars
        self.programs = {}

    def __init__(self):
        self.solver = Solver()
        self.programs = {}

    def parseProgram(self, f, name, index):
        source = getSource(f)
        parsedSource = ast.parse(source)
        self.programs[index] = parsedSource, f, name

    def calcTermForProgram(self, index, *rdds):
        debug("Original code %s", ast.dump(self.programs[index][0]))

        converter = SparkConverter(self.solver, self.programs[index][2], *rdds)
        converter.visit(self.programs[index][0])

        resultingTerm = converter.ret
        debug("Got Spark program term %s, type = %s", resultingTerm, type(resultingTerm))

        return converter

    def createProgramEnv(self, f, name, index, *rdds):
        self.parseProgram(f, name, index)
        return self.calcTermForProgram(index, *rdds)


    def verifyEquivalence(self, p1, p2, *rdds):
        print("")
        #
        fillAllFuncs(p1)
        fillAllFuncs(p2)

        result1 = self.createProgramEnv(p1, p1.__name__, 0, *rdds)
        result2 = self.createProgramEnv(p2, p2.__name__, 1, *rdds)

        """
        Check type:
            If fold level = 0, then it's NoAgg
            If fold level > 1, return False as we don't know how to handle it.
        """
        if result1.ret_fold_level != result2.ret_fold_level:
            return False

        if result1.ret_fold_level > 1:
            return False

        return self.verify(result1, result2)

    def verify(self, sc1, sc2):

        print "Comparing ", sc1.ret, sc2.ret
        print "Fold level: ", sc1.ret_fold_level
        print "Vars: ", sc1.ret_vars, sc2.ret_vars

        if sc1.ret_arity != sc2.ret_arity:
            return False

        ret1 = normalizeTuple(sc1.ret)
        ret2 = normalizeTuple(sc2.ret)

        print "Comparing ", ret1, ret2

        if isinstance(ret1, tuple) and isinstance(ret2, tuple):
           if len(ret1) != len(ret2):
               return False

           are_equivalent = True
           for e1, e2 in zip(ret1, ret2):
               if sc1.ret_fold_level > 0:
                   are_equivalent = self.verifyEquivalentFolds(normalizeTuple(e1), normalizeTuple(e2))
               else:
                    are_equivalent = self.verifyEquivalentElements(normalizeTuple(e1), normalizeTuple(e2))

               if are_equivalent == False:
                   return False

           return True

        if not isinstance(ret1, tuple) and not isinstance(ret2, tuple):
            if sc1.ret_fold_level > 0:
                return self.verifyEquivaentFolds(ret1, ret2, sc1, sc2)
            else:
                return self.verifyEquivalentElements(ret1, ret2)

    def isAgg1pairsync(self, foldRes1, foldRes2, programCtx1, programCtx2):
        pass


    def verifyEquivaentFolds(self, e1, e2, programCtx1, programCtx2):
        foldAndCallCtx1 = {}
        foldAndCallCtx1.update(programCtx1.foldResults)
        foldAndCallCtx1.update(programCtx1.callResults)

        foldAndCallCtx2 = {}
        foldAndCallCtx2.update(programCtx2.foldResults)
        foldAndCallCtx2.update(programCtx2.callResults)

        foldRes1 = foldAndCallCtx1[e1.name] # TODO what if it is a call on a boxedz3int?
        foldRes2 = foldAndCallCtx2[e2.name]

        print "Got fold/call results: ", foldRes1, foldRes2

        """ CHECK IF AGG1PAIRSYNC """
        if self.isAgg1pairsync(foldRes1,foldRes2, programCtx1, programCtx2):
            return self.verifyEquivalentSyncfolds(foldRes1, foldRes2, programCtx1, programCtx2)

        """ AGG1 """
        """
            Now we generate the following for each program:
            1. RepVarSet-s of the underlying fold terms
            2. Init of the fold substituted in the called functions (recurse) #TODO: Assume just one CallResult right now
            3. Intermediate value substituted in the call
            4. Calculate fold UDF function applied on the intermediate value -> "Advanced" value, and return "Advanced" value substituted in the call
        """
        def get_objects_for_agg1(foldRes, ctx):
            call_func = None
            call_args = None
            if isinstance(foldRes, CallResult.CallResult):
                call_func = foldRes.func
                call_args = foldRes.args
            else:
                call_args = (foldRes,)

            rep_var_sets = ()
            inits = ()
            intermediate_vars = ()
            advanced_vars = ()

            def handle_fold_result(foldResult, rep_var_sets, inits, intermediate_vars, advanced_vars):
                rep_var_sets += (foldResult.vars,)
                inits += (foldResult.init,)

                intermediate_var = BoxedZ3IntVarNonBot(gen_name("intermediate"), self.solver)
                advanced_var = substituteInFuncDec(Globals.funcs[foldResult.udf.id],
                                                   (intermediate_var, foldResult.term), self.solver)

                intermediate_vars += (intermediate_var,)
                advanced_vars += (advanced_var,)

                return rep_var_sets, inits, intermediate_vars, advanced_vars

            for call_arg in call_args:
                print "Generating for call_arg %s from %s"%(call_arg, foldRes)
                if (isinstance(call_arg, BoxedZ3Int)):
                    call_arg = ctx[call_arg.name]

                if isinstance(call_arg, FoldResult.FoldResult):
                    rep_var_sets, inits, intermediate_vars, advanced_vars = handle_fold_result(call_arg, rep_var_sets, inits, intermediate_vars, advanced_vars)
                else:
                    rep_var_sets += (set(),)
                    inits += (call_arg, )
                    intermediate_vars += (call_arg,)
                    advanced_vars += (call_arg,)

            if call_func != None:
                initApp = substituteInFuncDec(Globals.funcs[call_func], inits, self.solver)
                intermediateApp = substituteInFuncDec(Globals.funcs[call_func], intermediate_vars, self.solver)
                nextStepApp = substituteInFuncDec(Globals.funcs[call_func], advanced_vars, self.solver)
                return rep_var_sets, initApp, intermediateApp, nextStepApp

            return rep_var_sets, inits, intermediate_vars, advanced_vars


        rep_var_sets1, inits1, intermediate1, advanced1 = get_objects_for_agg1(foldRes1, foldAndCallCtx1)
        print rep_var_sets1, inits1, intermediate1, advanced1

        rep_var_sets2, inits2, intermediate2, advanced2 = get_objects_for_agg1(foldRes2, foldAndCallCtx2)
        print rep_var_sets2, inits2, intermediate2, advanced2

        if rep_var_sets1 != rep_var_sets2:
            print "Not equivalent due to different rep var sets"
            return False

        if isinstance(inits1, tuple):
            work_on_tuples = True
        else:
            work_on_tuples = False

        initComparison = True
        if work_on_tuples:
            for i1,i2 in zip(inits1,inits2):
                initComparison = And(initComparison, i1==i2)
        else:
            initComparison = inits1==inits2

        induction = True
        if work_on_tuples:
            for inter1,nextStep1,inter2,nextStep2, in zip(intermediate1,advanced1,intermediate2,advanced2):
                step = Implies((inter1==inter2),nextStep1==nextStep2)
                induction = And(induction,step)
        else:
            step = Implies((intermediate1==intermediate2),advanced1==advanced2)
            induction = And(induction, step)

        self.solver.push()
        self.solver.add(Not(And(initComparison, induction)))
        result = solverResult(self.solver)
        self.solver.pop()
        if result == unsat:
            self.solver.add(And(initComparison, induction))

        return result


    def verifyEquivalentElements(self, e1, e2):
        self.solver.push()
        self.solver.add(e1 != e2)
        result = solverResult(self.solver)
        self.solver.pop()
        if result == unsat:
            self.solver.add(e1 == e2)

        return result


def solverResult(solver):
    debug("Solver: %s", solver)
    # Solve - if UNSAT, equivalent.
    result = solver.check()
    print solver.sexpr()
    debug("Solver result = %s", result)
    if result == sat:
        print '\033[91m'+ "Not equivalent! Model showing inequivalence %s" % (solver.model()) + '\033[0m'
        return False
    else:
        if result == unsat:
            debug("Core: %s", solver.unsat_core())
            print '\033[94m' + "Equivalent!" + '\033[0m'
            return True
        else:
            print "Unknown: %s" % (result)
