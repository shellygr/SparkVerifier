


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

def doubleValue((x,y)):
    return (x, 2*y)

def doubleJoinedPair((x, (y,z))):
    return (2*x, (2*y, 2*z))

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

def joinFilter((x,y)):
    if x[0] == y[0]:
        return True
    else:
        return False

def joinFilterForPairs(((k,v),(kk,vv))):
    if k==kk:
        return True
    else:
        return False

# Do not support slicing with index yet!
def postJoinMapSlice((x,y)):
    return (x[0], (x[1], y[1]))

def postJoinMap(((x,y), (z,w))):
    return (x, (y,w))


def specialDoubleMap(((x,y), (z,w))):
    return ((x,2*y), (z,2*w))

# TODO: Should take 2 rdds to be absolutely correct - we do not support self joins!
def joinMap(rdd,rdd2):
    p = rdd.cartesian(rdd2).filter(joinFilterForPairs).map(postJoinMap).map(doubleJoinedPair)
    return p

def mapJoin(rdd,rdd2):
    r1 = rdd.map(doublePair)
    r2 = rdd2.map(doublePair)
    p2 = r1.cartesian(r2)
    p3 = p2.filter(joinFilterForPairs).map(postJoinMap)
    return p3

def mapValuesJoin(rdd, rdd2):
    r1 = rdd.map(doubleValue)
    r2 = rdd2.map(doubleValue)
    p2 = r1.cartesian(r2)
    p3 = p2.filter(joinFilterForPairs).map(postJoinMap)
    return p3



def slimMapValuesJoin(rdd, rdd2):
    r1 = rdd.map(doubleValue)
    r2 = rdd2.map(doubleValue)
    p2 = r1.cartesian(r2)
    # p3 = p2.filter(joinFilter).map(postJoinMap)
    return p2

def slimJoinMap(rdd,rdd2):
    return rdd.cartesian(rdd2).map(specialDoubleMap)

def fSimp((k,v)):
    # return v >= 50
    return k%2==1

def fJoin((k, (v,w))):
    # return v>=50 and w >= 50
    return k%2==1

def filterJoin(rdd, rdd2):
    rr1 = rdd.filter(fSimp)
    rr2 = rdd2.filter(fSimp)
    c = rr1.cartesian(rr2)
    return c.filter(joinFilterForPairs).map(postJoinMap)

def joinThenFilter(rdd, rdd2):
    cc = rdd.cartesian(rdd2)
    j = cc.filter(joinFilterForPairs).map(postJoinMap)
    return j.filter(fJoin)