

class Agg1ByKeyChecker():
    def __init__(self):
        self.foldNestingLevel = 0

    def inputCb(self, rdd):
        debug("Agg1Checker: foldNestingLevel in input is %d", self.foldNestingLevel)
        return self.foldNestingLevel == 1

    def mapCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD'])

    def filterCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD'])

    def cartesianCb(self, rdd):
        annotations = rdd.getAnnotations()
        if self.foldNestingLevel != 1:
            return False

        currentFoldNestingLevel = self.foldNestingLevel # Keep for checking the level of the other element in the cartesian product
        if not self.walk(annotations['RDD']):
            return False

        self.foldNestingLevel = currentFoldNestingLevel # Reset back to old nesting level before cartesian, and check the other element
        return self.walk(annotations['Paired'])

    def foldCb(self, rdd):
        annotations = rdd.getAnnotations()
        self.foldNestingLevel = self.foldNestingLevel + 2 # Fold will fail the Agg1ByKey checker
        return self.walk(annotations['RDD'])

    def foldByKeyCb(self, rdd):
        annotations = rdd.getAnnotations()
        self.foldNestingLevel = self.foldNestingLevel + 1
        return self.walk(annotations['RDD'])

    def applyCb(self, rdd):
        annotations = rdd.getAnnotations()
        return self.walk(annotations['RDD'])

def isAgg1ByKey(rdd):
    walker = Agg1ByKeyChecker()
    return walker.walk(rdd)

def p1((k,v)):
    return k

def p2((k,v)):
    return v

class Agg1ByKeyEquivalenceChecker:


    def check(self, rdd1, rdd2):
        if (not isAgg1ByKey(rdd1) and not isAgg1ByKey(rdd2)):
            print "Not Agg1 instance: rdd1=%s, rdd2=%s" % (isAgg1ByKey(rdd1), isAgg1ByKey(rdd2))
            return "Not Agg1 instance"


        foldByKeyTerm1 = rdd1.getFoldTerm()
        foldByKeyTerm2 = rdd2.getFoldTerm()

        key1 = foldByKeyTerm1.map(p1)
        key2 = foldByKeyTerm2.map(p1)

        val1 = foldByKeyTerm1.map(p2)
        val2 = foldByKeyTerm2.map(p2)

        annotations1 = rdd1.getAnnotations()
        annotations2 = rdd2.getAnnotations()

        i1, f1 = annotations1['initVal'], annotations1['UDF']
        i2, f2 = annotations2['initVal'], annotations2['UDF']

        fold1 = val1.fold(i1, f1)
        fold2 = val2.fold(i2, f2)

        from SparkZ3.Simulator.AbsSolver import verifyEquivalenceOfSymbolicResults
        keysEqual = verifyEquivalenceOfSymbolicResults(key1, key2)
        print "------------->"
        print "Keys are equal"
        print ""

        valsEqual = verifyEquivalenceOfSymbolicResults(fold1, fold2)
        print "------------->"
        print "Values are equal"
        print ""

        return keysEqual and valsEqual

