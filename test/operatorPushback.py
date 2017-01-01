


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
    p1 = rdd.map(double)
    p2 = p1.filter(lessThan100)
    return p2

def filterThenMap(rdd):
    p2 = rdd.filter(lessThan50).map(double)
    return p2

def filterThenMapWrong(rdd):
    p2 = rdd.filter(lessThan100).map(double)
    return p2