
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

#TODO: Does not handle well if the if has no else, considers it's a bottom
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

