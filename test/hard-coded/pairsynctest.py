from z3 import *

from WrapperClass import BoxedZ3IntVar

x, y, z = Int("x"), Int("y"), Int("z")

fApp1 = BoxedZ3IntVar("fApp1")
fApp2 = BoxedZ3IntVar("fApp2")
sApp1 = BoxedZ3IntVar("sApp1")
sApp2 = BoxedZ3IntVar("sApp2")
shrinked1 = BoxedZ3IntVar("shrinked1")
shrinked2 = BoxedZ3IntVar("shrinked2")

solver = Solver()
solver.add(If(x%2 == 0, fApp1 == 1, fApp1 == 0))
solver.add(If(x%2 == 0, fApp2 == 1, fApp2 == 0))
solver.add(If(y%2 == 0, sApp1 == fApp1+1, sApp1 == fApp1))
solver.add(If(y%2 == 0, sApp2 == fApp2+1, sApp2 == fApp2))
solver.add(If(z%2 == 0, shrinked1 == 1, shrinked1 == 0))
solver.add(If(z%2 == 0, shrinked2 == 1, shrinked2 == 0))

solver.add(Exists(x, Exists(y, ForAll(z, Not(And(If(False,False,If(False,False,sApp1==shrinked1)), If(False,False,If(False,False,sApp2==shrinked2))))))))
#
# lhsIntermediate = BoxedZ3IntVar("lhsIntermediate")
# rhsIntermediate = BoxedZ3IntVar("rhsIntermediate")
# lNextElem = BoxedZ3IntVar("lNextElem")
# rNextElem = BoxedZ3IntVar("rNextElem")
#
# def f((x,y)):
#     return x+y
#
# solver.add(lNextElem==r2[1])
# solver.add(rNextElem==f(r2b[1]))
#
# solver.add(Not(Implies(lhsIntermediate==rhsIntermediate, f((lhsIntermediate,lNextElem))==f((rhsIntermediate,rNextElem)))))

res = solver.check()
print res
print solver.model()