import ast
import inspect
from z3 import Solver

import Globals
from UDFParser import getSource
from tools import debug

class FuncDbBuilder(ast.NodeVisitor):
    def __init__(self, verifier):
        self.verifier = verifier

    def visit_FunctionDef(self, node):
        debug("Adding func name %s with above src", node.name)
        self.verifier.funcs[node.name] = node

class Verifier:

    # Get all auxilary functions names from the file where the example Spark programs tested for equivalence are located
    def fillAllFuncs(self, p):
        module = inspect.getmodule(p)
        debug("Module of function %s is %s", p, module)
        src = getSource(module)
        parsedSrc = ast.parse(src)
        FuncDbBuilder(self).visit(parsedSrc)


    def verifyEquivalence(self, p1, p2, *rdds):
        print("")

        self.fillAllFuncs(p1)
        self.fillAllFuncs(p2)

        solver = Solver()
        vars = set()