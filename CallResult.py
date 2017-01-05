class CallResult:
    def __init__(self, func, args):
        self.func = func
        self.args = args

    def __str__(self):
        return "%s%s"%(self.func,self.args)