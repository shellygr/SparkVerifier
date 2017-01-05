

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


def atleast80(x):
    return x>=80

def equal100(x):
    return x==100


def equal80(x):
    return x==80

def id(x):
    return x

def takeMinimum(rdd):
    min1 = rdd.fold(1000, min)
    return min1


def takeMinimumAfterDiscount(rdd):
    rddAfterDiscount = rdd.map(newDiscount) # Originally discount. why aggpair1sync?
    min2 = rddAfterDiscount.fold(1000, min)
    return min2


def isMinimumAtLeast100(rdd):
    min1 = rdd.fold(1000, min)

    return atleast100(min1)


def isMinimumEqual100(rdd):
    min1 = rdd.fold(1000, min)

    return equal100(min1)


def isMinimumAtLeast80(rdd):
    min1 = rdd.fold(1000, min)

    return atleast80(min1)

def isMinimumAfterDiscountAtLeast100(rdd):

    rddAfterDiscount = rdd.map(discount)

    min2 = rddAfterDiscount.fold(1000, min)

    return atleast100(min2)

def isMinimumAfterDiscountAtLeast80(rdd):

    rddAfterDiscount = rdd.map(newDiscount) # Originally discount

    min2 = rddAfterDiscount.fold(1000, min)

    return atleast80(min2)


def isMinimumAfterDiscountEqual80(rdd):

    rddAfterDiscount = rdd.map(newDiscount) # Originally discount

    min2 = rddAfterDiscount.fold(1000, min)

    return equal80(min2)


def newDiscount(x):
    # return x*4/5
    return x-20

def newDiscountProgram(rdd):
    rddAfterDiscount = rdd.map(newDiscount)
    min2 = rddAfterDiscount.fold(1000000, min)
    return apply(atleast80, (min2,))
