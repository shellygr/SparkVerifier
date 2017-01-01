


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

def prod((x,y)):
    return (x*y)

def doublePairProd((x,y)):
    return (2*x*2*y)

def double(x):
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

# TODO: Should take 2 rdds to be absolutely correct - we do not support self joins!
def cartesianThenMap(rdd, rdd2):
    p = rdd.cartesian(rdd2).map(doublePairProd)
    return p

def mapThenCartesianThenMap(rdd, rdd2):
    p2 = rdd.map(double).cartesian(rdd2.map(double)).map(prod)

    return p2
