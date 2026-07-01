#!/usr/bin/env python

"""
This module contains various utility functions that are used to
find and change different elements of the Copasi files. For example
given the name of a species in the model the function
`Change_Species()` can search the root element and change the
value of the initial concentration. 

Example Run
-----------
Although this script can be run separately it is mainly intended
to be imported as a module in other scripts and use the different
functions in it.

Dependencies
------------
- Python >= 2.7

Python 2.7 is needed here as XPath support was introduced in the
ElementTree module only in this version.
"""

from itertools import product
from pprint import pprint
from string import Template
import csv, json, os
import xml.etree.ElementTree as ET

Copasi_Templates = {
    "Initial Species Values" : "CN=Root,Model=$model,Vector=Compartments[$compartment],Vector=Metabolites[$species]",
    "Initial Compartment Sizes" : "CN=Root,Model=$model,Vector=Compartments[$compartment]",
    "Initial Global Quantities" : "CN=Root,Model=$model,Vector=Values[$global]",
    "Kinetic Parameters" : "CN=Root,Model=$model,Vector=Reactions[$reaction],ParameterGroup=$paramgroup,Parameter=$parameter"
    }
'''This contains the template strings for specific elements in the Copasi model such as the list of initial species concentration, compartment size, global parameters and reaction parameters. The placeholders use the syntax of the Template strings in python [string module](https://docs.python.org/2/library/string.html#template-strings)'''

def Generate_Sweeps(sweep_info):
    """
    Generates the whole sweep space based on
    the information provided by the user
    """
    Sweep_Space = []
    for ii, value in enumerate(product(*sweep_info.values())):
        Sweep_Space.append(dict(zip(sweep_info.keys(), value)))

    return Sweep_Space

def Generate_Xml(Xmlfile, remove_namespace=True):
    """
    Obtains and returns the root object of the
    Xml
    """
    with open(Xmlfile, 'r') as fp: xmlstring = fp.read()

    if remove_namespace:
        xmlstring = ET.re.sub(' xmlns="[^"]+"','',xmlstring,count=1)
    root = ET.fromstring(xmlstring)

    return root

def Generate_Template(root, Paramtype="Initial Species Values"):
    """
    This creates identifier string for a specific
    parameter type (species, global quantities etc)
    using the information in a Copasi file
    """
    model = root.find("Model")
    name = model.get("name")

    template = Template(Copasi_Templates[Paramtype])

    return template.safe_substitute(model=name)

def Generate_Id(parameter, template):
    """
    Generates list of template strings for each type
    parameters
    Form of parameter dictionary is as below
    {"Compartments" : "Cytoplasm","Name": "Her4"}
    """

    return Template(template).safe_substitute(parameter)

def Get_Elem(root, XPathstr):
    """
    Gets the specified parameter value from the copasi
    file
    """
    #elem = root.find(".//*[@cn='%s']" % Id)
    elem = root.find(XPathstr)
    if elem is not None:
        return elem
    else:
        raise Exception("Element not found for provided XPath=%s" % XPathstr)

def Cps_Name(elem, pattern):
    """
    Returns name from a specific Cps element
    based on provided pattern
    """
    try:
        match = ET.re.match(pattern, elem.get('cn')).groupdict()
    except AttributeError:
        match = None
    return match

def Change_Species(change_info, Cpsfile, Outfile=""):
    """
    Changes species initial activity based on
    provided information
    """

    root = Generate_Xml(Cpsfile)
    Outfile = Cpsfile if Outfile == "" else Outfile
    Paramtype="Initial Species Values"
    template = Generate_Template(root, Paramtype=Paramtype)
    for species, compartment in change_info:
        parameter = {"compartment" : compartment,"species" : species}
        Id = Generate_Id(parameter, template)
        XPathstr = ".//*[@cn='%s']" % Id
        elem = Get_Elem(root, XPathstr)
        current_value = str(elem.get("value"))
        elem.set("value", str(0.75*current_value))

    ET.ElementTree(root).write(Outfile, encoding='utf-8')

if __name__ == '__main__':

    test_sweep = { "a" : [1,2], "b" : [1,2] }
    Copasifile = "test/ErbB4-JAK2-STAT5_Yamda_Combined_Exec.cps"
    parameter = {"compartment" : "Cytoplasm","species" : "Her4"}
    Paramtype="Initial Species Values"
    output_cps = "test/tempfile.cps"
    value = 6022141790000000 * 2
    root = Generate_Xml(Copasifile)
    template = Generate_Template(root, Paramtype=Paramtype)
    Id = Generate_Id(parameter, template)
    elem = Get_Elem(root, Id)
    print "Current value %3.3e" % float(elem.get("value"))
    elem.set("value", str(value))
    print "Value after changing %3.3e" % float(elem.get("value"))
    ET.ElementTree(root).write(output_cps, encoding='utf-8')
                               
    #for elem in Generate_Sweeps(test_sweep):
    #    print elem
