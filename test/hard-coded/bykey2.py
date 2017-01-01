from z3 import *

from SparkZ3.Simulator.WrapperClass import BoxedZ3IntVar


A = Int("A")
Ap = Int("Ap")

p = Int("p")
c = Int("c")

d = Int("d")
B = Int("B")
Bp = Int("Bp")


solver = Solver()

cond = A*(p - c) == Ap
result = (A+1)*(p - c) == Ap + (p - c)

cond2 = And(cond, If(d == 18112016, B == (A+1)*(p-c), B == A*(p-c)), If(d == 18112016, Bp == Ap + (p-c), Bp == Ap))
result2 = B==Bp

solver.add(And(cond2, Not(result2)))


res = solver.check()
print res
if res == sat:
    print solver.model()
print solver