

def min((A, x)):
    if x<A:
        return x
    else:
        return A

def max((A, x)):
    if x>A:
        return x
    else:
        return A

#TODO: Does not handle well if the if has no else, thinks it's a bottom
def discount(x):
    if x>125:
        return x*4/5
    else:
        return x

def discountReverse(x):
    if x>50:
        return x*2
    else:
        return x


def atleast100(x):
    return x>=100

def invert(x):
    return -x

def id(x):
    return x

def takeMaximum(rdd):
    maxElem = rdd.fold(-100, max)
    return maxElem

def takeMaximumWrongInit(rdd):
    maxElem = rdd.fold(0, max)
    return maxElem


def takeMaximumByMinimum(rdd):
    invertedRdd = rdd.map(invert)
    minElem = invertedRdd.fold(100, min)
    return apply(invert, (minElem,))

