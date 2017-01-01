


def min(A, x):
    if x<A:
        return x
    else:
        return A

def discount(x):
    if x>125:
        return x*4/5

    return x

def doublePair((x,y)):
    return (2*x, 2*y)

def doublePair2((x,y)):
    return (doubleUninterp(x), doubleUninterp(y))

def double(x):
    return 2*x


def uninterp(f):
    pass


def doubleUninterp(x):
    return 2*x


def doubleAndAdd1(x):
    return 2*x+1


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

def cartesianThenMap(rdd,rdd2):
    p = rdd.cartesian(rdd2).map(doublePair)
    return p

def cartesianThenMapUninterp(rdd,rdd2):
    p = rdd.cartesian(rdd2).map(doublePair2)
    return p

def mapUninterpThenCartesian(rdd,rdd2):
    p2 = rdd.map(doubleUninterp).cartesian(rdd2.map(doubleUninterp))
    return p2

def mapPartialUninterpThenCartesian(rdd,rdd2):
    p2 = rdd.map(double).cartesian(rdd2.map(doubleUninterp))
    return p2
