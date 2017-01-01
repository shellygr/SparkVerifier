


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

def doubleMap(rdd):
    p = rdd.map(double)
    return p

def doubleAndAdd1Map(rdd):
    p2 = rdd.map(doubleAndAdd1)
    return p2
