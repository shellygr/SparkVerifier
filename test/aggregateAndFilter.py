

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


    # print rdd
    min1 = rdd.fold(1000000, min)

    # print min1
    return min1


def takeMinimumAfterDiscount(rdd):
    #
    # print rdd

    rddAfterDiscount = rdd.map(discount)

    min2 = rddAfterDiscount.fold(1000000, min)

    # print min2
    return min2


def isMinimumAtLeast100(rdd):

    # print rdd
    min1 = rdd.fold(1000000, min)

    # print min1
    return apply(atleast100, (min1,))


def isMinimumAfterDiscountAtLeast100(rdd):
    # print rdd

    rddAfterDiscount = rdd.map(discount)

    min2 = rddAfterDiscount.fold(1000000, min)

    # print min2
    return apply(atleast100, (min2,))

def someBoolUninterp(x):
    return True # impl doesn't matter

def isOdd(x):
    return x%2==0

def countUdf((A,x)):
    return A+1

def aggregateFiltered(rdd):
    rddFilter = rdd.filter(isOdd) # originally - someBoolUninterp (TODO: check with aggpair1sync)

    count = rddFilter.fold(0, countUdf)

    return count

def filteringMap(x):
    if isOdd(x): # Originally someBoolUninterp
        return 1
    else:
        return 0

def sumUdf((A,x)):
    return A+x

def aggregateMap(rdd):
    rddMap = rdd.map(filteringMap)

    sum = rddMap.fold(0, sumUdf)

    return sum
