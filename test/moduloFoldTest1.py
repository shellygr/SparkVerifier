

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

def mod5(x):
    return x%5

def sumMod5(A,x):
    return mod5(A+x)

def simpleSum(A,x):
    return A+x

def triple(x):
    return 3*x

def atleast100(x):
    return x>=100

def equal0(x):
    return x==0

def equal0mod5(x):
    return equal0(x%5)


def equal0mod6(x):
    return equal0(x%6)

def id(x):
    return x

def takeSumMod5Sum(rdd):
    modResult1 = rdd.fold(0, sumMod5)
    return modResult1

def takeSumMod5SumOfTriples(rdd):
    rddTripled = rdd.map(triple)
    modResult2 = rddTripled.fold(0, sumMod5)
    return modResult2

def isSimpleSumMod5Equal0(rdd):
    modResult1 = rdd.fold(0, simpleSum)
    return equal0mod5(modResult1)

def isSimpleSumMod5OfTripledEqual0(rdd):
    rddTripled = rdd.map(triple)
    modResult2 = rddTripled.fold(0, simpleSum)
    return equal0mod5(modResult2)

def isSimpleSumMod6Equal0(rdd):
    modResult1 = rdd.fold(0, simpleSum)
    return equal0mod6(modResult1)

def isSimpleSumMod6OfTripledEqual0(rdd):
    rddTripled = rdd.map(triple)
    modResult2 = rddTripled.fold(0, simpleSum)
    return equal0mod6(modResult2)
