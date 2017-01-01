import ast
import inspect
from z3 import Solver, sat, unsat

import Globals
from SolverTools import normalizeTuple
from SparkConverter import SparkConverter
from UDFParser import getSource
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

    def __init__(self):
        self.solver = Solver()
        self. vars = set()


    def createProgramEnv(self, f, name, *rdds):
        source = getSource(f)
        parsedSource = ast.parse(source)

        debug("Original code %s", ast.dump(parsedSource))

        converter = SparkConverter(self.solver, self.vars, name, *rdds)
        converter.visit(parsedSource)

        resultingTerm = converter.ret
        debug("Got Spark program term %s, type = %s", resultingTerm, type(resultingTerm))

        return converter

    def verifyEquivalence(self, p1, p2, *rdds):
        print("")
        #
        fillAllFuncs(p1)
        fillAllFuncs(p2)

        result1 = self.createProgramEnv(p1, p1.__name__, *rdds)
        result2 = self.createProgramEnv(p2, p2.__name__, *rdds)

        return self.verify(result1, result2)


    def verify(self, sc1, sc2):

        if sc1.ret_arity != sc2.ret_arity:
            return False

        ret1 = normalizeTuple(sc1.ret)
        ret2 = normalizeTuple(sc2.ret)


        if isinstance(ret1, tuple) and isinstance(ret2, tuple):
           if len(ret1) != len(ret2):
               return False

           are_equivalent = True
           for e1, e2 in zip(ret1, ret2):
                are_equivalent = self.verifyEquivalentElements(normalizeTuple(e1), normalizeTuple(e2))
                if are_equivalent == False:
                    return False

           return True

        if not isinstance(ret1, tuple) and not isinstance(ret2, tuple):
            return self.verifyEquivalentElements(ret1, ret2)


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
