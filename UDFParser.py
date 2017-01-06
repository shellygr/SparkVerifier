import ast
import inspect
import operator
from _ast import AST
from z3 import If, And, Or, Not, Function, IntSort, BoolSort, Bool

import Globals
from RDDTools import gen_name
from SolverTools import normalizeTuple, makeTuple
from WrapperClass import _to_BoxedZ3Int, BoxedZ3Int, BoxedZ3IntVar, bot
from tools import debug


def getSource(f):
    return inspect.getsource(f)


class UDFConverter(ast.NodeVisitor):
    def __init__(self, term, solver):
        self.term = term
        self.solver = solver
        self.env = {}

    def visit_FunctionDef(self, node):

        for i in range(0, len(node.args.args)): # each argument should be mapped to the concrete argument
            arg = node.args.args[i]

            if isinstance(arg, ast.Tuple) and i == 0: # This is a function on a record-type rdd, looping on the tuple's elements:
                for j in range(0, len(arg.elts)):
                    if isinstance(self.term[j], ast.Num):
                        self.env[arg.elts[j].id] = self.visit(self.term[j])
                    else:
                        self.env[arg.elts[j].id] = self.term[j]
            else:
                # Each arg must be a name node
                if isinstance(self.term[i], ast.Num):
                    self.env[arg.id] = self.visit(self.term[i])
                else:
                    self.env[arg.id] = self.term[i]

        for line in node.body: # TODO: Support more than 1 line. Currently supports only a single line which must be a return
            result = self.visit(line) # only support Return, If and operations

        return result

    def visit_Return(self, node):
        # Return must be non-void
        ret = self.visit(node.value)
        return ret

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
        otherwise = self.visit(node.orelse[0]) if len(node.orelse) > 0 else None
        debug("Test = %s, Then = %s, Otherwise = %s. Type of then is %s", test, then, otherwise, type(then))

        u = gen_name("u") # TODO: If tuple, need several vars. See existing code in FormulaCreatorRddWalker, filterCb

        if type(then) == bool:
            uVar = Bool(u)
        else:
            uVar = BoxedZ3IntVar(u)

        if with_else:
            formula = If(test == True, uVar == then, uVar == otherwise)
            self.solver.add(formula)
        else:
            formula = If(test == True, uVar == then, uVar == bot)
            self.solver.add(formula)

        return uVar


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
        left = _to_BoxedZ3Int(self.visit(node.left))
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


def substituteInFuncDec(f, term, solver):

    debug("Original code %s", ast.dump(f))

    term = makeTuple(term)
    converter = UDFConverter(term, solver)
    resultingTerm = converter.visit(f)

    debug("Substituted %s in UDF %s, got: %s, type = %s", term, f.name, resultingTerm, type(resultingTerm))

    return resultingTerm

