
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


def count(A, x):
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

# TODO: program2 and program4 - Check why fails on key when has more than 1 join - program4 key is bottom?
def program2(rp, rc, rs):
    rpbk = rp.foldByKey(0, sumAll)
    rcbk = rc.foldByKey(0, sumAll)
    rsbk = rc.foldByKey(0, sumAll)

    rp_rc_join = rpbk.cartesian(rcbk).filter(joinFilterForPairs).map(postJoinMap)
    rp_rc_rs_join = rp_rc_join.cartesian(rsbk).filter(joinFilterForPairs).map(postJoinMap)

    return rp_rc_join

def sumSecond(A, (x,y)):
    return A+y

def sumAll2((A,B), (x,y)):
    return (A+x,B+y)

def sumAll3((A,B,C), (x,y,z)):
    return (A+x,B+y,C+z)

def program4(rp, rc, rs):
    rp_rc_join = rp.cartesian(rc).filter(joinFilterForPairs).map(postJoinMap)
    rp_rc_rs_join = rp_rc_join.cartesian(rs).filter(joinFilterForPairs).map(postJoinMap)

    return rp_rc_join.foldByKey((0,0,0), sumAll2)


def program5(rp, rs):
    rp_rs_join = rp.cartesian(rs).filter(joinFilterForPairs).map(postJoinMap)
    return rp_rs_join.foldByKey(0, sumSecond)

def program6(rp, rs):
    rsbk = rs.foldByKey(0, sumSecond)
    rp_rsbk_join = rp.cartesian(rsbk).filter(joinFilterForPairs).map(postJoinMap)
    return rp_rsbk_join

def mod10(x):
    return x/10

def invert_to_class((s,g)):
    return (mod10(g), s)

def passed_class((grade_class,count)):
    return grade_class >= 6

def students_who_passed((s,g)):
    return g >= 60

def only_positive_grades((s,g)):
    return g >= 0

def program1(rg):
    # rg_positive_grades = rg.filter(only_positive_grades)
    rg_invert = rg.map(invert_to_class)
    rg_histogram = rg_invert.foldByKey(0, count)
    return rg_histogram.filter(passed_class)

def program2(rg):
    # rg_positive_grades = rg.filter(only_positive_grades)
    rg_passed = rg.filter(students_who_passed)
    rg_passed_invert = rg_passed.map(invert_to_class)
    return rg_passed_invert.foldByKey(0, count)