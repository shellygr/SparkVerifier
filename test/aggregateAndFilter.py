

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

def id(x):
    return x

def takeMinimum(rdd):
    min1 = rdd.fold(1000000, min)
    return min1


def takeMinimumAfterDiscount(rdd):
    rddAfterDiscount = rdd.map(discount)

    min2 = rddAfterDiscount.fold(1000000, min)

    return min2


def isMinimumAtLeast100(rdd):
    min1 = rdd.fold(1000000, min)
    return apply(atleast100, (min1,))


def isMinimumAfterDiscountAtLeast100(rdd):
    rddAfterDiscount = rdd.map(discount)
    min2 = rddAfterDiscount.fold(1000000, min)
    return apply(atleast100, (min2,))


def someBoolUninterp(x):
    return True # impl doesn't matter

def isEven(x):
    return x%2==0

def isOdd(x):
    return x%2==1


def countUdf(A,x):
    return A+1

def aggregateFiltered(rdd):
    rddFilter = rdd.filter(isOdd) # originally - someBoolUninterp (TODO: check with aggpair1sync)

    count = rddFilter.fold(0, countUdf)

    return count

def filteringMap(x):
    if isOdd(x): # Originally someBoolUninterp
        return 1 # return 2 - for rebuttal cav'17 test
    else:
        return 0

def sumUdf(A,x):
    return A+x

def aggregateMap(rdd):
    rddMap = rdd.map(filteringMap)

    sum = rddMap.fold(0, sumUdf)

    return sum

def isValAtLeastZero(v):
    return v >= 0

def isValNonNegative(v):
    return v > -1

def sumFilter1(rdd):
    r2 = rdd.filter(isValAtLeastZero)
    return r2.fold(0,sumUdf)

def sumFilter2(rdd):
    r2 = rdd.filter(isValNonNegative)
    return r2.fold(0,sumUdf)