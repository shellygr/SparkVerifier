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

def getName(f):
    return getSource(f).split(" ")[1].split("(")[0]



class Z3BaseConverter(ast.NodeVisitor):

    def generic_visit(self, node):
        # Overrided to return the visit value of the first child node
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, AST):
                        return self.visit(item)
            elif isinstance(value, AST):
                return self.visit(value)

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
        # print left, left.__class__.__name__, comparators, comparators.__class__.__name__
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
        debug("VisitTuple = %s", visitTuple)
        return visitTuple

    def visit_BinOp(self, node):
        op = self.visit(node.op)
        left = _to_BoxedZ3Int(self.visit(node.left))
        right = self.visit(node.right)
        debug("Left = %s, right = %s, op = %s", left, right, op)
        debug("Returning %s", op(left,right))
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


# Convert AST tuple to names
def astTupleToSimpleNameTuple(tup):
    # Helping function: name arguments go to their id, otherwise we convert the tuple of arguments
    def convertNode(node):
        if isinstance(node, ast.Name):
            return node.id
        else:
            return astTupleToSimpleNameTuple(node)

    # base
    if isinstance(tup, ast.Name):
        return (tup.id,)

    # Call to recursive convertNode (which recursively calls astTupleToSimpleNameTuple) on every element of the tuple
    simpleTup = tuple([convertNode(elm) for elm in tup.elts])
    debug("Converted AST tuple: %s --> %s", ast.dump(tup), simpleTup)

    return simpleTup

def isUninterpFunc(funcName):
    return "Uninterp" in funcName

