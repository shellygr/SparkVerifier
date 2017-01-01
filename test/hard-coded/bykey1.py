from z3 import *

from SparkZ3.Simulator.WrapperClass import BoxedZ3IntVar

r = (Int("r1"), Int("r2"))

solver = Solver()

r2 = (r[0], r[0]+r[1])
r2b = (r[0], (r[0],r[1]))

solver.add(r[0]==r[0])

lhsIntermediate = BoxedZ3IntVar("lhsIntermediate")
rhsIntermediate = BoxedZ3IntVar("rhsIntermediate")
lNextElem = BoxedZ3IntVar("lNextElem")
rNextElem = BoxedZ3IntVar("rNextElem")

def f((x,y)):
    return x+y

solver.add(lNextElem==r2[1])
solver.add(rNextElem==f(r2b[1]))

solver.add(Not(Implies(lhsIntermediate==rhsIntermediate, f((lhsIntermediate,lNextElem))==f((rhsIntermediate,rNextElem)))))

res = solver.check()
print res