import Globals
from Agg1ByKeySolver import isAgg1ByKey, Agg1ByKeyEquivalenceChecker
from Agg1Solver import isAgg1, Agg1EquivalenceChecker
from AggPair1SyncSolver import AggPair1SyncClassDefChecker
from AggPair1SyncSolver import AggPair1SyncEquivalenceChecker
from NoAggSolver import isNoAgg, noAggEquivalenceTest


def verifyEquivalenceOfSymbolicResults(result1, result2):
    # TODO: Return this
    """
    if not verifySignature(result1, result2): # Fix for programs returning a tuple
        return False
    """

    # replace trivial folds - TODO

    # noagg checking
    if isNoAgg(result1) and isNoAgg(result2):
        noAggResult = noAggEquivalenceTest(result1, result2)
        return noAggResult

    # not applicable for noAgg - continue with Agg1
    if isAgg1(result1) and isAgg1(result2):
        if AggPair1SyncClassDefChecker().check(result1, result2):
             return AggPair1SyncEquivalenceChecker().check(result1, result2)
        Globals.uninterpFuncs = {} # Resetting after running AggPair1Sync def checker
        return Agg1EquivalenceChecker().check(result1, result2)

    if isAgg1ByKey(result1) and isAgg1ByKey(result2):
        return Agg1ByKeyEquivalenceChecker().check(result1, result2)



    return "not implemented yet"





def verifyEquivalenceOfSymbolicResultsMult(result1, result2):
    return verifyEquivalenceOfSymbolicResults(result1[0], result2[0])
    # return AggMultChecker().check(result1, result2)

