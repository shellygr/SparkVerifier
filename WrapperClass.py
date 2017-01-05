from z3 import *

class BoxedZ3Int:
    def __init__(self, val, isBot, name):
        self.val = val
        self.isBot = isBot
        self.isUnique = False
        self.name = name

    def __add__(self, other):
        other = _to_BoxedZ3Int(other)
        return BoxedZ3Int(self.val + other.val, Or(self.isBot, other.isBot), self.name+"+"+other.name)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        other = _to_BoxedZ3Int(other)
        return BoxedZ3Int(self.val - other.val, Or(self.isBot, other.isBot), self.name+"-"+other.name)

    def __mul__(self, other):
        other = _to_BoxedZ3Int(other)
        return BoxedZ3Int(self.val*other.val, Or(self.isBot, other.isBot), self.name+"*"+other.name)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __mod__(self, other):
        other = _to_BoxedZ3Int(other)
        return BoxedZ3Int(self.val.__mod__(other.val), Or(self.isBot, other.isBot), self.name+"%"+other.name)

    def __div__(self, other):
        other = _to_BoxedZ3Int(other)
        return BoxedZ3Int(self.val.__div__(other.val), Or(self.isBot, other.isBot), self.name+"/"+other.name)

    def __divmod__(self, other):
        other = _to_BoxedZ3Int(other)
        return BoxedZ3Int(self.val.__divmod__(other.val), Or(self.isBot, other.isBot), self.name + " divmov " + other.name)

    def __neg__(self):
        return BoxedZ3Int(self.val.__neg__(), self.isBot, "-"+self.name)

    def __eq__(self, other):
        if other == None:
            return False
        other = _to_BoxedZ3Int(other)
        return If(other.isBot, self.isBot, If(self.isBot, other.isBot, self.val == other.val))
        # return Or(And(self.isBot, other.isBot), And(Not(self.isBot), Not(other.isBot), self.val == other.val))

    def __ne__(self, other):
        return Not(self.__eq__(other))

    def __lt__(self, other):
        other = _to_BoxedZ3Int(other)
        return And(Not(self.isBot), Not(other.isBot), self.val.__lt__(other.val))

    def __le__(self, other):
        other = _to_BoxedZ3Int(other)
        return And(Not(self.isBot), Not(other.isBot), self.val.__le__(other.val))

    def __gt__(self, other):
        other = _to_BoxedZ3Int(other)
        return And(Not(self.isBot), Not(other.isBot), self.val.__gt__(other.val))

    def __ge__(self, other):
        other = _to_BoxedZ3Int(other)
        return And(Not(self.isBot), Not(other.isBot), self.val.__ge__(other.val))

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __len__(self):
        return 1

    # dict key support
    def __hash__(self):
        return hash((self.name))

def BoxedZ3IntVarNonBot(name, solver):
    var = BoxedZ3IntVar(name)
    solver.add(var.isBot==False)
    return var

def BoxedZ3IntVar(name):
    return BoxedZ3Int(Int('%s.val' % name), Bool('%s.isBot' % name), name)

def BoxedZ3IntVal(v):
    return BoxedZ3Int(IntVal(v), BoolVal(False), str(v))

def Bot():
    return BoxedZ3Int(IntVal(0), BoolVal(True), "bot")

def _to_BoxedZ3Int(v):
    if isinstance(v, BoxedZ3Int):
        return v
    elif isinstance(v, ArithRef):
        return BoxedZ3Int(v, BoolVal(False), str(v))
    else:
        return BoxedZ3IntVal(v)

BoxedInt = Datatype("BoxedInt")
BoxedInt.declare('bot')
BoxedInt.declare('num', ('val', IntSort()))
BoxedInt = BoxedInt.create()
bot = BoxedInt.bot
num = BoxedInt.num
val = BoxedInt.val



def test():
    x0 = BoxedZ3IntVar("x0")
    x1 = BoxedZ3IntVar("x1")
    i0 = Int("i0")

    # print x0<x1
    # print If(x0<x1,i0,i0)

    sol = Solver()
    # sol.add(Implies(x0<x1,i0==i0))
    # sol.add(If(x0<x1, x0.val,x1.val)==i0)
    sol.add(If(x0<x1, x0==x1,x1!=x0))
    # sol.add(x0 < i0)
    # sol.add(And(x0 <= 2*x1, x0==Bot()))
    print sol
    print sol.check()
    print sol.model()

    x = Const('x', BoxedInt)
    L, R = Consts('L R', IntSort())
    print bot.sort()
    print val(x).sort()
    print num(val(x)*2).sort()
    formula = If(val(x) > 50, num(val(x)*2),bot) < num(R)

    z,y = Consts('z y', BoxedInt)
    formula = val(z)<val(y)
    # formula = If(val(x)>50, (val(x), val(x)), (val(x), val(x)))
    # sol.add(formula)
    # print sol
    # print sol.check()
    # print sol.model()
# test()