class Z3Converter(Z3BaseConverter):
    def __init__(self, term, solver, vars):
        debug("Argument is %s, type %s", term, term.__class__.__name__)
        self.solver = solver
        self.vars = vars
        self.argument = term
        self.substituted = None # Will be filled upon seeing a function def

    def handleUninterpretedFunctionDef(self, node):
        u = gen_name("u") # TODO: If tuple, need several vars. See existing code in FormulaCreatorRddWalker
        if "BoolUninterp" in node.name:
            debug("%s = Bool('%s')", u, u)
            self.vars[u] = Bool(u)
        else:
            self.vars[u] = BoxedZ3IntVar(u)

        if node.name not in Globals.uninterpFuncs:
            auxUninterp = gen_name("auxUninterp")
            Globals.uninterpFuncs[node.name] = auxUninterp
            if "BoolUninterp" in node.name:
                debug("%s = Function('%s', IntSort(), BoolSort())", auxUninterp, auxUninterp) # TODO: Support different types - easy to do multiple args, but what about multiple outs
                self.vars[auxUninterp] = Function(auxUninterp, IntSort(), BoolSort())
            else:
                debug("%s = Function('%s', IntSort(), IntSort())", auxUninterp, auxUninterp) # TODO: Support different types - easy to do multiple args, but what about multiple outs
                self.vars[auxUninterp] = Function(auxUninterp, IntSort(), IntSort())
        else:
            auxUninterp = Globals.uninterpFuncs[node.name]
            debug("Fetching uninterpreted function %s, called %s", node.name, auxUninterp)

        debug("%s, %s", self.argument, self.argument.__class__.__name__)
        if isinstance(self.argument, BoxedZ3Int):
            substituteTerm = self.argument.val
        else:
            substituteTerm = self.argument

        formula = self.vars[u] == self.vars[auxUninterp](substituteTerm)
        debug("Adding formula for applying an uninterpreted function %s",formula)
        self.solver.add(formula)

        return self.vars[u]

    def visit_FunctionDef(self, node):
        debug("Function def = %s", ast.dump(node))
        callerSubstituted = None
        if self.substituted != None:
            callerSubstituted = self.substituted # to be restored

        self.substituted = normalizeTuple(astTupleToSimpleNameTuple(node.args.args[0]))
        debug("Going to substitute: %s with %s", self.substituted, self.argument)
        if isUninterpFunc(node.name):
            uninterpretedTerm = self.handleUninterpretedFunctionDef(node)
            if callerSubstituted != None:
                self.substituted = callerSubstituted
            return uninterpretedTerm

        term = self.visit(node.body[0])

        if callerSubstituted != None:
            self.substituted = callerSubstituted
        return term

    def visit_Call(self,node): # TODO: Build from sources of all FunctionDef-s instead of rewriting everything with apply
        calledF = Globals.funcs[node.func.id]
        args = self.visit(node.args[0])
        debug("Args for callee = %s, class %s", args, args.__class__.__name__)

        # Gen a variable for the args
        u = gen_name("u") # TODO: If tuple, need several vars. See existing code in FormulaCreatorRddWalker
        self.vars[u] = BoxedZ3IntVar(u)
        Globals.newNames.append(self.vars[u].val)

        formula = self.vars[u] == args
        debug("Caller formula: %s", formula)
        self.solver.add(formula)

        callerArgument = self.argument # to be restored
        self.argument = self.vars[u] # TODO: Will not be good if there are several non nested calls
        calleeResult = self.visit(calledF)
        debug("Callee = %s, Callee body = %s, Callee result = %s, type %s", node.func.id, calledF, calleeResult, calleeResult.__class__.__name__)

        self.argument = callerArgument
        return calleeResult

    # Substituted and argument (which substitutes) have the same tuple structure. We know there are no duplicate names.
    def findSubstitution(self, node, substituted, argument):
        # Base case: if done with the current tuple, need to continue to the next element in the containing tuple.
        if len(substituted) == 0:
            return None

        # Should support nested tuples.
        if isinstance(substituted[0], tuple):
            visitResult = self.findSubstitution(node, substituted[0], argument[0])
            if visitResult is not None:
                return visitResult
            else:
                return self.findSubstitution(node, substituted[1:], argument[1:])
        else:
            if node.id == substituted[0]:
                debug("match for name %s", node.id)
                return argument[0]

        # Continue with next element in tuple
        return self.findSubstitution(node, substituted[1:], argument[1:])

    def visit_Name(self, node):
        debug("node is %s, substituted is %s, arguments are %s", node.id, self.substituted, self.argument)

        if node.id == "True":
            return True

        if node.id == "False":
            return False

        if isinstance(self.substituted, tuple):
            retVal = self.findSubstitution(node, self.substituted, self.argument)
            debug("replacing %s with %s", node.id, retVal)
            return retVal

        if node.id == self.substituted:
            debug("replacing %s with %s", node.id, self.argument)
            return normalizeTuple(self.argument)

    def visit_If(self, node): # TODO: Update the solver with the if variable
        debug("If node = %s", ast.dump(node))

        test = self.visit(node.test)
        # then = makeTuple(self.visit(node.body[0]))
        then = self.visit(node.body[0])
        # otherwise = makeTuple(self.visit(node.orelse[0]) if len(node.orelse) > 0 else None)
        otherwise = self.visit(node.orelse[0]) if len(node.orelse) > 0 else None
        debug("Test = %s, Then = %s, Otherwise = %s", test, then, otherwise)

        u = gen_name("u") # TODO: If tuple, need several vars. See existing code in FormulaCreatorRddWalker, filterCb
        # self.vars[u] = tuple([BoxedZ3IntVar("%s_%d"%(u,i)) for i in range(1,len(then)+1)])
        self.vars[u] = BoxedZ3IntVar(u)
        Globals.newNames.append(self.vars[u].val)
        if otherwise != None:
            formula = If(test == True, self.vars[u] == then, self.vars[u] == otherwise)
            # formula = If(test == True, And([subU==subThen for subU,subThen in zip(self.vars[u],then)]), And([subU==subElse for subU,subElse in zip(self.vars[u],otherwise)]))
            debug("ADDING TO SOLVER: %s", formula)
            self.solver.add(formula)
        else:
            formula = If(test == True, self.vars[u] == then, self.vars[u] == bot)
            # formula = If(test == True, And([subU==subThen for subU,subThen in zip(self.vars[u],then)]), And([subU==bot for subU in self.vars[u]])) # TODO: Tuple support
            debug("If formula: %s", formula)
            self.solver.add(formula)

        return self.vars[u]


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
                    self.env[arg.elts[j].id] = self.term[j]
            else:
                # Each arg must be a name node
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
        # then = makeTuple(self.visit(node.body[0]))
        then = self.visit(node.body[0])
        # otherwise = makeTuple(self.visit(node.orelse[0]) if len(node.orelse) > 0 else None)
        otherwise = self.visit(node.orelse[0]) if len(node.orelse) > 0 else None
        debug("Test = %s, Then = %s, Otherwise = %s. Type of then is %s", test, then, otherwise, type(then))

        u = gen_name("u") # TODO: If tuple, need several vars. See existing code in FormulaCreatorRddWalker, filterCb
        # self.vars[u] = tuple([BoxedZ3IntVar("%s_%d"%(u,i)) for i in range(1,len(then)+1)])
        if type(then) == bool:
            uVar = Bool(u)
        else:
            uVar = BoxedZ3IntVar(u)

        # Globals.newNames.append(uVar.val)
        if otherwise != None:
            formula = If(test == True, uVar == then, uVar == otherwise)
            # formula = If(test == True, And([subU==subThen for subU,subThen in zip(self.vars[u],then)]), And([subU==subElse for subU,subElse in zip(self.vars[u],otherwise)]))
            debug("ADDING TO SOLVER: %s", formula)
            self.solver.add(formula)
        else:
            formula = If(test == True, uVar == then, uVar == bot)
            # formula = If(test == True, And([subU==subThen for subU,subThen in zip(self.vars[u],then)]), And([subU==bot for subU in self.vars[u]])) # TODO: Tuple support
            debug("If formula: %s", formula)
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
        # print left, left.__class__.__name__, comparators, comparators.__class__.__name__
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
        debug("VisitTuple = %s", visitTuple)
        return visitTuple

    def visit_BinOp(self, node):
        op = self.visit(node.op)
        left = _to_BoxedZ3Int(self.visit(node.left))
        right = normalizeTuple(self.visit(node.right))
        debug("Left = %s, right = %s, op = %s", left, right, op)
        debug("Returning %s(%s,%s) = %s", op, left,right, op(left,right))
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
    debug("Term: %s of type %s", term, type(term))
    converter = UDFConverter(term, solver)
    resultingTerm = converter.visit(f)

    debug("Substituted in UDF %s, type = %s", resultingTerm, type(resultingTerm))

    return resultingTerm

