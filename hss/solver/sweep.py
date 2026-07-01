#!/usr/bin/env python

from itertools import product
from pprint import pprint
from string import Template
import csv, json, os, copy, re
import xml.etree.ElementTree as ET

Copasi_Templates = {
    "Initial Species Values" : "CN=Root,Model=$model,Vector=Compartments[$compartment],Vector=Metabolites[$species]",
    "Initial Compartment Sizes" : "CN=Root,Model=$model,Vector=Compartments[$compartment]",
    "Initial Global Quantities" : "CN=Root,Model=$model,Vector=Values[$global]",
    "Kinetic Parameters" : "CN=Root,Model=$model,Vector=Reactions[$reaction],ParameterGroup=$paramgroup,Parameter=$parameter"
    }

species_pattern = r"CN=Root,Model=(?P<model>[ -_a-zA-Z0-9]+),Vector=Compartments\[(?P<compartment>\w+)\],Vector=Metabolites\[(?P<species>[ -:_a-zA-Z0-9]+)\],Reference=(?P<reference>\w+)"
value_pattern = r"CN=Root,Model=(?P<model>[ -_a-zA-Z0-9]+),Vector=\w+\[(?P<value>[ -_a-zA-Z0-9]+)\],Reference=(?P<reference>\w+)"


def Generate_Sweeps(Rundata):
    """
    Generates the whole sweep space based on
    the information provided by the user
    """
    #with open(Sweepfile) as fp: Rundata = json.load(fp)
    sweep_info = { key : value["value"] for key, value in Rundata.items() }
    Sweep_Space_Full = []
    for ii, value in enumerate(product(*sweep_info.values())):
        elem_data = {}
        for key, val in zip(sweep_info.keys(), value):
            elem_data[key] = copy.deepcopy(Rundata[key])
            elem_data[key]["value"] = val
        Sweep_Space_Full.append(elem_data.values())

    return Sweep_Space_Full

def Generate_Xml(Xmlfile, remove_namespace=True):
    """
    Obtains and returns the root object of the
    Xml
    """
    with open(Xmlfile, 'r') as fp: xmlstring = fp.read()

    if remove_namespace:
        # Strip all namespace declarations (default and prefixed)
        xmlstring = re.sub(r'\s+xmlns(?::\w+)?="[^"]*"', '', xmlstring)
        # Strip namespace prefixes from element and attribute names
        xmlstring = re.sub(r'<(/?)(\w+):(\w+)', r'<\1\3', xmlstring)
        xmlstring = re.sub(r'(\s)(\w+):(\w+)=', r'\1\3=', xmlstring)
    root = ET.fromstring(xmlstring)

    return root, xmlstring

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


def Set_Elem(elem, target, value, check = False):
    """
    Sets the value of a specific element
    of the Copasi file
    """
    current_value = elem.get(target)
    if current_value is not None:
        elem.set(target, str(value))
    else:
        raise Exception("Target %s not found" % target)
    if check:
        print "Current value %s" %  current_value
        print "Value after changing %s" % elem.get(target)
    return elem

def Get_Headers(root, XPathstr, first = "Time"):
    """
    Extracts name of header species from the report
    """
    headers = [first]
    Report_Table = root.find(XPathstr)
    if Report_Table is not None:
        for elem in Report_Table[1:]:
            cnstr = elem.get('cn')
            try:
                if "Metabolites" in cnstr:
                    species_dict = ET.re.match(species_pattern, elem.get('cn')).groupdict()
                    headers.append(species_dict["species"].replace(':','_').replace(' ','_') + "-" + species_dict["compartment"])
                else:
                    values_dict = ET.re.match(value_pattern, cnstr).groupdict()
                    headers.append(values_dict["value"].replace(" ","_"))
            except AttributeError:
                print "The string %s in the header file does not match any given pattern" % cnstr
                raise
    else:
        raise Exception("Target %s not found" % XPathstr)
    return headers

def Write_File(root, output_cps, encoding = 'utf-8'):
    """
    Writes the root element to a temporary
    file
    """
    ET.ElementTree(root).write(output_cps, encoding='utf-8')


def SetCpsValues(root, parameter, conv=1.0):
    """
    Sets values of provided parameters in the
    Copasi file
    """
    template = Generate_Template(root, Paramtype=parameter["Paramtype"])
    Id = Generate_Id(parameter["substitute"], template)
    XPathstr = ".//*[@cn='%s']" % Id
    elem = Get_Elem(root, XPathstr)
    oldval = elem.get("value")
    elem = Set_Elem(elem, "value", conv*float(parameter["value"]))
    newval = elem.get("value")

    return (oldval, newval)

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
    elem = Set_Elem(elem, value, check = True)
    Write_File(root, output_cps)
    out, err = OdeRun(output_cps)
    species_pattern = r"CN=Root,Model=(?P<model>(\w\s*)+),Vector=Compartments\[(?P<compartment>\w+)\],Vector=Metabolites\[(?P<species>\w+)\],Reference=Concentration"
    Report_Time_Course = root.find("ListOfReports").find("./*[@taskType='timeCourse']")
    Task_Time_Course = root.find("ListOfTasks").find("./*[@type='timeCourse']")[0]
    Outfilename = os.path.join(os.path.split(Copasifile)[0], Task_Time_Course.get("target"))
    Report_Table = Report_Time_Course.find("Table")
    headers = ["Time"]
    for elem in Report_Table[1:]:
        species_dict = ET.re.match(species_pattern, elem.get('cn')).groupdict()
        headers.append(species_dict["species"] + "-" + species_dict["compartment"])

    time_course_data = { key : [] for key in headers }
    print headers
    
    with open(Outfilename) as fp:
        reader = csv.DictReader(fp, fieldnames = headers)
        for ii, row in enumerate(reader):
            if ii == 0:
                continue
            else:
                for key in row:
                    time_course_data[key].append(float(row[key]))
    with open("Time_Course.json","w") as fp: json.dump(time_course_data, fp)
                               
    #for elem in Generate_Sweeps(test_sweep):
    #    print elem
