from SparkContext import SparkContext


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

sc = SparkContext(appName="discountTest2")

# rdd = sc.parallelize([2,3,4,2,3,2,24,45,2,3,42,342,3,1,42,43,24,52,11,341,12,41,4,3,9,6,5,46,45,70])
rdd = sc.parallelize([293, 2910])

print rdd
# min1 = rdd.fold(1000000, min)

# rddAfterDiscount = rdd.map(discount)

# min2 = rddAfterDiscount.fold(100000, min)

# print formulate(min1)
# print apply(atleast100, (min1,))
# print min2

# print convertToZ3(min)
# print convertToZ3(discount)

# print Agg1EquivalenceChecker().check(min1,min2, id, id) # Should fail

# print Agg1EquivalenceChecker().check(min1,min2, atleast100, atleast100)
