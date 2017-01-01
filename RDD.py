class RDD:
    def __init__(self, name, paramType, arity):
        self.name = name
        self.fv = set()
        self.arity = arity
        self.paramType = paramType
        self.vars = None