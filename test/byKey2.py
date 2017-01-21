
def min(A, x):
    if x<A:
        return x
    else:
        return A

def max(A, x):
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

def keyToSum(k,v):
    return (k, k+v)

def sumAll(A, v):
    return A+v

def directSum(rdd):
    r2 = rdd.map(keyToSum)
    r3 = r2.foldByKey(0, sumAll)
    return r3

def keyToTuple(k,v):
    return (k, (k, v))

def sumTuple(A, (k,v)):
    return A+k+v

def sumByMap(rdd):
    r2 = rdd.map(keyToTuple)
    r3 = r2.foldByKey(0,sumTuple)
    return r3


def isValAtLeastZero(k,v):
    return v >= 0

def isValNonNegative(k,v):
    return v > -1

def sum1(rdd):
    r2 = rdd.filter(isValAtLeastZero)
    return r2.foldByKey(0,sumAll)

def sum2(rdd):
    r2 = rdd.filter(isValNonNegative)
    return r2.foldByKey(0,sumAll)


def joinFilterForPairs(((k,v),(kk,vv))):
    if k==kk:
        return True
    else:
        return False

def outerJoinFilterForPairs(((k,v),(kk,vv))):
    return True


def postJoinMap(((x,y), (z,w))):
    return (x, (y,w))

def join(rdd,rdd2):
    p = rdd.cartesian(rdd2).filter(joinFilterForPairs).map(postJoinMap)
    return p


def filterToday((prod, (date, price))):
    if date == 18112016:
        return True
    else:
        return False

def filterTodayAsMap((prod, (date, price))):
    if date == 18112016:
        return (prod, (date, price))
    else:
        return (prod, (date, 0))

def sumPriceForDate(A, (date, price)):
    return A+price

def sumRevenueForDate(A, (date, price, cost)):
    return A+(price-cost)

def program1real(rp, rc, rs):
    r_today = join(rs,rp).filter(filterToday)
    r_earnings_today = r_today.foldByKey(0, sumPriceForDate)
    r_all = join(join(rs,rp),rc)
    r_revenue = r_all.foldByKey(0, sumRevenueForDate)
    return join(r_earnings_today, r_revenue)

def program1(rp, rc, rs):
    r_today = rs.cartesian(rp).filter(joinFilterForPairs).map(postJoinMap).filter(filterToday) # join(rs,rp)
    r_earnings_today = r_today.foldByKey(0, sumPriceForDate)
    r_j_rs_rp = rs.cartesian(rp).filter(joinFilterForPairs).map(postJoinMap) # join(rs,rp)
    r_all = r_j_rs_rp.cartesian(rc).filter(joinFilterForPairs).map(postJoinMap) # join(r_j_rs_rp,rc)
    r_revenue = r_all.foldByKey(0, sumRevenueForDate)
    return r_earnings_today.cartesian(r_revenue).filter(joinFilterForPairs).map(postJoinMap) # join(r_earnings_today, r_revenue)

def program1outerJoin(rp, rc, rs):
    r_today = rs.cartesian(rp).filter(joinFilterForPairs).map(postJoinMap).map(filterTodayAsMap) # join(rs,rp)
    r_earnings_today = r_today.foldByKey(0, sumPriceForDate)
    r_j_rs_rp = rs.cartesian(rp).filter(joinFilterForPairs).map(postJoinMap) # join(rs,rp)
    r_all = r_j_rs_rp.cartesian(rc).filter(joinFilterForPairs).map(postJoinMap) # join(r_j_rs_rp,rc)
    r_revenue = r_all.foldByKey(0, sumRevenueForDate)
    return r_revenue.cartesian(r_earnings_today).filter(outerJoinFilterForPairs).map(postJoinMap) # join(r_earnings_today, r_revenue)


def count((A, x)):
    return A+1

def countForDate(A, date):
    if date == 18112016:
        return True
    else:
        return False

def mult(folded, multiplier):
    return folded*multiplier

def p3Map((prod, (((countAll, price), cost), (countToday, )))):
    return (prod, (mult(countToday,price), mult(countAll,(price-cost)))) # Need to replace with apply action

def program3real(rp, rc, rs):
    r_counts_sales = rs.foldByKey(0, count)
    r_small_all = join(join(r_counts_sales, rp), rc)
    r_today_count = rs.foldByKey(0, countForDate)
    return join(r_small_all, r_today_count).map(p3Map)

def program3(rp, rc, rs):
    r_counts_sales = rs.foldByKey(0, count)
    r_count_sales_join_rp = r_counts_sales.cartesian(rp).filter(joinFilterForPairs).map(postJoinMap) # join(r_counts_sales, rp)
    r_small_all =  r_count_sales_join_rp.cartesian(rc).filter(joinFilterForPairs).map(postJoinMap)# join(join(r_counts_sales, rp), rc)
    r_today_count = rs.foldByKey(0, countForDate)
    return r_small_all.cartesian(r_today_count).filter(joinFilterForPairs).map(postJoinMap) .map(p3Map) #join(r_small_all, r_today_count).map(p3Map)