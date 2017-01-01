import inspect

# DEBUG = False
DEBUG = True

def debug(str, *args):
    if (DEBUG):
        print ("%s: "+str) %((inspect.stack()[1][3], )+args)

def idFunc(x):
    return x

# First must be an RDD
def apply(f, args):
    rddObj = args[0]
    return rddObj.apply(f)
