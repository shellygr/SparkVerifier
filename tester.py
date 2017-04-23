import sys

import time

import Globals

from SparkContext import SparkContext
from Verifier import Verifier
from test import operatorPushback, byKey1, byKey2, byKey3, doublingCartesian, discountTest1, discountTest2, moduloFoldTest1, doublingElements, filterCartesian, filterCartesianNonEquivalent, minimumMaximumFold, aggregateAndFilter, join



class Tester:
    def __init__(self, f1, f2, *args):
        self.f1 = f1
        self.f2 = f2
        self.args = args


    def verify(self):
        verifier = Verifier()
        verifier.setInputs(*self.args)
        return verifier.verifyEquivalence(self.f1, self.f2)

    def __str__(self):
        return "%s=?=%s"%(self.f1,self.f2)

def test(test, expected):
    Globals.testNo += 1
    start = time.time()
    res = test.verify()
    end = time.time()

    if res == True:
        res = "equivalent"
    else:
        res = "Not equivalent"

    print test

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

r_grades = sc.parallelize([(1,78), (2,85), (3,43), (4,100), (5,94), (6,87), (7,55), (8,65)])

test_dict = {
# Basic
    1: (Tester(operatorPushback.mapThenFilter, operatorPushback.filterThenMap, rdd), "equivalent"), #P1, P2
    2: (Tester(operatorPushback.mapThenFilter, operatorPushback.filterThenMapWrong, rdd), "Not equivalent"), #P1, P2'
    3: (Tester(doublingCartesian.cartesianThenMap, doublingCartesian.mapThenCartesian, rdd), "equivalent"), #P25, P26
    4: (Tester(doublingElements.doubleMap, doublingElements.doubleAndAdd1Map, rdd), "Not equivalent"), #P27, P28
    5: (Tester(filterCartesian.cartesianThenFilter, filterCartesian.filterThenCartesian, rdd, rdd2), "equivalent"), #P29, P30
    6: (Tester(filterCartesianNonEquivalent.cartesianThenWrongFilter, filterCartesianNonEquivalent.filterThenCartesian, rdd, rdd2), "Not equivalent"), #P29', P30
    7: (Tester(discountTest1.takeMinimum, discountTest1.takeMinimumAfterDiscount, rdd), "Not equivalent"), #P31, P32
    8: (Tester(discountTest1.isMinimumAtLeast100, discountTest1.isMinimumAfterDiscountAtLeast80, rdd), "equivalent"), #P3, P4
    9: (Tester(discountTest1.isMinimumEqual100, discountTest1.isMinimumAfterDiscountEqual80, rdd), "equivalent"), #P5, P6
    10: (Tester(moduloFoldTest1.takeSumMod5Sum, moduloFoldTest1.takeSumMod5SumOfTriples, rdd), "Not equivalent"), #P33, P34
    11: (Tester(moduloFoldTest1.isSimpleSumMod5Equal0, moduloFoldTest1.isSimpleSumMod5OfTripledEqual0, rdd), "equivalent"), #P15, P16
    12: (Tester(moduloFoldTest1.isSimpleSumMod6Equal0, moduloFoldTest1.isSimpleSumMod6OfTripledEqual0, rdd), "Not equivalent"), #P15', P16'
    13: (Tester(minimumMaximumFold.takeMaximum, minimumMaximumFold.takeMaximumByMinimum, rdd), "equivalent"), # P17, P18
    14: (Tester(minimumMaximumFold.takeMaximumWrongInit, minimumMaximumFold.takeMaximumByMinimum, rdd), "Not equivalent"), #P17', P18
    15: (Tester(aggregateAndFilter.aggregateFiltered, aggregateAndFilter.aggregateMap, rdd), "equivalent"), #P13, P14
    16: (Tester(join.mapJoin, join.joinMap, rdd3, rdd4), "equivalent"), #P9, P10
    17: (Tester(join.slimMapValuesJoin, join.slimJoinMap, rdd3, rdd4), "equivalent"), #P23, P24
    18: (Tester(join.mapValuesJoin, join.joinMap, rdd3, rdd4), "Not equivalent"), #P9', P10
    19: (Tester(join.filterJoin, join.joinThenFilter, rdd5, rdd6), "equivalent"), #P11, P12
    # 20: (Tester(aggregateAndFilter.sumFilter1, aggregateAndFilter.sumFilter2, rdd), "equivalent"), # Very similar to P19,P20 which does the same with by key.
    20: (Tester(byKey1.sum1, byKey1.sum2, rdd3), "equivalent"), # P19, P20
    21: (Tester(byKey1.directSum, byKey1.sumByMap, rdd3), "equivalent"), #P21, P22
    22: (Tester(byKey3.program1, byKey3.program2, r_grades), "equivalent"), #P7, P8
    23: (Tester(moduloFoldTest1.isCountMod5Equal0, moduloFoldTest1.isCountMod5OfTripledEqual0, rdd), "equivalent") #P15'', P16'' - should fail!
}

def testAll():
    for idx, (test_instance, expected_result) in test_dict.items():
        test(test_instance, expected_result)

def run_specific_test(idx):
    test(*test_dict[idx])

testAll()

# run_specific_test(9)
# run_specific_test(10)
# run_specific_test(11)
# run_specific_test(15)
# run_specific_test(18)
# run_specific_test(20)

# Tester(discountTest1.isMinimumAtLeast100, discountTest1.newDiscountProgram, rdd), "equivalent"

#
# test(
# Tester(uninterpretedMapCartesian.cartesianThenMapUninterp, uninterpretedMapCartesian.mapUninterpThenCartesian, rdd, rdd2), "equivalent"
# )
#
# test(
# Tester(uninterpretedMapCartesian.cartesianThenMapUninterp, uninterpretedMapCartesian.mapPartialUninterpThenCartesian, rdd, rdd2), "Not equivalent"
# )


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



# AggN
# test(
#     Tester(byKey2.program5, byKey2.program6, r_prices, r_sales), "equivalent"
# )

# AggN
# test(
#     Tester(byKey2.program2, byKey2.program4, r_prices, r_costs, r_sales), "equivalent"
# )

# Agg1R
# test(
# Tester(byKey2.program1outerJoin, byKey2.program3, r_prices, r_costs, r_sales), "equivalent"
# )
