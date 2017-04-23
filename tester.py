import sys

import time

import Globals

from SparkContext import SparkContext
from Verifier import Verifier
from test import operatorPushback, byKey1, byKey3, doublingCartesian, discountTest1, moduloFoldTest1, \
    doublingElements, filterCartesian, filterCartesianNonEquivalent, minimumMaximumFold, aggregateAndFilter, join

"""
 A tester class for an instance of the equivalence problem.
 Given f1, f2 are Python functions that integrate with the real Spark library
    (it is almost compatible with real Spark code and very similar to SparkLite syntax).
"""
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

""" Run a test, with the expected result, where programs are denoted p and q """
def test(test, expected, p, q):
    Globals.testNo += 1
    print ""
    print "---------------------------------------------------------------"
    print "Testing %s, %s for equivalence..." % (p, q)
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
        print 'time: %.2f seconds' % (end - start)
        # sys.exit(-1)

    # Clear globals uninterpreted functions after every test
    Globals.uninterpFuncs = {}

# sc, rddN variables are for Spark library support
sc = SparkContext(appName="CAV2017")

rdd = sc.parallelize([293, 2910])
rdd2 = sc.parallelize([2934, 2, 32, 87])

rdd3 = sc.parallelize([(1,2),(3,5)])
rdd4 = sc.parallelize([(231,212),(13,85), (2398, 83)])

rdd5 = sc.parallelize([(1,2),(3,5)])
rdd6 = sc.parallelize([(231,212),(13,85), (2398, 83)])

r_grades = sc.parallelize([(1,78), (2,85), (3,43), (4,100), (5,94), (6,87), (7,55), (8,65)])

"""
    Order of the tests is not equal to that in the highlighted test cases or in the Technical report.
    Can use run_specific_test(TestNumber) to run a specific test.
    "Equivalent!" message will be outputted for every component in the tuple, if the return value is of tuple bag type.
"""
test_dict = {
# Basic
    1: (Tester(operatorPushback.mapThenFilter, operatorPushback.filterThenMap, rdd), "equivalent" , "P1", "P2"), #P1, P2
    2: (Tester(operatorPushback.mapThenFilter, operatorPushback.filterThenMapWrong, rdd), "Not equivalent", "P1", "P2'"), #P1, P2'
    3: (Tester(doublingCartesian.cartesianThenMap, doublingCartesian.mapThenCartesian, rdd), "equivalent", "P25", "P26"), #P25, P26
    4: (Tester(doublingElements.doubleMap, doublingElements.doubleAndAdd1Map, rdd), "Not equivalent", "P27", "P28"), #P27, P28
    5: (Tester(filterCartesian.cartesianThenFilter, filterCartesian.filterThenCartesian, rdd, rdd2), "equivalent", "P29", "P30"), #P29, P30
    6: (Tester(filterCartesianNonEquivalent.cartesianThenWrongFilter, filterCartesianNonEquivalent.filterThenCartesian, rdd, rdd2), "Not equivalent", "P29'", "P30"), #P29', P30
    7: (Tester(discountTest1.takeMinimum, discountTest1.takeMinimumAfterDiscount, rdd), "Not equivalent","P31", "P32"), #P31, P32
    8: (Tester(discountTest1.isMinimumAtLeast100, discountTest1.isMinimumAfterDiscountAtLeast80, rdd), "equivalent", "P3", "P4"), #P3, P4
    9: (Tester(discountTest1.isMinimumEqual100, discountTest1.isMinimumAfterDiscountEqual80, rdd), "equivalent", "P5", "P6"), #P5, P6
    10: (Tester(moduloFoldTest1.takeSumMod5Sum, moduloFoldTest1.takeSumMod5SumOfTriples, rdd), "Not equivalent", "P33", "P34"), #P33, P34
    11: (Tester(moduloFoldTest1.isSimpleSumMod5Equal0, moduloFoldTest1.isSimpleSumMod5OfTripledEqual0, rdd), "equivalent", "P15", "P16"), #P15, P16
    12: (Tester(moduloFoldTest1.isSimpleSumMod6Equal0, moduloFoldTest1.isSimpleSumMod6OfTripledEqual0, rdd), "Not equivalent", "P15'", "P16'"), #P15', P16'
    13: (Tester(moduloFoldTest1.isCountMod5Equal0, moduloFoldTest1.isCountMod5OfTripledEqual0, rdd), "equivalent", "P15''", "P16''"), #P15'', P16'' - should fail!
    14: (Tester(minimumMaximumFold.takeMaximum, minimumMaximumFold.takeMaximumByMinimum, rdd), "equivalent", "P17", "P18"), # P17, P18
    15: (Tester(minimumMaximumFold.takeMaximumWrongInit, minimumMaximumFold.takeMaximumByMinimum, rdd), "Not equivalent", "P17'", "P18"), #P17', P18
    16: (Tester(aggregateAndFilter.aggregateFiltered, aggregateAndFilter.aggregateMap, rdd), "equivalent", "P13", "P14"), #P13, P14
    17: (Tester(join.mapJoin, join.joinMap, rdd3, rdd4), "equivalent", "P9", "P10"), #P9, P10
    18: (Tester(join.slimMapValuesJoin, join.slimJoinMap, rdd3, rdd4), "equivalent", "P23", "P24"), #P23, P24
    19: (Tester(join.mapValuesJoin, join.joinMap, rdd3, rdd4), "Not equivalent", "P9'", "P10"), #P9', P10
    20: (Tester(join.filterJoin, join.joinThenFilter, rdd5, rdd6), "equivalent", "P11", "P12"), #P11, P12
    21: (Tester(byKey1.sum1, byKey1.sum2, rdd3), "equivalent", "P19", "P20"), # P19, P20
    22: (Tester(byKey1.directSum, byKey1.sumByMap, rdd3), "equivalent", "P21", "P22"), #P21, P22
    23: (Tester(byKey3.program1, byKey3.program2, r_grades), "equivalent", "P7", "P8") #P7, P8
}

def testAll():
    for idx, (test_instance, expected_result, p, q) in test_dict.items():
        test(test_instance, expected_result, p, q)

def run_specific_test(idx):
    test(*test_dict[idx])

testAll()
