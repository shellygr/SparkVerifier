import sys

import time

import Globals

from SparkContext import SparkContext
from Verifier import Verifier
from test import operatorPushback, byKey1, byKey2, doublingCartesian, discountTest1, discountTest2, moduloFoldTest1, doublingElements, filterCartesian, filterCartesianNonEquivalent, minimumMaximumFold, aggregateAndFilter, join



class Tester:
    def __init__(self, f1, f2, *args):
        self.f1 = f1
        self.f2 = f2
        self.args = args


    def verify(self):
        verifier = Verifier()
        verifier.setInputs(*self.args)
        return verifier.verifyEquivalence(self.f1, self.f2)

def test(test, expected):
    Globals.testNo += 1
    start = time.time()
    res = test.verify()
    end = time.time()

    if res == True:
        res = "equivalent"
    else:
        res = "Not equivalent"

    if res==expected:
        print '\033[1;32;50m' + "%d: passed!" % Globals.testNo + '\033[0m'
        print 'time: %.2f seconds'%(end-start)
    else:
        print '\033[1;31;50m' + "%d: failed! expected %s, got %s" % (Globals.testNo, expected, res) + '\033[0m'
        sys.exit(-1)

    # Clear globals uninterpreted functions after every test
    Globals.uninterpFuncs = {}


sc = SparkContext(appName="CAV2017")
# rdd = sc.parallelize([2,3,4,2,3,2,24,45,2,3,42,342,3,1,42,43,24,52,11,341,12,41,4,3,9,6,5,46,45,70])
rdd = sc.parallelize([293, 2910])
rdd2 = sc.parallelize([2934, 2, 32, 87])

rdd3 = sc.parallelize([(1,2),(3,5)])
rdd4 = sc.parallelize([(231,212),(13,85), (2398, 83)])

rdd5 = sc.parallelize([(1,2),(3,5)])
rdd6 = sc.parallelize([(231,212),(13,85), (2398, 83)])


# The interesting example!
r_prices = sc.parallelize([(1,89),(2,110),(3,65)])
r_costs = sc.parallelize([(1,40),(2,60),(3,10)])
r_sales = sc.parallelize([(1,18112016), (3,18112016), (3,20112016), (2,01122015), (3,15122016), (2,01022016),   (1,12122016)])


# Basic
test(
Tester(operatorPushback.mapThenFilter, operatorPushback.filterThenMap, rdd), "equivalent"
)

test(
Tester(operatorPushback.mapThenFilter, operatorPushback.filterThenMapWrong, rdd), "Not equivalent"
)


test(
Tester(doublingCartesian.cartesianThenMap, doublingCartesian.mapThenCartesian, rdd), "equivalent"
)

test(
Tester(doublingElements.doubleMap, doublingElements.doubleAndAdd1Map, rdd), "Not equivalent"
)

test(
Tester(filterCartesian.cartesianThenFilter, filterCartesian.filterThenCartesian, rdd, rdd2), "equivalent"
)

test(
Tester(filterCartesianNonEquivalent.cartesianThenWrongFilter, filterCartesianNonEquivalent.filterThenCartesian, rdd, rdd2), "Not equivalent"
)

test(
Tester(discountTest1.takeMinimum, discountTest1.takeMinimumAfterDiscount, rdd), "Not equivalent"
)

test(
Tester(discountTest1.isMinimumAtLeast100, discountTest1.isMinimumAfterDiscountAtLeast80, rdd), "equivalent"
)

test(
Tester(discountTest1.isMinimumEqual100, discountTest1.isMinimumAfterDiscountEqual80, rdd), "equivalent"
)
#
# test(
# Tester(discountTest1.isMinimumAtLeast100, discountTest1.newDiscountProgram, rdd), "equivalent"
# )


test(
Tester(moduloFoldTest1.takeSumMod5Sum, moduloFoldTest1.takeSumMod5SumOfTriples, rdd), "Not equivalent"
)

test(
Tester(moduloFoldTest1.isSimpleSumMod5Equal0, moduloFoldTest1.isSimpleSumMod5OfTripledEqual0, rdd), "equivalent" # equivalent due to agg sync, but inquivalent in agg1
)

test(
Tester(moduloFoldTest1.isSimpleSumMod6Equal0, moduloFoldTest1.isSimpleSumMod6OfTripledEqual0, rdd), "Not equivalent"
)

test(
Tester(minimumMaximumFold.takeMaximum, minimumMaximumFold.takeMaximumByMinimum, rdd), "equivalent"
)

test(
Tester(minimumMaximumFold.takeMaximumWrongInit, minimumMaximumFold.takeMaximumByMinimum, rdd), "Not equivalent"
)
#
# test(
# Tester(uninterpretedMapCartesian.cartesianThenMapUninterp, uninterpretedMapCartesian.mapUninterpThenCartesian, rdd, rdd2), "equivalent"
# )
#
# test(
# Tester(uninterpretedMapCartesian.cartesianThenMapUninterp, uninterpretedMapCartesian.mapPartialUninterpThenCartesian, rdd, rdd2), "Not equivalent"
# )

test(
Tester(aggregateAndFilter.aggregateFiltered, aggregateAndFilter.aggregateMap, rdd), "equivalent"
)

test(
Tester(join.mapJoin, join.joinMap, rdd3, rdd4), "equivalent"
)

test(
Tester(join.slimMapValuesJoin, join.slimJoinMap, rdd3, rdd4), "equivalent"
)

test(
Tester(join.mapValuesJoin, join.joinMap, rdd3, rdd4), "Not equivalent"
)

test(
Tester(join.filterJoin, join.joinThenFilter, rdd5, rdd6), "equivalent"
)


# Not Presburger
# test(
# Tester(doublingCartesianNonConstMult.mapThenCartesianThenMap, doublingCartesianNonConstMult.cartesianThenMap, rdd, rdd2), "equivalent"
# )


# Fold with tuple intermediate values
# test(
# Tester(mult.g1, mult.g2, rdd), "equivalent"
# )
#
# test(
# TesterMult(mult.func1, mult.func2, rdd), "equivalent"
# )


# BY KEY
#
test(
Tester(byKey1.sum1, byKey1.sum2, rdd3), "equivalent"
)

test(
Tester(byKey1.directSum, byKey1.sumByMap, rdd3), "equivalent"
)

test(
Tester(byKey2.program1, byKey2.program3, r_prices, r_costs, r_sales), "equivalent"
)

