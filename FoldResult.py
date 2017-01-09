class FoldResult:
    def __init__(self, term, init, udf, fold_level):
        self.term = term
        self.init = init
        self.udf = udf
        self.fold_level = fold_level # Fold level of the current term

    def set_vars(self, vars):
        self.vars = vars

    def __str__(self):
        return "[%s]_{%s,%s}^{%s}"%(self.term,self.init.n,self.udf.id,self.fold_level)