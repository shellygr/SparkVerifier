
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
    maxElem = rdd.fold(-1000000, max)
    return maxElem

def takeMaximumWrongInit(rdd):
    maxElem = rdd.fold(0, max)
    return maxElem


def takeMaximumByMinimum(rdd):
    invertedRdd = rdd.map(invert)
    minElem = invertedRdd.fold(1000000, min)
    return apply(invert, (minElem,))

def keyToSum((k,v)):
    return (k, k+v)

def sumAll(A, v):
    return A+v

def directSum(rdd):
    r2 = rdd.map(keyToSum)
    r3 = r2.foldByKey(0, sumAll)
    return r3

def keyToTuple((k,v)):
    return (k, (k, v))

def sumTuple(A, (k,v)):
    return A+k+v

def sumByMap(rdd):
    r2 = rdd.map(keyToTuple)
    r3 = r2.foldByKey(0,sumTuple)
    return r3


def isValAtLeastZero((k,v)):
    return v >= 0

def isValNonNegative((k,v)):
    return v > -1

def sum1(rdd):
    r2 = rdd.filter(isValAtLeastZero)
    return r2.foldByKey(0,sumAll)

def sum2(rdd):
    r2 = rdd.filter(isValNonNegative)
    return r2.foldByKey(0,sumAll)