import ast
from z3 import If, And

import Globals
from FoldResult import FoldResult
from RDDTools import gen_name
from SolverTools import makeTuple, normalizeTuple
from UDFParser import substituteInFuncDec
from WrapperClass import bot, BoxedZ3IntVar, Bot
from tools import debug





class SparkConverter(ast.NodeVisitor):
    # Solver is Z3
    # Vars are all the vars we keep for the solver  -  TODO: Get rid of it!
    # Program name is the name of the function representing the spark program
    # rdds is a list of the concrete arguments from which we infer type information
    def __init__(self, solver, vars, programName, *rdds):
        self.solver = solver # Need to also append all env to the solver in the end, but still required: for example, for filter
        self.vars = vars
        self.programName = programName
        self.rdds = rdds
        self.env = {}
        self.ret = None
        self.ret_arity = 0

    def visit_FunctionDef(self, node):
        if node.name == self.programName:

            for i in range(0, len(node.args.args)): # each argument should be mapped to the concrete argument
                arg = node.args.args[i]

                # Each arg must be a name node
                self.env[arg.id] = self.rdds[i].vars, self.rdds[i].arity

            for line in node.body:
                self.visit(line) # only support Return, Assign and If (if is allowed only on primitives, so avoiding it - not really supported)

    def visit_Return(self, node):
        # Return must be non-void
        ret, ret_arity = self.visit(node.value)
        self.ret = ret
        self.ret_arity = ret_arity


    def visit_Assign(self, node):
        # Assume a single target
        target = node.targets[0]
        value = node.value

        parsed_value, parsed_value_arity = self.visit(value)

        # The target is a name
        self.env[target.id] = parsed_value, parsed_value_arity

    # Now we handle expressions - it's only spark operations, and function renames, so handling Name and Call
    # TODO: We may want to support usual operations for primitives symbolically
    def visit_Name(self, node):
        return self.env[node.id]

    def visit_Call(self, node):
        # Func is an attribute
        op_name = node.func.attr
        first_rdd, first_rdd_arity = self.visit(node.func.value)

        if op_name == "map":
            # get the args - should be 1 - a udf
            udf = node.args[0] # Should be Name node for UDF
            udf_arg, udf_arg_arity = first_rdd, first_rdd_arity

            result = substituteInFuncDec(Globals.funcs[udf.id], udf_arg, self.solver, self.vars)

            # TODO: result may have an arity > 1. This should be noted when reading from env.
            return result, udf_arg_arity
            # solver.add()

        if op_name == "filter":
            # get the args - should be 1 - a udf
            udf = node.args[0] # Should be Name node for UDF
            udf_arg, udf_arg_arity = makeTuple(first_rdd), first_rdd_arity

            result = substituteInFuncDec(Globals.funcs[udf.id], udf_arg, self.solver, self.vars) # Result is a boolean variable

            out_vars = ()
            then = True
            otherwise = True
            for i in range(0, udf_arg_arity):
                out_var = BoxedZ3IntVar(gen_name("t"))
                out_vars += (out_var,)
                then = And(then, out_var == normalizeTuple(udf_arg[i]))
                otherwise = And(otherwise, out_var == Bot())

            ite = If(result == True, then, otherwise)
            self.solver.add(ite)
            return out_vars, udf_arg_arity

        if op_name == "cartesian":
            # get the args - should be 1 - an rdd
            other_rdd = node.args[0]

            first_rdd_term, first_term_arity = makeTuple(first_rdd), first_rdd_arity
            other_rdd_term, other_term_arity = self.visit(other_rdd)
            other_rdd_term = makeTuple(other_rdd_term)
            
            # if any of the elements is bot, need to bot the whole resulting term. So need to allocate new vars
            out_vars1 = ()
            for i in range(0, first_term_arity):
                out_var = BoxedZ3IntVar(gen_name("c"))
                out_vars1 += (out_var, )

            out_vars2 = ()
            for i in range(0, other_term_arity):
                out_var = BoxedZ3IntVar(gen_name("c'"))
                out_vars2 += (out_var, )

            for t in first_rdd_term + other_rdd_term:
                for (orig_t, out_t) in list(zip(first_rdd_term, out_vars1)) + list(zip(other_rdd_term, out_vars2)):
                    self.solver.add(If(Bot() == t, out_t == Bot(), out_t == orig_t))

            result = (out_vars1, out_vars2)

            return result, first_term_arity + other_term_arity


        if op_name == "fold":
            # get the args - should be 2 - an init value, and a udf
            init_value = node.args[0]
            udf = node.args[1]

            rdd_term, rdd_term_arity = first_rdd, first_rdd_arity

            result = FoldResult(rdd_term, init_value, udf)

            # Assign tmp variable(s) for the fold result


            # TODO: Return a tuple of variables representing the folded type result, so it could be given as input to functions
            return result, 1

        if op_name == "foldByKey":
            # get the args - should be 2 - an init value, and a udf
            init_value = node.args[0]
            udf = node.args[1]
            rdd_term, rdd_term_arity = first_rdd, first_rdd_arity # it must be a tuple!

            result = (rdd_term[0], FoldResult(rdd_term[1:], init_value, udf))

            return result, 1 + 1

        return None, None