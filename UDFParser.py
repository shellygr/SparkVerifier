import ast
import inspect
import operator
from _ast import AST
from z3 import If, And, Or, Not, Function, IntSort, BoolSort, Bool, simplify

import Globals
from RDDTools import gen_name
from SolverTools import normalizeTuple, makeTuple
from WrapperClass import _to_BoxedZ3Int, BoxedZ3Int, BoxedZ3IntVar, bot, Bot, BoxedZ3IntVarNonBot
from tools import debug


def getSource(f):
    return inspect.getsource(f)


class UDFConverter(ast.NodeVisitor):
    def __init__(self, term, formulas, var_defs, var_deps, isFoldUdf = False):
        self.term = normalizeTuple(term)
        self.formulas = formulas
        self.var_defs = var_defs
        self.var_deps = var_deps
        self.env = {}
        self.isFoldUdf = isFoldUdf

    def fillArgWithTerm(self, arg, term):
        if isinstance(arg, ast.Tuple):
            term = makeTuple(term)
            for i in range(0, len(arg.elts)):
                if isinstance(arg.elts[i], ast.Tuple):
                    self.fillArgWithTerm(arg.elts[i], term[i])
                else:
                    if isinstance(term[i], ast.Num):
                        self.env[arg.elts[i].id] = self.visit(term[i])
                    else:
                        self.fillArgWithTerm(arg.elts[i], term[i])
        else:
            if isinstance(term, ast.Num):
                self.env[arg.id] = self.visit(term)
            else:
                self.env[arg.id] = term

    def fillEnvForNonFoldUdf(self, args):
        if len(args) != 1:
            raise Exception("Invalid non-fold UDF, must have a single argument")

        arg = args[0]
        self.fillArgWithTerm(arg, self.term)

    def fillEnvForFoldUdf(self, args):
        if len(args) != 2:
            raise Exception("Invalid fold UDF, must have one argument for the aggregated value, other for the RDD element")

        aggregated_value_arg = args[0]
        element_arg = args[1]

        aggregated_value_term = self.term[0]
        if isinstance(self.term[1][0], tuple):
            self.term = (self.term[0], normalizeTuple(self.term[1]))

        element_term = self.term[1]

        self.fillArgWithTerm(aggregated_value_arg, aggregated_value_term)
        self.fillArgWithTerm(element_arg, element_term)
        #
        # for i in range(0, len(node.args.args)):  # each argument should be mapped to the concrete argument
        #     arg = node.args.args[i]
        #
        #     if isinstance(arg,
        #                   ast.Tuple) and i == 0:  # This is a function on a record-type rdd, looping on the tuple's elements:
        #         for j in range(0, len(arg.elts)):
        #             if isinstance(arg.elts[j], ast.Tuple):
        #                 for k in range(0, len(arg.elts[j].elts)):
        #                     if isinstance(self.term[j], ast.Num):
        #                         self.env[arg.elts[j].elts[k].id] = self.visit(self.term[j][k])
        #                     else:
        #                         self.env[arg.elts[j].elts[k].id] = self.term[j][k]
        #             else:
        #                 if isinstance(self.term[j], ast.Num):
        #                     self.env[arg.elts[j].id] = self.visit(self.term[j])
        #                 else:
        #                     self.env[arg.elts[j].id] = self.term[j]
        #     else:
        #         # Each arg must be a name node
        #         if isinstance(self.term[i], ast.Num):
        #             self.env[arg.id] = self.visit(self.term[i])
        #         else:
        #             self.env[arg.id] = self.term[i]

    def visit_FunctionDef(self, node):

        if self.isFoldUdf:
            self.fillEnvForFoldUdf(node.args.args)
        else:
            self.fillEnvForNonFoldUdf(node.args.args)



        for line in node.body: # TODO: Support more than 1 line. Currently supports only a single line which must be a return
            result = self.visit(line) # only support Return, If and operations

        if self.isFoldUdf:
            result_var = BoxedZ3IntVarNonBot(gen_name("fU"))
            is_any_bot = False
            for i in range(0,len(self.term[1])):
                is_any_bot = Or(is_any_bot, Bot()==self.term[1][i])

            acc = self.term[0]
            if isinstance(acc, ast.Num):
                acc = self.visit(acc)

            foldUdfResultFormula = simplify(If(is_any_bot, result_var == acc, result_var == result))
            debug("For fold UDF the result formula is %s", foldUdfResultFormula)
            self.formulas.add(foldUdfResultFormula)
            self.var_defs[result_var.name] = foldUdfResultFormula

            return result_var

        return result

    def visit_Return(self, node):
        # Return must be non-void
        ret = self.visit(node.value)
        return ret

    def visit_Call(self, node):
        func_name = node.func.id
        func = Globals.funcs[func_name]
        # Backup environment
        backupEnv = {}
        for arg,idx in zip(func.args.args, range(0,len(func.args.args))):
            backupEnv[arg.id] = self.env[arg.id]
            self.env[arg.id] = self.visit(node.args[idx])

        for line in func.body:
            result = self.visit(line)

        # Restore environment
        for arg_name in backupEnv:
            self.env[arg_name] = backupEnv[arg_name]

        return result


    def visit_Name(self, node):
        if node.id == "True":
            return True

        if node.id == "False":
            return False

        return self.env[node.id]

    def visit_If(self, node):
        debug("If node = %s", ast.dump(node))

        test = self.visit(node.test)

        then = normalizeTuple(self.visit(node.body[0]))

        with_else = len(node.orelse) > 0
        if with_else:
            otherwise = self.visit(node.orelse[0]) if len(node.orelse) > 0 else None
        else:
            otherwise = map(lambda x: bot, then)

        debug("Test = %s, Then = %s, Otherwise = %s. Type of then is %s", test, then, otherwise, type(then))

        generated_names = ()
        u_vars_out = ()
        thenFormula = True
        otherwiseFormula = True
        for elem, elemOther in zip(makeTuple(then), makeTuple(otherwise)):
            if isinstance(elem, tuple):
                sub_u_vars_out = ()
                for sub_elem, sub_elemOther in zip(elem, elemOther):
                    u = gen_name("u")
                    generated_names += (u,)
                    self.var_deps[u] = sub_elem # TODO: need to return sub_elemOther too! But find_rep_vars_for_expr should return a set
                    if type(sub_elem) == bool:
                        u_var_out = Bool(u)
                    else:
                        u_var_out = BoxedZ3IntVar(u)

                    thenFormula = And(thenFormula, u_var_out == sub_elem)
                    otherwiseFormula = And(otherwiseFormula, u_var_out == sub_elemOther)

                    sub_u_vars_out += (u_var_out,)
                u_vars_out += (sub_u_vars_out,)
            else:
                u = gen_name("u")
                generated_names += (u,)
                self.var_deps[u] = elem  # TODO: need to return elemOther too! But find_rep_vars_for_expr should return a set
                if type(elem) == bool:
                    u_var_out = Bool(u)
                else:
                    u_var_out = BoxedZ3IntVar(u)

                thenFormula = And(thenFormula, u_var_out == elem)
                otherwiseFormula = And(otherwiseFormula, u_var_out == elemOther)

                u_vars_out += (u_var_out,)

        # u = gen_name("u") # TODO: If tuple, need several vars. See existing code in FormulaCreatorRddWalker, filterCb
        #
        # if type(then) == bool:
        #     uVar = Bool(u)
        # else:
        #     uVar = BoxedZ3IntVar(u)

        debug("Then formula = %s, Else formula = %s", thenFormula, otherwiseFormula)
        if with_else:
            # formula = If(test == True, And(uVar.val == then, uVar.isBot == False), And(uVar.val == otherwise, uVar.isBot == False))
            # formula = simplify(If(test == True, uVar == then, uVar == otherwise))
            formula = simplify(If(test == True, thenFormula, otherwiseFormula))
            debug("Formula added for if: %s", formula)
            self.formulas.add(formula)
            # print simplify(formula)
            for name in generated_names:
                self.var_defs[name] = formula
        else:
            # formula = If(test == True, And(uVar.val == then, uVar.isBot == False), uVar.isBot == True)
            # formula = simplify(If(test == True, uVar == then, uVar == bot))
            formula = simplify(If(test == True, thenFormula, otherwiseFormula))
            self.formulas.add(formula)
            for name in generated_names:
                self.var_defs[name] = formula

        return normalizeTuple(u_vars_out)


    def visit_Lt(self, node):
        return operator.lt

    def visit_LtE(self, node):
        return operator.lte

    def visit_Gt(self, node):
        return operator.gt

    def visit_GtE(self, node):
        return operator.ge

    def visit_Eq(self, node):
        return operator.eq

    def visit_NotEq(self,node):
        return operator.ne

    def visit_Compare(self, node):
        op = self.visit(node.ops[0]) # Assumes single compare
        left = self.visit(node.left)
        left = normalizeTuple(left)
        left = _to_BoxedZ3Int(left)
        comparators = self.visit(node.comparators[0])
        return op(left,comparators)

    def visit_Mult(self, node):
        return operator.mul

    def visit_Add(self, node):
        return operator.add

    def visit_Sub(self, node):
        return operator.sub

    def visit_Div(self, node):
        return operator.div

    def visit_Mod(self, node):
        return operator.mod

    def visit_Num(self, node):
        return node.n

    def visit_Tuple(self, node):
        visitTuple = tuple(map(self.visit, node.elts))
        return visitTuple

    def visit_BinOp(self, node):
        op = self.visit(node.op)
        left = _to_BoxedZ3Int(normalizeTuple(self.visit(node.left)))
        right = normalizeTuple(self.visit(node.right))
        return op(left, right)

    def visit_And(self, node):
        return And

    def visit_Or(self,node):
        return Or

    def visit_BoolOp(self, node): # assumes binary
        op = self.visit(node.op)
        arg1 = self.visit(node.values[0])
        arg2 = self.visit(node.values[1])
        return op(arg1, arg2)

    def visit_Not(self, node):
        return Not

    def visit_USub(self, node):
        return operator.neg

    def visit_UnaryOp(self, node):
        op = self.visit(node.op)
        return op(self.visit(node.operand))


def substituteInFuncDec(f, term, formulas, var_defs = {}, var_deps = {}, isFoldUdf = False):

    debug("Original code %s", ast.dump(f))

    term = makeTuple(term)
    converter = UDFConverter(term, formulas, var_defs, var_deps, isFoldUdf)
    resultingTerm = converter.visit(f)

    debug("Substituted %s in UDF %s (a fold UDF: %s), got: %s, type = %s", term, f.name, isFoldUdf, resultingTerm, type(resultingTerm))

    return resultingTerm

