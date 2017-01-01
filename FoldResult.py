class FoldResult:
    def __init__(self, term, init, udf):
        self.term = term
        self.init = init
        self.udf = udf

    def set_vars(self, vars):
        self.vars = vars