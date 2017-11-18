import inspect

DEBUG = False
# DEBUG = True

def debug(str, *args):
    if (DEBUG):
        print ('\033[1m'+"%s: "+'\033[0m'+str) %((inspect.stack()[1][3], )+args)

def idFunc(x):
    return x

# First arg must be an RDD
def apply(f, args):
    rddObj = args[0]
    return rddObj.apply(f)
