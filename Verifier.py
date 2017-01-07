import ast
import inspect
from z3 import Solver, sat, unsat, And, Implies, Not, Exists, ForAll

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

    def setInputs(self, *inputs):
        self.inputs = inputs

    def parseProgram(self, f, name, index):
        source = getSource(f)
        parsedSource = ast.parse(source)
        self.programs[index] = parsedSource, f, name

    def calcTermForProgram(self, index, rdds):
        debug("Original code %s", ast.dump(self.programs[index][0]))

        converter = SparkConverter(self.solver, self.programs[index][2], rdds)
        converter.visit(self.programs[index][0])

        resultingTerm = converter.ret
        debug("Got Spark program term %s, type = %s", resultingTerm, type(resultingTerm))

        return converter

    def createProgramEnv(self, f, name, index, *rdds):
        self.parseProgram(f, name, index)
        return self.calcTermForProgram(index, *rdds)


    def verifyEquivalence(self, p1, p2):
        print("")
        #
        fillAllFuncs(p1)
        fillAllFuncs(p2)

        result1 = self.createProgramEnv(p1, p1.__name__, 0, self.inputs)
        result2 = self.createProgramEnv(p2, p2.__name__, 1, self.inputs)

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
           for e1, e2, element_index in zip(ret1, ret2, range(0,len(ret1))):
               if sc1.ret_fold_level > 0:
                   are_equivalent = self.verifyEquivalentFolds(normalizeTuple(e1), normalizeTuple(e2), sc1, sc2, element_index)
               else:
                    are_equivalent = self.verifyEquivalentElements(normalizeTuple(e1), normalizeTuple(e2), element_index)

               if are_equivalent == False:
                   return False

           return True

        if not isinstance(ret1, tuple) and not isinstance(ret2, tuple):
            if sc1.ret_fold_level > 0:
                return self.verifyEquivalentFolds(ret1, ret2, sc1, sc2)
            else:
                return self.verifyEquivalentElements(ret1, ret2)

    def get_refreshed_fold_elements(self, element_index):
        refreshed_inputs = tuple(map(lambda x: x.refresh_vars(), self.inputs))
        refreshed_result1 = self.calcTermForProgram(0, refreshed_inputs)
        refreshed_result2 = self.calcTermForProgram(1, refreshed_inputs)

        refreshed_result1_ret = normalizeTuple(refreshed_result1.ret)
        refreshed_result2_ret = normalizeTuple(refreshed_result2.ret)
        if element_index > -1:
            refreshed_results_zip = zip(refreshed_result1_ret, refreshed_result2_ret,
                                        range(0, len(refreshed_result1_ret)))
            relevant_refreshed_element1 = refreshed_results_zip[element_index]
            relevant_refreshed_element2 = refreshed_results_zip[element_index]

        else:
            relevant_refreshed_element1 = refreshed_result1_ret
            relevant_refreshed_element2 = refreshed_result2_ret

        refreshedFoldAndCallCtx1 = self.getFoldAndCallCtx(refreshed_result1)
        refreshedFoldAndCallCtx2 = self.getFoldAndCallCtx(refreshed_result2)

        return refreshedFoldAndCallCtx1, refreshedFoldAndCallCtx2, refreshedFoldAndCallCtx1[relevant_refreshed_element1.name], refreshedFoldAndCallCtx2[relevant_refreshed_element2.name]


    def verifyEquivalentSyncfolds(self, foldRes1, foldRes2, programCtx1, programCtx2, element_index):


        foldAndCallCtx1 = self.getFoldAndCallCtx(programCtx1)
        foldAndCallCtx2 = self.getFoldAndCallCtx(programCtx2)

        rep_var_sets1, inits1, intermediate1, advanced1 = self.get_objects_for_agg1(foldRes1, foldAndCallCtx1)
        print "For Fold1",foldRes1,":",rep_var_sets1, inits1, intermediate1, advanced1

        rep_var_sets2, inits2, intermediate2, advanced2 = self.get_objects_for_agg1(foldRes2, foldAndCallCtx2)
        print "For Fold2", foldRes2, ":",rep_var_sets2, inits2, intermediate2, advanced2

        # Need to refresh the vars - for the second application
        refreshed_ctx_for_secondapp1, refreshed_ctx_for_secondapp2, refreshed_fold_for_secondapp1, refreshed_fold_for_secondapp2 = self.get_refreshed_fold_elements(element_index)

        rep_var_sets_refreshed1, inits_refreshed1, intermediate_refreshed1, advanced_refreshed1 = self.get_objects_for_agg1(refreshed_fold_for_secondapp1, refreshed_ctx_for_secondapp1)
        print "For RefreshedFoldForSecondApp1",refreshed_fold_for_secondapp1,":",rep_var_sets_refreshed1,inits_refreshed1,intermediate_refreshed1,advanced_refreshed1

        rep_var_sets_refreshed2, inits_refreshed2, intermediate_refreshed2, advanced_refreshed2 = self.get_objects_for_agg1(refreshed_fold_for_secondapp2, refreshed_ctx_for_secondapp2)
        print "For RefreshedFoldForSecondApp2", refreshed_fold_for_secondapp2, ":", rep_var_sets_refreshed2, inits_refreshed2, intermediate_refreshed2, advanced_refreshed2


        pass

    def isAgg1pairsync(self, foldRes1, foldRes2, programCtx1, programCtx2, element_index = -1):

        call_func1 = None
        call_func2 = None
        def unfold_calls(potential_call):
            if isinstance(potential_call, CallResult.CallResult):
                return potential_call.args[0]
            else:
                return potential_call

        if isinstance(foldRes1, CallResult.CallResult):  # TODO: In our theory, aggpair1sync can only be on a single fold, so even if we have a call, it's a call with a single argument
            if len(foldRes1.args) > 1:
                return False

            call_func1 = foldRes1.func
            foldRes1 = foldRes1.args[0]

        if isinstance(foldRes2, CallResult.CallResult):  # TODO: In our theory, aggpair1sync can only be on a single fold, so even if we have a call, it's a call with a single argument
            if len(foldRes2.args) > 1:
                return False

            call_func2 = foldRes2.func
            foldRes2 = foldRes2.args[0]

        foldAndCallCtx1 = self.getFoldAndCallCtx(programCtx1)
        foldAndCallCtx2 = self.getFoldAndCallCtx(programCtx2)

        rep_var_sets1, inits1, intermediate1, advanced1 = self.get_objects_for_agg1(foldRes1, foldAndCallCtx1)
        print "For Fold1",foldRes1,":",rep_var_sets1, inits1, intermediate1, advanced1

        rep_var_sets2, inits2, intermediate2, advanced2 = self.get_objects_for_agg1(foldRes2, foldAndCallCtx2)
        print "For Fold2", foldRes2, ":",rep_var_sets2, inits2, intermediate2, advanced2

        # Need to refresh the vars - for the second application
        refreshed_ctx_for_secondapp1, refreshed_ctx_for_secondapp2, refreshed_fold_for_secondapp1, refreshed_fold_for_secondapp2 = self.get_refreshed_fold_elements(element_index)

        rep_var_sets_refreshed1, inits_refreshed1, intermediate_refreshed1, advanced_refreshed1 = self.get_objects_for_agg1(refreshed_fold_for_secondapp1, refreshed_ctx_for_secondapp1)
        print "For RefreshedFoldForSecondApp1",refreshed_fold_for_secondapp1,":",rep_var_sets_refreshed1,inits_refreshed1,intermediate_refreshed1,advanced_refreshed1

        rep_var_sets_refreshed2, inits_refreshed2, intermediate_refreshed2, advanced_refreshed2 = self.get_objects_for_agg1(refreshed_fold_for_secondapp2, refreshed_ctx_for_secondapp2)
        print "For RefreshedFoldForSecondApp2", refreshed_fold_for_secondapp2, ":", rep_var_sets_refreshed2, inits_refreshed2, intermediate_refreshed2, advanced_refreshed2

        refreshed_fold_for_secondapp1 = unfold_calls(refreshed_fold_for_secondapp1)
        refreshed_fold_for_secondapp2 = unfold_calls(refreshed_fold_for_secondapp2)

        # Need to refresh the vars - for the shrinked application
        refreshed_ctx_for_shrinked1, refreshed_ctx_for_shrinked2, refreshed_fold_for_shrink1, refreshed_fold_for_shrink2 = self.get_refreshed_fold_elements(element_index)

        rep_var_set_shrinked1, inits_shrinked1, intermediate_shrinked1, advanced_shrinked1 = self.get_objects_for_agg1(refreshed_fold_for_shrink1, refreshed_ctx_for_shrinked1)
        print "For RefreshsedFoldForShrinked1",refreshed_fold_for_shrink1,":",rep_var_set_shrinked1,inits_shrinked1,intermediate_shrinked1,advanced_shrinked1

        rep_var_set_shrinked2, inits_shrinked2, intermediate_shrinked2, advanced_shrinked2 = self.get_objects_for_agg1(refreshed_fold_for_shrink2, refreshed_ctx_for_shrinked2)
        print "For RefreshsedFoldForShrinked2", refreshed_fold_for_shrink2, ":", rep_var_set_shrinked2, inits_shrinked2, intermediate_shrinked2, advanced_shrinked2

        refreshed_fold_for_shrink1 = unfold_calls(refreshed_fold_for_shrink1)
        refreshed_fold_for_shrink2 = unfold_calls(refreshed_fold_for_shrink2)

        def from_boxed_var_to_complex_obj(obj, ctx):
            if isinstance(obj, BoxedZ3Int):
                return ctx[obj.name]
            return obj

        foldResObj1 = from_boxed_var_to_complex_obj(foldRes1, foldAndCallCtx1)
        foldResObj2 = from_boxed_var_to_complex_obj(foldRes2, foldAndCallCtx2)
        refreshed_for_secondapp_obj1 = from_boxed_var_to_complex_obj(refreshed_fold_for_secondapp1, refreshed_ctx_for_secondapp1)
        refreshed_for_secondapp_obj2 = from_boxed_var_to_complex_obj(refreshed_fold_for_secondapp2, refreshed_ctx_for_secondapp2)
        refreshed_for_shrinked_obj1 = from_boxed_var_to_complex_obj(refreshed_fold_for_shrink1, refreshed_ctx_for_shrinked1)
        refreshed_for_shrinked_obj2 = from_boxed_var_to_complex_obj(refreshed_fold_for_shrink2, refreshed_ctx_for_shrinked2)

        firstApp1 = substituteInFuncDec(Globals.funcs[foldResObj1.udf.id], (foldResObj1.init, foldResObj1.term), self.solver)
        secondApp1 = substituteInFuncDec(Globals.funcs[foldResObj1.udf.id], (firstApp1, refreshed_for_secondapp_obj1.term), self.solver)
        shrinked1 = substituteInFuncDec(Globals.funcs[foldResObj1.udf.id], (foldResObj1.init, refreshed_for_shrinked_obj1.term), self.solver)

        firstApp2 = substituteInFuncDec(Globals.funcs[foldResObj2.udf.id], (foldResObj2.init, foldResObj2.term), self.solver)
        secondApp2 = substituteInFuncDec(Globals.funcs[foldResObj2.udf.id], (firstApp2, refreshed_for_secondapp_obj2.term), self.solver)
        shrinked2 = substituteInFuncDec(Globals.funcs[foldResObj2.udf.id], (foldResObj2.init, refreshed_for_shrinked_obj2.term), self.solver)

        # There is an assumption that secondApp1, secondApp2, shrinked1, shrinked2 are all BoxedZ3Int-s that we can refer to whose 'val' fields.
        # TODO: If those are tuples, include all elements. Also map all to val, and make sure all tuple elements are indeed such ints - if not, consider allocating "s" variables specialized for it.
        self.solver.push()
        formula = Exists(list(normalizeTuple(rep_var_sets1)),
                            Exists(list(normalizeTuple(rep_var_sets_refreshed1)),
                                ForAll(list(normalizeTuple(rep_var_set_shrinked1).union(set([secondApp1.val]).union(set([secondApp2.val]).union(set([shrinked1.val]).union(set([shrinked2.val])))))),
                                   Not(And(secondApp1==shrinked1,secondApp2==shrinked2)))))
        print "AggPair1Sync containment check formula:",formula
        self.solver.add(formula)
        result = solverResult(self.solver)
        self.solver.pop()

        if result :
            print "This example is AggPair1Sync"
        else:
            print "This example is not AggPair1Sync"

        return result


    """
        Now we generate the following for each program:
        1. RepVarSet-s of the underlying fold terms
        2. Init of the fold substituted in the called functions (recurse) #TODO: Assume just one CallResult right now
        3. Intermediate value substituted in the call
        4. Calculate fold UDF function applied on the intermediate value -> "Advanced" value, and return "Advanced" value substituted in the call
    """
    def get_objects_for_agg1(self, foldRes, ctx):
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

    def getFoldAndCallCtx(self, programCtx):
        ctx = {}
        ctx.update(programCtx.foldResults)
        ctx.update(programCtx.callResults)
        return ctx

    def verifyEquivalentFolds(self, e1, e2, programCtx1, programCtx2, element_index = -1):
        foldAndCallCtx1 = self.getFoldAndCallCtx(programCtx1)
        foldAndCallCtx2 = self.getFoldAndCallCtx(programCtx2)

        foldRes1 = foldAndCallCtx1[e1.name] # TODO what if it is a call on a boxedz3int?
        foldRes2 = foldAndCallCtx2[e2.name]

        print "Got fold/call results: ", foldRes1, foldRes2

        """ CHECK IF AGG1PAIRSYNC """
        if self.isAgg1pairsync(foldRes1,foldRes2, programCtx1, programCtx2, element_index):
            return self.verifyEquivalentSyncfolds(foldRes1, foldRes2, programCtx1, programCtx2, element_index)

        """ AGG1 """

        rep_var_sets1, inits1, intermediate1, advanced1 = self.get_objects_for_agg1(foldRes1, foldAndCallCtx1)
        print "For Fold1",foldRes1,":",rep_var_sets1, inits1, intermediate1, advanced1

        rep_var_sets2, inits2, intermediate2, advanced2 = self.get_objects_for_agg1(foldRes2, foldAndCallCtx2)
        print "For Fold2", foldRes2, ":",rep_var_sets2, inits2, intermediate2, advanced2

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


    def verifyEquivalentElements(self, e1, e2, element_index=-1):
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
