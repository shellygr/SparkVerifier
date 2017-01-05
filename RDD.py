from z3 import Int

from RDDTools import gen_name


class RDD:
    def __init__(self, name, paramType, arity):
        self.name = name
        self.fv = set()
        self.arity = arity
        self.paramType = paramType
        self.vars = None

    def refresh_vars(self):
        def rename_var(var):
            name = var.id
            new_name = gen_name(name)
            return Int(new_name)

        new_vars = map(rename_var, self.vars)

        print "refreshed vars for", self.name,":",new_vars

        self.vars = new_vars
