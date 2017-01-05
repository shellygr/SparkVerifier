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

    def createProgramEnv(self, f, name, *rdds):
        source = getSource(f)
        parsedSource = ast.parse(source)

        debug("Original code %s", ast.dump(parsedSource))

        converter = SparkConverter(self.solver, name, *rdds)
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


    def verifyEquivaentFolds(self, e1, e2, programCtx1, programCtx2):
        foldAndCallCtx1 = {}
        foldAndCallCtx1.update(programCtx1.foldResults)
        foldAndCallCtx1.update(programCtx1.callResults)

        foldAndCallCtx2 = {}
        foldAndCallCtx2.update(programCtx2.foldResults)
        foldAndCallCtx2.update(programCtx2.callResults)

        foldRes1 = foldAndCallCtx1[e1.name] # TODO what if it is a call on a boxedz3int?
        foldRes2 = foldAndCallCtx2[e2.name]

        print "Got fold results: ", foldRes1, foldRes2




        return False


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
