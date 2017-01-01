from z3 import *

from SparkZ3.Simulator.WrapperClass import BoxedZ3IntVar
#
# f = Function('f', IntSort(), IntSort(), IntSort())
# x, y = Ints('x y')
# print ForAll([x, y], f(x, y) == 0)
# print Exists(x, f(x, x) >= 0)
#
# a, b = Ints('a b')
# s = Solver()
# s.add(ForAll(x, f(x, x) == 0))
# s.check()
# print s.model()


#
# x = Int('x')
# y = Int('y')
# d = Distinct(x, y)
#
# s = Solver()
# s.add(d) # SAT without this one, UNSAT with
# s.add(x == y)
# print s
# print s.check()

x,y,b = Ints('x y b')
solver = Solver()

solver.add(Distinct(x, y))

def min(x,y):
	return If(x<y,x,y)

firstApp = min(100,x)
secondApp = min(firstApp, y)

firstApp2 = min(80,4*x/5)
secondApp2 = min(firstApp2, 4*y/5)

sVal1, sVal2 = Ints('sVal1 sVal2')
shrinked1 = min(100,b)
shrinked2 = min(80,4*b/5)

solver.add(sVal1==shrinked1)
solver.add(sVal2==shrinked2)

solver.add(Exists(x, Exists(y,
                         ForAll([b, sVal1, sVal2],
                                Or(secondApp!=sVal1, # Try replacing shrinked with sVal
                                        secondApp2!=sVal2)))))
                                # Or(secondApp!=shrinked1, # Try replacing shrinked with sVal
                                #         secondApp2!=shrinked2)))))

res = solver.check()
print solver.sexpr()
if res == sat:
    m = solver.model()
    print m
    print x, "=", m.evaluate(x, model_completion=True)
    print "min(100,x)", firstApp, "=", m.evaluate(firstApp, model_completion=True)
    print "min(m,y)", secondApp, "=", m.evaluate(secondApp, model_completion=True)
    print "min(100,4x)", firstApp2, "=", m.evaluate(firstApp2, model_completion=True)
    print "min(m',4y)", secondApp2, "=", m.evaluate(secondApp2, model_completion=True)
print res