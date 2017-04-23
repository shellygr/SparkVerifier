import ast

import itertools
from z3 import If, And, Or, simplify

import Globals
from CallResult import CallResult
from FoldResult import FoldResult
from RDDTools import gen_name
from SolverTools import makeTuple, normalizeTuple
from UDFParser import substituteInFuncDec
from WrapperClass import bot, BoxedZ3IntVar, Bot, BoxedZ3Int, BoxedZ3IntVarNonBot
from tools import debug

class SparkConverter(ast.NodeVisitor):
    # Solver is Z3
    # Vars are all the vars we keep for the solver  -  TODO: Get rid of it!
    # Program name is the name of the function representing the spark program
    # rdds is a list of the concrete arguments from which we infer type information
    def __init__(self, programName, rdds):
        self.formulas = set() # Need to also append all env to the solver in the end, but still required: for example, for filter
        self.var_defs = {}
        self.programName = programName
        self.rdds = rdds
        self.env = {} # Variables in the program to their bag expression, arity of bag expression, RepVarSet, fold level (default 0)
        self.foldResults = {} # Names of folds are mapped to their FoldResult
        self.callResults = {} # Names of calls are mapped to their CallResult
        self.ret = None # Bag expression type
        self.ret_arity = 0
        self.ret_vars = {}
        self.ret_fold_level = 0
        self.var_dependency = {}

    def visit_FunctionDef(self, node):
        if node.name == self.programName:

            for i in range(0, len(node.args.args)): # each argument should be mapped to the concrete argument
                arg = node.args.args[i]

                # Each arg must be a name node
                self.env[arg.id] = self.rdds[i].vars, self.rdds[i].arity, set(self.rdds[i].vars), 0

            for line in node.body:
                self.visit(line) # only support Return, Assign and If (if is allowed only on primitives, so avoiding it - not really supported)

    def visit_Return(self, node):
        # Return must be non-void
        ret, ret_arity, ret_vars, ret_fold_level = self.visit(node.value)
        self.ret = ret
        self.ret_arity = ret_arity
        self.ret_vars = ret_vars
        self.ret_fold_level = ret_fold_level


    def visit_Assign(self, node):
        # Assume a single target
        target = node.targets[0]
        value = node.value

        parsed_value, parsed_value_arity, parsed_value_vars, parsed_value_fold_level = self.visit(value)

        # The target is a name
        self.env[target.id] = parsed_value, parsed_value_arity, parsed_value_vars, parsed_value_fold_level

    # Now we handle expressions - it's only spark operations, and function renames, so handling Name and Call
    # TODO: We may want to support usual operations for primitives symbolically
    def visit_Name(self, node):
        return self.env[node.id]

    def visit_Call(self, node):
        # Func is an attribute if it is an RDD operation, and name if it's a simple call (for primitives, not for RDDs!).
        if isinstance(node.func, ast.Name):
            def create_call_vars(callResult, result_arity, additional_dependency=set()):
                call_vars = ()
                name_base = gen_name("c")
                self.callResults[name_base] = callResult
                for i in range(0, result_arity):
                    derived_name = gen_name(name_base+"_")
                    call_var = BoxedZ3IntVar(derived_name)
                    self.var_dependency[derived_name] = additional_dependency.union(callResult.args)
                    self.callResults[derived_name] = callResult
                    call_vars += (call_var,)

                return call_vars

            # Must be a function on primitives
            op_name = node.func.id
            def getTermAndFoldLevel(x):
                visited = self.visit(x)
                return visited[0], visited[3]
            eval_args = map(getTermAndFoldLevel, node.args)
            maxFoldLevel = max([subtuple[1] for subtuple in eval_args])
            flattened_args = tuple([item for subtuple in eval_args for item in subtuple[0]])
            result = substituteInFuncDec(Globals.funcs[op_name], flattened_args, self.formulas, self.var_defs, self.var_dependency)
            result = makeTuple(result)

            callResult = CallResult(op_name, flattened_args)
            result_arity = len(result)
            call_vars = create_call_vars(callResult, result_arity,{normalizeTuple(result)})

            return call_vars, len(result), {}, maxFoldLevel

        op_name = node.func.attr
        first_rdd, first_rdd_arity, first_rdd_vars, first_rdd_fold_level = self.visit(node.func.value)

        if op_name == "map":
            # get the args - should be 1 - a udf
            udf = node.args[0] # Should be Name node for UDF
            udf_arg, udf_arg_arity = first_rdd, first_rdd_arity

            result = substituteInFuncDec(Globals.funcs[udf.id], udf_arg, self.formulas, self.var_defs, self.var_dependency)

            result = makeTuple(result)

            debug("Map operation: %s", result)
            # TODO: result may have an arity > 1. This should be noted when reading from env.
            return result, len(result), first_rdd_vars, first_rdd_fold_level
            # solver.add()

        if op_name == "filter":
            # get the args - should be 1 - a udf
            udf = node.args[0] # Should be Name node for UDF
            udf_arg, udf_arg_arity = makeTuple(first_rdd), first_rdd_arity

            result = substituteInFuncDec(Globals.funcs[udf.id], udf_arg, self.formulas, self.var_defs, self.var_dependency) # Result is a boolean variable

            out_vars = ()
            then = True
            otherwise = True
            for i in range(0, udf_arg_arity):
                base_name = gen_name("t")
                if isinstance(udf_arg[i], tuple):
                    sub_out_vars = ()
                    for j in range(0, len(udf_arg[i])):
                        if isinstance(udf_arg[i][j], tuple):
                            sub_sub_out_vars = ()
                            for k in range(0, len(udf_arg[i][j])):
                                if isinstance(udf_arg[i][j][k], tuple):
                                    sub_sub_sub_out_vars = ()
                                    for l in range(0, len(udf_arg[i][j][k])):
                                        out_var = BoxedZ3IntVar(gen_name(base_name + "_"))
                                        self.var_dependency[out_var.name] = normalizeTuple(udf_arg[i][j][k][l])
                                        sub_sub_sub_out_vars += (out_var,)
                                        then = And(then, out_var == normalizeTuple(udf_arg[i][j][k][l]))
                                        otherwise = And(otherwise, out_var == Bot())

                                    sub_sub_out_vars += (sub_sub_sub_out_vars,)
                                else:
                                    out_var = BoxedZ3IntVar(gen_name(base_name + "_"))
                                    self.var_dependency[out_var.name] = normalizeTuple(udf_arg[i][j][k])
                                    sub_sub_out_vars += (out_var,)
                                    then = And(then, out_var == normalizeTuple(udf_arg[i][j][k]))
                                    otherwise = And(otherwise, out_var == Bot())
                            sub_out_vars += (sub_sub_out_vars,)
                        else:
                            out_var = BoxedZ3IntVar(gen_name(base_name+"_"))
                            self.var_dependency[out_var.name] = normalizeTuple(udf_arg[i][j])
                            sub_out_vars += (out_var,)
                            then = And(then, out_var == normalizeTuple(udf_arg[i][j]))
                            otherwise = And(otherwise, out_var == Bot())
                    out_vars += (sub_out_vars,)
                else:
                    out_var = BoxedZ3IntVar(base_name)
                    self.var_dependency[out_var.name] = normalizeTuple(udf_arg[i])
                    if isinstance(udf_arg[i], BoxedZ3Int) and udf_arg[i].name in self.foldResults:
                        self.foldResults[out_var.name] = self.foldResults[udf_arg[i].name]
                    if isinstance(udf_arg[i], BoxedZ3Int) and udf_arg[i].name in self.callResults:
                        self.callResults[out_var.name] = self.callResults[udf_arg[i].name]
                    out_vars += (out_var,)
                    then = And(then, out_var == normalizeTuple(udf_arg[i]))
                    otherwise = And(otherwise, out_var == Bot())

            ite = If(result == True, then, otherwise)
            debug("Filter operation formula: %s", ite)

            self.formulas.add(ite)
            for out_var in out_vars:
                if isinstance(out_var, tuple):
                    for sub_out_var in out_var:
                        if isinstance(sub_out_var, tuple):
                            for sub_sub_out_var in sub_out_var:
                                if isinstance(sub_sub_out_var, tuple):
                                    for sub_sub_sub_out_var in sub_sub_out_var:
                                        self.var_defs[normalizeTuple(sub_sub_sub_out_var).name] = ite
                                else:
                                    self.var_defs[normalizeTuple(sub_sub_out_var).name] = ite
                        else:
                            self.var_defs[normalizeTuple(sub_out_var).name] = ite
                else:
                    self.var_defs[normalizeTuple(out_var).name] = ite
            return out_vars, udf_arg_arity, first_rdd_vars, first_rdd_fold_level

        if op_name == "cartesian":
            # get the args - should be 1 - an rdd
            other_rdd = node.args[0]

            first_rdd_term, first_term_arity, first_term_vars = makeTuple(first_rdd), first_rdd_arity, first_rdd_vars
            other_rdd_term, other_term_arity, other_term_vars, other_term_fold_level = self.visit(other_rdd)
            other_rdd_term = makeTuple(other_rdd_term)

            # if any of the elements is bot, need to bot the whole resulting term. So need to allocate new vars
            out_vars1 = ()
            for i in range(0, first_term_arity):
                if isinstance(first_rdd_term[i], tuple):
                    out_var = ()
                    for j in range(len(first_rdd_term[i])):
                        if isinstance(first_rdd_term[i][j], tuple):
                            sub_out_var = ()
                            for k in range(len(first_rdd_term[i][j])):
                                if isinstance(first_rdd_term[i][j][k], tuple):
                                    sub_sub_out_var = ()
                                    for l in range(len(first_rdd_term[i][j][k])):
                                        sub_sub_sub_out_var = BoxedZ3IntVar(gen_name("c"))
                                        self.var_dependency[sub_sub_sub_out_var.name] = first_rdd_term[i][j][k][l]
                                        sub_sub_out_var += (sub_sub_sub_out_var,)
                                else:
                                    sub_sub_out_var = BoxedZ3IntVar(gen_name("c"))
                                    self.var_dependency[sub_sub_out_var.name] = first_rdd_term[i][j][k]
                                    sub_out_var += (sub_sub_out_var,)
                        else:
                            sub_out_var = BoxedZ3IntVar(gen_name("c"))
                            self.var_dependency[sub_out_var.name] = first_rdd_term[i][j]
                        out_var += (sub_out_var,)
                else:
                    out_var = BoxedZ3IntVar(gen_name("c"))
                    self.var_dependency[out_var.name] = first_rdd_term[i]

                out_vars1 += (out_var, )

            out_vars2 = ()
            for i in range(0, other_term_arity):
                if isinstance(other_rdd_term[i], tuple):
                    out_var = ()
                    for j in range(len(other_rdd_term[i])):
                        if isinstance(other_rdd_term[i][j], tuple):
                            sub_out_var = ()
                            for k in range(len(other_rdd_term[i][j])):
                                sub_sub_out_var = BoxedZ3IntVar(gen_name("c"))
                                self.var_dependency[sub_sub_out_var.name] = other_rdd_term[i][j][k]
                                sub_out_var += (sub_sub_out_var,)
                        else:
                            sub_out_var = BoxedZ3IntVar(gen_name("c'"))
                            self.var_dependency[sub_out_var.name] = other_rdd_term[i][j]
                        out_var += (sub_out_var,)
                else:
                    out_var = BoxedZ3IntVar(gen_name("c'"))
                    self.var_dependency[out_var.name] = other_rdd_term[i]

                out_vars2 += (out_var, )

            # Calculate the condition if there are any bots in the cartesian product
            isAnyBot = False
            for t in first_rdd_term + other_rdd_term:
                if isinstance(t, tuple):
                    for sub_t in t:
                        if isinstance(sub_t, tuple):
                            for sub_sub_t in sub_t:
                                if isinstance(sub_sub_t, tuple):
                                    for sub_sub_sub_t in sub_sub_t:
                                        isAnyBot = Or(isAnyBot, Bot() == normalizeTuple(sub_sub_sub_t))
                                else:
                                    isAnyBot = Or(isAnyBot, Bot() == normalizeTuple(sub_sub_t))
                        else:
                            isAnyBot = Or(isAnyBot, Bot() == normalizeTuple(sub_t))
                else:
                    isAnyBot = Or(isAnyBot, Bot() == t)


            debug("Is any of the terms a bottom in %s + %s ? %s", first_rdd_term, other_rdd_term, isAnyBot)

            # Now we set the out_vars properly by adding the condition that if any of the participating elements in the cartesian is bot, then all are bot
            formulaString = ""
            for (orig_t, out_t) in list(zip(first_rdd_term, out_vars1)) + list(zip(other_rdd_term, out_vars2)):
                if isinstance(orig_t, tuple):
                    for sub_orig, sub_out in zip(orig_t,out_t):
                        if isinstance(sub_orig, tuple):
                            for sub_sub_orig,sub_sub_out in zip(sub_orig,sub_out):
                                formula = If(isAnyBot, normalizeTuple(sub_sub_out) == Bot(), normalizeTuple(sub_sub_out) == normalizeTuple(sub_sub_orig))
                                self.var_defs[sub_sub_out.name] = formula

                                formulaString = formulaString + " AND " + str(formula)
                                self.formulas.add(formula)
                        else:
                            formula = If(isAnyBot, normalizeTuple(sub_out) == Bot(), normalizeTuple(sub_out) == normalizeTuple(sub_orig))
                            self.var_defs[sub_out.name] = formula

                            formulaString = formulaString + " AND " + str(formula)
                            self.formulas.add(formula)
                else:
                    formula = If(isAnyBot, out_t == Bot(), out_t == orig_t)
                    self.var_defs[out_t.name] = formula

                    formulaString = formulaString + " AND " + str(formula)
                    self.formulas.add(formula)


            result = (out_vars1, out_vars2)

            debug("Cartesian operation: %s -> %s", formulaString, result)
            # 2 was originally first_term_arity + other_term_arity,
            return result, \
                   2, \
                   first_term_vars.union(other_term_vars), max(first_rdd_fold_level, other_term_fold_level) # This max has no meaning really...


        def create_folded_vars(foldResult, result_arity):
            fold_vars = ()
            name_base = gen_name("f")
            self.foldResults[name_base] = foldResult
            for i in range(0, result_arity):
                fold_var = BoxedZ3IntVarNonBot(gen_name(name_base+"_"))
                self.var_dependency[fold_var.name] = foldResult.vars
                self.foldResults[fold_var.name] = foldResult
                fold_vars += (fold_var, )

            return fold_vars

        if op_name == "fold":
            # get the args - should be 2 - an init value, and a udf
            init_value = node.args[0]
            udf = node.args[1]

            rdd_term, rdd_term_arity = first_rdd, first_rdd_arity

            result = FoldResult(rdd_term, init_value, udf, first_rdd_fold_level)
            result.set_vars(first_rdd_vars)

            result_arity = 1 #TODO: get_result_arity(result)

            # Assign tmp variable(s) for the fold result
            fold_vars = create_folded_vars(result, result_arity)

            debug("Fold operation returns fold vars %s with Fold object %s", fold_vars, result)
            # Return a tuple of variables representing the folded type result,
            # so it could be given as input to functions
            return fold_vars, result_arity, {}, first_rdd_fold_level+1

        if op_name == "foldByKey":
            # get the args - should be 2 - an init value, and a udf
            init_value = node.args[0]
            udf = node.args[1]
            rdd_term, rdd_term_arity = first_rdd, first_rdd_arity # it must be a tuple!

            foldResult = FoldResult(rdd_term[1:], init_value, udf, first_rdd_fold_level)
            foldResult.set_key_vars(self.find_rep_vars_for_expr(rdd_term[0]))
            foldResult.set_vars(first_rdd_vars)

            result_arity = 1 # TODO: get_result_arity(result)
            fold_vars = create_folded_vars(foldResult, result_arity)

            debug("FoldByKey operation returns fold vars %s with Fold object %s", fold_vars, foldResult)

            key_var = BoxedZ3IntVar(gen_name("k"))
            self.var_dependency[key_var.name] = rdd_term[0]
            # TODO: Set key_var to be unique, with rdd_term[0]'s value
            # TODO: Note key_var cannot be a tuple
            result = (rdd_term[0], normalizeTuple(fold_vars))

            return result, 1 + 1, {key_var}, first_rdd_fold_level+1 # 1 for key + 1 for value because even if folded
            # value is a tuple, we address it as a single value and UDFs for
            #  map/filter will have to be smart enough to know it

        return None, None

    # Needs to return a set
    def find_rep_vars_for_expr(self, e):
        if not isinstance(e, BoxedZ3Int):
            return {e}

        if e.name[0] == "x":
            return {e}

        loopOn = e
        while True:
            candidate = self.var_dependency[loopOn.name]

            if not isinstance(candidate, BoxedZ3Int) or candidate.name[0] == "x":
                if isinstance(candidate, set):
                    return candidate
                return {candidate}

            loopOn = candidate
