


def min(A, x):
    if x<A:
        return x
    else:
        return A

def discount(x):
    if x>125:
        return x*4/5

    return x

def double(x):
    return 2*x

def lessThan50(x):
    if x<50:
        return True
    else:
        return False

def lessThan100(x):
    if x<100:
        return True
    else:
        return False

def lessThan200(x):
    if x<200:
        return True
    else:
        return False

def mapThenFilter(rdd):
    p1 = rdd.map(double).filter(lessThan100)
    return p1

def filterThenMap(rdd):
    p2 = rdd.filter(lessThan50).map(double)
    return p2

def filterThenMapWrong(rdd):
    p2 = rdd.filter(lessThan100).map(double)
    return p2


def h(((A,B), x)):
    if x >= 0:
        return (A+x, B)
    else:
        return (A, B-x)

# First must be an RDD
def apply(f, args):
    rddObj = args[0]
    return rddObj.apply(f)

def p1((a,b)):
    return a

def p2((a,b)):
    return b

def func1(rdd):
    res = rdd.fold((0,0), h)
    return (apply(p1, (res,)), apply(p2, (res,)))

def atLeast0(x):
    return x >= 0

def lessThan0(x):
    return x < 0

def inverse(x):
    return -x

def sumMy((A,x)):
    return A+x



def func2(rdd):
    rp = rdd.filter(atLeast0)
    rn = rdd.filter(lessThan0).map(inverse)
    return (rp.fold(0, sumMy), apply(inverse, (rn.fold(0,sumMy),)))

def g1(rdd):
    res = rdd.fold((0,0), h)
    return apply(p1, (res,))

def g2(rdd):
    rp = rdd.filter(atLeast0)
    return rp.fold(0,sumMy)