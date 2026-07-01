#!/usr/bin/env python

Nodes = {
    "Dox" : ["ATM","TP53","BAX","BCL2"],
    "Vincristine" : ["CDK1"],
    "Actinomycin" : ["ATM","TP53","BAX","BCL2"]
    }

Thresholds = { "Dox" : 0.1, "Vincristine" : 0.1, "Actinomycin" : 0.2}
KD = { "Dox" : 0.1, "Vincristine" : 0, "Actinomycin" : 0.05 }
coeff = { "Dox" : 2, "Vincristine" : 0, "Actinomycin" : 1 }

class Drugs:
    """
    Class to determine drug
    dosage and thresholds
    """
    def __init__(self, name, dosage):
        self.name = name
        self.dosage = dosage
        self.threshold = Thresholds[self.name]
        self.kd = KD[self.name]
        self.coeff = coeff[self.name]
    def find_nodes(self):
        """
        Determines the influenced nodes
        """
        if self.dosage > self.threshold:
            self.nodes = Nodes[self.name]
        else:
            self.nodes = []
        return self.nodes
    def calc_base(self):
        """
        Determines the base status
        """
        if self.dosage > self.threshold:
            self.base = int(round(3/(((self.kd/self.dosage)**self.coeff) + 1) - 1))
        else:
            self.base = 0
        return self.base

    def __str__(self):
        return "Drug(name = %s, dosage = %2.2f)" % (self.name, self.dosage)
        
