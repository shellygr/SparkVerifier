import ast
import inspect
from z3 import Solver, sat, unsat, And, Implies, Not, Exists, ForAll, simplify, BoolRef, BoolVal, is_const, is_false, \
    set_option

import CallResult
import FoldResult
import Globals
from RDDTools import gen_name
from SolverTools import normalizeTuple
from SparkConverter import SparkConverter
from UDFParser import getSource, substituteInFuncDec
from WrapperClass import BoxedZ3IntVarNonBot, BoxedZ3Int, BoxedZ3IntVar, BoxedZ3IntVal, bot, Bot
from tools import debug

class FuncDbBuilder(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        # debug("Adding func name %s with above src", node.name)
        Globals.funcs[node.name] = node

def fillAllFuncs(p):
    module = inspect.getmodule(p)
    # debug("Module of function %s is %s", p, module)
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

        converter = SparkConverter(self.programs[index][2], rdds)
        converter.visit(self.programs[index][0])

        resultingTerm = converter.ret
        debug("Got Spark program term %s, type = %s", resultingTerm, type(resultingTerm))

        return converter

    def createProgramEnv(self, f, name, index, *rdds):
        self.parseProgram(f, name, index)
        return self.calcTermForProgram(index, *rdds)


    def verifyEquivalence(self, p1, p2):
        # Parse all functions and UDFs in the given Spark programs
        fillAllFuncs(p1)
        fillAllFuncs(p2)

        # Create a program term (it is internally a set of formulas which are added to the solver).
        # The result also calculates various metadata regarding the type of the expression and the syntactic class.
        result1 = self.createProgramEnv(p1, p1.__name__, 0, self.inputs)
        result2 = self.createProgramEnv(p2, p2.__name__, 1, self.inputs)

        self.solver.add(result1.formulas)
        self.solver.add(result2.formulas)
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

    def is_fold(self, e, sc):
        foldAndCallCtx = self.getFoldAndCallCtx(sc)

        if (not isinstance(e, BoxedZ3Int) and not isinstance(e, set)) or (
            isinstance(e, BoxedZ3Int) and ('*' in e.name or '+' in e.name or '-' in e.name)):
                return False, None
        if isinstance(e, set):
            is_fold_result = False
            for elm in e:
                is_fold_result, candidate = self.is_fold(elm, sc)
                if is_fold_result:
                    sc.foldResults[elm.name] = candidate
                    return is_fold_result, candidate

            return is_fold_result, None
                # return any(map(lambda x: is_fold(x, sc)[0], e))

        if e.name in foldAndCallCtx:
            return True, foldAndCallCtx[e.name]

        is_fold_result, fold = self.is_fold(sc.var_dependency[e.name], sc)
        if is_fold_result:
            sc.foldResults[e.name] = fold
        return is_fold_result, fold

    def verify(self, sc1, sc2):
        # Verifies equivalence of each component in the result (if a tuple or tuple of tuples. Depth is limited to 2.)
        if sc1.ret_arity != sc2.ret_arity:
            return False

        ret1 = normalizeTuple(sc1.ret)
        ret2 = normalizeTuple(sc2.ret)

        if isinstance(ret1, tuple) and isinstance(ret2, tuple):
           if len(ret1) != len(ret2):
               return False

           are_equivalent = True
           for e1, e2, element_index in zip(ret1, ret2, range(0,len(ret1))):
               debug("Comparing %s and %s (index %d)", e1, e2, element_index)

               if self.is_fold(normalizeTuple(e1), sc1)[0] and self.is_fold(normalizeTuple(e2), sc2)[0]:
                   are_equivalent = self.verifyEquivalentFolds(normalizeTuple(e1), normalizeTuple(e2), sc1, sc2, element_index)
               else:
                   e1 = normalizeTuple(e1)
                   e2 = normalizeTuple(e2)
                   if isinstance(e1, tuple) and isinstance(e2, tuple) and len(e1) != len(e2):
                       return False

                   if isinstance(e1, tuple):
                       for e1b, e2b, element_index_b in zip(e1, e2, range(0,len(e1))):
                           debug("Comparing %s and %s (index %d)", e1b, e2b, element_index_b)
                           if self.is_fold(normalizeTuple(e1b),sc1)[0] and self.is_fold(normalizeTuple(e2b), sc2)[0]:
                               are_equivalent = self.verifyEquivalentFolds(normalizeTuple(e1b), normalizeTuple(e2b), sc1, sc2, element_index_b)
                           else:
                               are_equivalent = self.verifyEquivalentElements(normalizeTuple(e1b), normalizeTuple(e2b), element_index_b)

                           if are_equivalent == False:
                               return False
                   else:
                       are_equivalent = self.verifyEquivalentElements(normalizeTuple(e1), normalizeTuple(e2), element_index)

               if are_equivalent == False:
                   return False

           return True

        if not isinstance(ret1, tuple) and not isinstance(ret2, tuple):
            debug("Comparing %s and %s", ret1, ret2)
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
            relevant_refreshed_element1 = normalizeTuple(refreshed_results_zip[element_index][0])
            relevant_refreshed_element2 = normalizeTuple(refreshed_results_zip[element_index][1])

        else:
            relevant_refreshed_element1 = refreshed_result1_ret
            relevant_refreshed_element2 = refreshed_result2_ret

        refreshedFoldAndCallCtx1 = self.getFoldAndCallCtx(refreshed_result1)
        refreshedFoldAndCallCtx2 = self.getFoldAndCallCtx(refreshed_result2)

        return refreshedFoldAndCallCtx1, refreshedFoldAndCallCtx2, refreshedFoldAndCallCtx1[relevant_refreshed_element1.name], refreshedFoldAndCallCtx2[relevant_refreshed_element2.name], refreshed_result1.formulas, refreshed_result2.formulas, refreshed_result1.var_defs, refreshed_result2.var_defs

    #TODO: Create in SparkConverter a formula map - from new variable name to the formula that defines it, and add only the required formulas for clarity/correctness.
    def verifyEquivalentSyncfolds(self, foldRes1, foldRes2, programCtx1, programCtx2, element_index):

        call_func1 = None
        call_func2 = None

        if isinstance(foldRes1, CallResult.CallResult):  # TODO: In our theory, aggpair1sync can only be on a single fold, so even if we have a call, it's a call with a single argument
            if len(foldRes1.args) > 1:
                return False

            call_func1 = foldRes1.func
            foldRes1 = foldRes1.args[0]
        else:
            call_func1 = "id"

        if isinstance(foldRes2, CallResult.CallResult):  # TODO: In our theory, aggpair1sync can only be on a single fold, so even if we have a call, it's a call with a single argument
            if len(foldRes2.args) > 1:
                return False

            call_func2 = foldRes2.func
            foldRes2 = foldRes2.args[0]
        else:
            call_func2 = "id"

        foldAndCallCtx1 = self.getFoldAndCallCtx(programCtx1)
        foldAndCallCtx2 = self.getFoldAndCallCtx(programCtx2)

        rep_var_sets1, inits1, intermediate1, advanced1, formulas1, var_defs1 = self.get_objects_for_agg1(foldRes1, foldAndCallCtx1)
        rep_var_sets2, inits2, intermediate2, advanced2, formulas2, var_defs2 = self.get_objects_for_agg1(foldRes2, foldAndCallCtx2)

        if rep_var_sets1 != rep_var_sets2:
            debug("Not equivalent due to different rep var sets")
            return False

        # Need to refresh the vars - for the second application
        refreshed_ctx_for_secondapp1, refreshed_ctx_for_secondapp2, refreshed_fold_for_secondapp1, refreshed_fold_for_secondapp2, formulas_secondapp1, formulas_secondapp2, var_defs_secondapp1, var_defs_secondapp2 = self.get_refreshed_fold_elements(element_index)
        self.solver.add(formulas_secondapp1)
        self.solver.add(formulas_secondapp2)

        rep_var_sets_refreshed1, inits_refreshed1, intermediate_refreshed1, advanced_refreshed1, formulas_refreshed1, var_defs_refreshed1 = self.get_objects_for_agg1(refreshed_fold_for_secondapp1, refreshed_ctx_for_secondapp1)
        rep_var_sets_refreshed2, inits_refreshed2, intermediate_refreshed2, advanced_refreshed2, formulas_refreshed2, var_defs_refreshed2 = self.get_objects_for_agg1(refreshed_fold_for_secondapp2, refreshed_ctx_for_secondapp2)

        self.solver.add(formulas1)
        self.solver.add(formulas2)
        self.solver.add(formulas_refreshed1)
        self.solver.add(formulas_refreshed2)

        refreshed_fold_for_secondapp1 = self.unfold_calls(refreshed_fold_for_secondapp1)
        refreshed_fold_for_secondapp2 = self.unfold_calls(refreshed_fold_for_secondapp2)

        foldResObj1 = self.from_boxed_var_to_complex_obj(foldRes1, foldAndCallCtx1)
        foldResObj2 = self.from_boxed_var_to_complex_obj(foldRes2, foldAndCallCtx2)
        refreshed_for_secondapp_obj1 = self.from_boxed_var_to_complex_obj(refreshed_fold_for_secondapp1,
                                                                          refreshed_ctx_for_secondapp1)
        refreshed_for_secondapp_obj2 = self.from_boxed_var_to_complex_obj(refreshed_fold_for_secondapp2,
                                                                          refreshed_ctx_for_secondapp2)

        firstApp1 = substituteInFuncDec(Globals.funcs[foldResObj1.udf.id], (foldResObj1.init, foldResObj1.term),
                                        self.solver, {}, {}, True)
        secondApp1 = substituteInFuncDec(Globals.funcs[foldResObj1.udf.id],
                                         (firstApp1, refreshed_for_secondapp_obj1.term), self.solver, {}, {}, True)

        firstApp2 = substituteInFuncDec(Globals.funcs[foldResObj2.udf.id], (foldResObj2.init, foldResObj2.term),
                                        self.solver, {}, {}, True)
        secondApp2 = substituteInFuncDec(Globals.funcs[foldResObj2.udf.id],
                                         (firstApp2, refreshed_for_secondapp_obj2.term), self.solver, {}, {}, True)

        if call_func1:
            initsInCall1 = substituteInFuncDec(Globals.funcs[call_func1], inits1, self.solver, {})
            firstInCall1 = substituteInFuncDec(Globals.funcs[call_func1], firstApp1, self.solver, {})
            secondInCall1 = substituteInFuncDec(Globals.funcs[call_func1], secondApp1, self.solver, {})
        else:
            initsInCall1 = normalizeTuple(inits1)
            firstInCall1 = firstApp1
            secondInCall1 = secondApp1

        if call_func2:
            initsInCall2 = substituteInFuncDec(Globals.funcs[call_func2], inits2, self.solver, {})
            firstInCall2 = substituteInFuncDec(Globals.funcs[call_func2], firstApp2, self.solver, {})
            secondInCall2 = substituteInFuncDec(Globals.funcs[call_func2], secondApp2, self.solver, {})
        else:
            initsInCall2 = normalizeTuple(inits2)
            firstInCall2 = firstApp2
            secondInCall2 = secondApp2

        if isinstance(initsInCall1, tuple):
            work_on_tuples = True
        else:
            work_on_tuples = False

        initComparison = True
        if work_on_tuples:
            for i1,i2 in zip(initsInCall1,initsInCall2):
                initComparison = And(initComparison, i1==i2)
        else:
            initComparison = initsInCall1==initsInCall2

        induction = True
        if work_on_tuples:
            for app1a,app2a,app1b,app2b in zip(firstInCall1, secondInCall1, firstInCall2, secondInCall2):
                step = Implies((app1a==app1b),app2a==app2b)
                induction = And(induction,step)
        else:
            step = Implies((firstInCall1==firstInCall2),secondInCall1==secondInCall2)
            induction = And(induction, step)

        self.solver.push()
        self.solver.add(Not(And(initComparison, induction)))
        result = solverResult(self.solver)
        self.solver.pop()
        if result == unsat:
            self.solver.add(And(initComparison, induction))

        return result

    def unfold_calls(self, potential_call):
        if isinstance(potential_call, CallResult.CallResult):
            return potential_call.args[0]
        else:
            return potential_call

    def from_boxed_var_to_complex_obj(self, obj, ctx):
        if isinstance(obj, BoxedZ3Int):
            return ctx[obj.name]
        return obj

    def make_vars(self, expression):
        if isinstance(expression, tuple):
            tup = ()
            base_name = gen_name("n")
            for elm in expression:
                new_var_elm = BoxedZ3IntVar(gen_name(base_name))
                self.solver.add(new_var_elm==elm)
                tup += (new_var_elm,)

            return tup
        else:
            new_var = BoxedZ3IntVar(gen_name("n"))
            debug("%s == %s", new_var, expression)
            self.solver.add(new_var==expression)
            return new_var

    def isAgg1pairsync(self, foldRes1, foldRes2, programCtx1, programCtx2, element_index = -1):

        self.solver.push()

        if isinstance(foldRes1, CallResult.CallResult):  # TODO: In our theory, aggpair1sync can only be on a single fold, so even if we have a call, it's a call with a single argument
            if len(foldRes1.args) > 1:
                return False

            foldRes1 = foldRes1.args[0]

        if isinstance(foldRes2, CallResult.CallResult):  # TODO: In our theory, aggpair1sync can only be on a single fold, so even if we have a call, it's a call with a single argument
            if len(foldRes2.args) > 1:
                return False

            foldRes2 = foldRes2.args[0]

        foldAndCallCtx1 = self.getFoldAndCallCtx(programCtx1)
        foldAndCallCtx2 = self.getFoldAndCallCtx(programCtx2)

        rep_var_sets1, inits1, intermediate1, advanced1, formulas1, var_defs1 = self.get_objects_for_agg1(foldRes1, foldAndCallCtx1)

        # Need to refresh the vars - for the second application
        refreshed_ctx_for_secondapp1, refreshed_ctx_for_secondapp2, refreshed_fold_for_secondapp1, refreshed_fold_for_secondapp2, formulas_secondapp1, formulas_secondapp2, var_deps_secondapp1, var_deps_secondapp2 = self.get_refreshed_fold_elements(element_index)
        #
        rep_var_sets_refreshed1, inits_refreshed1, intermediate_refreshed1, advanced_refreshed1, formulas_refreshed1, var_defs_refreshed1 = self.get_objects_for_agg1(refreshed_fold_for_secondapp1, refreshed_ctx_for_secondapp1)

        refreshed_fold_for_secondapp1 = self.unfold_calls(refreshed_fold_for_secondapp1)
        refreshed_fold_for_secondapp2 = self.unfold_calls(refreshed_fold_for_secondapp2)

        # Need to refresh the vars - for the shrinked application
        refreshed_ctx_for_shrinked1, refreshed_ctx_for_shrinked2, refreshed_fold_for_shrink1, refreshed_fold_for_shrink2, formulas_shrinked1, formulas_shrinked2, var_deps_shrinked1, var_deps_shrinked2 = self.get_refreshed_fold_elements(element_index)
        rep_var_set_shrinked1, inits_shrinked1, intermediate_shrinked1, advanced_shrinked1, formulas_shrinked_agg1, var_defs_shrinked1 = self.get_objects_for_agg1(refreshed_fold_for_shrink1, refreshed_ctx_for_shrinked1)

        refreshed_fold_for_shrink1 = self.unfold_calls(refreshed_fold_for_shrink1)
        refreshed_fold_for_shrink2 = self.unfold_calls(refreshed_fold_for_shrink2)

        foldResObj1 = self.from_boxed_var_to_complex_obj(foldRes1, foldAndCallCtx1)
        foldResObj2 = self.from_boxed_var_to_complex_obj(foldRes2, foldAndCallCtx2)
        refreshed_for_secondapp_obj1 = self.from_boxed_var_to_complex_obj(refreshed_fold_for_secondapp1, refreshed_ctx_for_secondapp1)
        refreshed_for_secondapp_obj2 = self.from_boxed_var_to_complex_obj(refreshed_fold_for_secondapp2, refreshed_ctx_for_secondapp2)
        refreshed_for_shrinked_obj1 = self.from_boxed_var_to_complex_obj(refreshed_fold_for_shrink1, refreshed_ctx_for_shrinked1)
        refreshed_for_shrinked_obj2 = self.from_boxed_var_to_complex_obj(refreshed_fold_for_shrink2, refreshed_ctx_for_shrinked2)

        firstApp1_formula_set = set()
        firstApp1 = substituteInFuncDec(Globals.funcs[foldResObj1.udf.id], (foldResObj1.init, foldResObj1.term), firstApp1_formula_set, programCtx1.var_defs, {}, True)
        secondApp1_formula_set = set()
        secondApp1 = substituteInFuncDec(Globals.funcs[foldResObj1.udf.id], (firstApp1, refreshed_for_secondapp_obj1.term), secondApp1_formula_set, programCtx1.var_defs, {}, True)
        shrinked1_formula_set = set()
        shrinked_defs1 = {}
        shrinked1 = substituteInFuncDec(Globals.funcs[foldResObj1.udf.id], (foldResObj1.init, refreshed_for_shrinked_obj1.term), shrinked1_formula_set, shrinked_defs1, {}, True)

        firstApp2_formula_set = set()
        firstApp2 = substituteInFuncDec(Globals.funcs[foldResObj2.udf.id], (foldResObj2.init, foldResObj2.term), firstApp2_formula_set, programCtx2.var_defs, {}, True)
        secondApp2_formula_set = set()
        secondApp2 = substituteInFuncDec(Globals.funcs[foldResObj2.udf.id], (firstApp2, refreshed_for_secondapp_obj2.term), secondApp2_formula_set, programCtx2.var_defs, {}, True)
        shrinked2_formula_set = set()
        shrinked_defs2 = {}
        shrinked2 = substituteInFuncDec(Globals.funcs[foldResObj2.udf.id], (foldResObj2.init, refreshed_for_shrinked_obj2.term), shrinked2_formula_set, shrinked_defs2, {}, True)

        if isinstance(shrinked1, tuple):
            work_on_tuples = True
        else:
            work_on_tuples = False

        syncEquivalenceConjunction = True
        if work_on_tuples:
            for s1,sh1,s2,sh2 in secondApp1,shrinked1,secondApp2,shrinked2:
                syncEquivalenceConjunction = And(syncEquivalenceConjunction, s1==sh1, s2==sh2)
        else:
            syncEquivalenceConjunction = And(secondApp1==shrinked1,secondApp2==shrinked2)


        def conjunctOfAll(*formulas):
            conjunct = True
            for formulaSet in formulas:
                for formula in formulaSet:
                    conjunct = And(conjunct, formula)

            return conjunct

        keys_are_equal = True
        if None != foldResObj1.key_vars and None != foldResObj2.key_vars:
            keys_are_equal = And(foldResObj1.key_vars == refreshed_for_secondapp_obj1.key_vars,
                                 foldResObj1.key_vars == refreshed_for_shrinked_obj1.key_vars,
                                 foldResObj2.key_vars == refreshed_for_secondapp_obj2.key_vars,
                                 foldResObj2.key_vars == refreshed_for_shrinked_obj2.key_vars)

        # TODO: If those are tuples, include all elements. Also map all to val, and make sure all tuple elements are indeed such ints - if not, consider allocating "s" variables specialized for it.
        self.solver.push()
        self.solver.add(conjunctOfAll(formulas_secondapp1, formulas_secondapp2, firstApp1_formula_set, firstApp2_formula_set, secondApp1_formula_set, secondApp2_formula_set))
        formula = Exists(list(normalizeTuple(rep_var_sets1)),
                            Exists(list(set(normalizeTuple(rep_var_sets_refreshed1)).difference(refreshed_for_secondapp_obj1.key_vars)),
                                ForAll(list(set(normalizeTuple(rep_var_set_shrinked1))
                                            .union(set(map(lambda x: Globals.boxed_var_name_to_var[x].val, var_defs_shrinked1.keys())))
                                            .union(set(filter(lambda x: not is_false(x),
                                                              map(lambda x: Globals.boxed_var_name_to_var[x].isBot, var_defs_shrinked1.keys()))))
                                            .union(set(map(lambda x: Globals.boxed_var_name_to_var[x].val, shrinked_defs1.keys())))
                                            .union(set(filter(lambda x: not is_false(x),
                                                              map(lambda x: Globals.boxed_var_name_to_var[x].isBot, shrinked_defs1.keys()))))
                                            .union(set(map(lambda x: Globals.boxed_var_name_to_var[x].val, shrinked_defs2.keys())))
                                            .union(set(filter(lambda x: not is_false(x),
                                                              map(lambda x: Globals.boxed_var_name_to_var[x].isBot,
                                                                  shrinked_defs2.keys()))))
                                            .union(set(filter(lambda x: not is_false(x),
                                                              map(lambda x: Globals.boxed_var_name_to_var[x].val,
                                                                  var_deps_shrinked1.keys()))))
                                            .union(set(filter(lambda x: not is_false(x),
                                                              map(lambda x: Globals.boxed_var_name_to_var[x].val,
                                                                  var_deps_shrinked2.keys()))))
                                            .union(set(filter(lambda x: not is_false(x),
                                                              map(lambda x: Globals.boxed_var_name_to_var[x].isBot,
                                                                  var_deps_shrinked1.keys()))))
                                            .union(set(filter(lambda x: not is_false(x),
                                                              map(lambda x: Globals.boxed_var_name_to_var[x].isBot,
                                                                  var_deps_shrinked2.keys()))))
                                            .difference(refreshed_for_shrinked_obj1.key_vars)),
                                   Implies(And(simplify(conjunctOfAll(formulas_shrinked1, formulas_shrinked2,
                                                                      shrinked1_formula_set, shrinked2_formula_set)),
                                                keys_are_equal),
                                                Not(syncEquivalenceConjunction)))))
        self.solver.add(formula)
        result = solverResult(self.solver, "Not AggOneSync!", "Instance is AggOneSync!")
        self.solver.pop()

        if result:
            debug("This example is AggOneSync")
        else:
            debug("This example is not AggOneSync")

        self.solver.pop()
        return result


    """
        Now we generate the following for each program:
        1. RepVarSet-s of the underlying fold terms
        2. Init of the fold substituted in the called functions (recurse) #TODO: Assume just one CallResult right now
        3. Intermediate value substituted in the call
        4. Calculate fold UDF function applied on the intermediate value -> "Advanced" value, and return "Advanced" value substituted in the call
    """
    def get_objects_for_agg1(self, foldRes, ctx, var_defs = {}):
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
        formulas = set()

        def handle_fold_result(foldResult, rep_var_sets, inits, intermediate_vars, advanced_vars):
            formulas = set() # TODO: Must replace self.solver properly!!!
            rep_var_sets += (foldResult.vars,)
            inits += (foldResult.init,)

            intermediate_var = BoxedZ3IntVarNonBot(gen_name("intermediate"))
            advanced_var = substituteInFuncDec(Globals.funcs[foldResult.udf.id],
                                               (intermediate_var, foldResult.term), formulas, var_defs, {}, True)

            intermediate_vars += (intermediate_var,)
            advanced_vars += (advanced_var,)

            return rep_var_sets, inits, intermediate_vars, advanced_vars, formulas, var_defs

        for call_arg in call_args:
            if (isinstance(call_arg, BoxedZ3Int)):
                call_arg = ctx[call_arg.name]

            if isinstance(call_arg, FoldResult.FoldResult):
                rep_var_sets, inits, intermediate_vars, advanced_vars, formulas, var_defs = handle_fold_result(call_arg, rep_var_sets, inits, intermediate_vars, advanced_vars)
            else:
                rep_var_sets += (set(),)
                inits += (call_arg, )
                intermediate_vars += (call_arg,)
                advanced_vars += (call_arg,)

        if call_func != None:
            initApp = substituteInFuncDec(Globals.funcs[call_func], inits, formulas, var_defs)
            intermediateApp = substituteInFuncDec(Globals.funcs[call_func], intermediate_vars, formulas, var_defs)
            nextStepApp = substituteInFuncDec(Globals.funcs[call_func], advanced_vars, formulas, var_defs)
            return rep_var_sets, initApp, intermediateApp, nextStepApp, formulas, var_defs

        return rep_var_sets, inits, intermediate_vars, advanced_vars, formulas, var_defs

    def getFoldAndCallCtx(self, programCtx):
        ctx = {}
        ctx.update(programCtx.foldResults)
        ctx.update(programCtx.callResults)
        return ctx

    def verifyEquivalentFolds(self, e1, e2, programCtx1, programCtx2, element_index = -1):
        foldAndCallCtx1 = self.getFoldAndCallCtx(programCtx1)
        foldAndCallCtx2 = self.getFoldAndCallCtx(programCtx2)

        is_fold_1, foldRes1 = self.is_fold(e1, programCtx1)
        is_fold_2, foldRes2 = self.is_fold(e2, programCtx2)

        """ CHECK IF AGG1PAIRSYNC """
        if self.isAgg1pairsync(foldRes1,foldRes2, programCtx1, programCtx2, element_index):
            return self.verifyEquivalentSyncfolds(foldRes1, foldRes2, programCtx1, programCtx2, element_index)

        """ AGG1 """
        rep_var_sets1, inits1, intermediate1, advanced1, formulas1, var_defs1 = self.get_objects_for_agg1(foldRes1, foldAndCallCtx1, programCtx1.var_defs)
        rep_var_sets2, inits2, intermediate2, advanced2, formulas2, var_defs2 = self.get_objects_for_agg1(foldRes2, foldAndCallCtx2, programCtx2.var_defs)

        self.solver.add(formulas1)
        self.solver.add(formulas2)

        if rep_var_sets1 != rep_var_sets2:
            debug("Not equivalent due to different rep var sets")
            return False

        if isinstance(inits1, tuple):
            work_on_tuples = True
        else:
            work_on_tuples = False

        initComparison = True
        if work_on_tuples:
            for i1,i2 in zip(inits1,inits2):
                initComparison = And(initComparison, i1.n==i2.n)
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

        debug("Base formula: %s",initComparison)
        debug("Induction formula: %s",induction)
        self.solver.push()
        self.solver.add(Not(And(initComparison, induction)))
        result = solverResult(self.solver)
        self.solver.pop()
        if result == unsat:
            self.solver.add(And(initComparison, induction))

        return result

    # Check a single component from each program
    def verifyEquivalentElements(self, e1, e2, element_index=-1):
        self.solver.push()
        self.solver.add(e1 != e2)
        result = solverResult(self.solver)
        self.solver.pop()
        if result == True:
            self.solver.add(e1 == e2)
            self.solver.add(Bot() != e1)

        return result


def solverResult(solver, sat_message = "Not equivalent!", unsat_message = "Equivalent!"):
    set_option(max_lines=2000, max_depth=1000000, max_args=100000)
    # debug("Solver: %s", solver)
    # Solve - if UNSAT, equivalent.
    result = solver.check()
    debug("Solver result = %s", result)
    if result == sat:
        print '\033[91m'+ "%s Model: %s" % (sat_message, solver.model()) + '\033[0m'
        return False
    else:
        if result == unsat:
            debug("Core: %s", solver.unsat_core())
            print '\033[94m' + "%s" % (unsat_message) + '\033[0m'
            return True
        else:
            print "Unknown: %s" % (result)
