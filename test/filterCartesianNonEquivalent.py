

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

def double(x):
    return 2*x

def doubleAndAdd1(x):
    return 2*x+1

def atLeast50Pair((x,y)):
    return x>=50 and y>=50

def atLeast50PairWrong((x,y)):
    return x>=50 or y>=50

def atLeast50(x):
    return x>=50

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


def cartesianThenWrongFilter(rdd, rdd2):
    p = rdd.cartesian(rdd2).filter(atLeast50PairWrong)
    return p

def filterThenCartesian(rdd, rdd2):

    p2 = rdd.filter(atLeast50).cartesian(rdd2.filter(atLeast50))
    return p2
