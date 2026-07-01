#!/usr/bin/env python

import subprocess, os
import csv, json
import xml.etree.ElementTree as ET
from pprint import pprint
from change import Generate_Xml

def OdeRun(input_cps, copasipath='CopasiSE'):
    """
    Wrapper function to call Copasi executable and run for
    a specified set of conditions

    Parameters
    -----------
    input_cps : string
        Name of the input copasi filename (*.cps)
    copasipath : string, optional
        Full path of the copasi executable. By default assumes
        CopasiSE is in system path and passes this name
        to subprocess
    logfile : string, optional
        Name of the output logfile. By default this writes
        the standard out and error of the Copasi command
        into a file with name obtain by joining input_cps
        name and current date and time

    Returns
    -------------
    out : string
        Output from Copasi collected by subprocess
    err : string
        Error messages from Copasi collected by subprocess
    """

    #Get system architecture and use appropriate copasi file
    out = ''
    err = ''
    Copasi_Command = copasipath

    #Call Copasi executable using the name of the input cps
    output_cps = input_cps
    p = subprocess.Popen(Copasi_Command + ' --verbose ' + input_cps,shell=True,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for lines in iter(p.stdout.readline,''): out += lines.rstrip()
    for lines in iter(p.stderr.readline,''): err += lines.rstrip()
    streams = p.communicate()

    return out, err

def OdeData(Cpsfile):
    """
    Collects data from specified cps file by
    reading the target csv location and headers
    """
    species_pattern = r"CN=Root,Model=(?P<model>(\w\s*)+),Vector=Compartments\[(?P<compartment>\w+)\],Vector=Metabolites\[(?P<species>\w+)\],Reference=Concentration"
    root = Generate_Xml(Cpsfile)
    Report_Time_Course = root.find("ListOfReports").find("./*[@taskType='timeCourse']")
    Task_Time_Course = root.find("ListOfTasks").find("./*[@type='timeCourse']")[0]
    Outfilename = os.path.join(os.path.split(Cpsfile)[0], Task_Time_Course.get("target"))
    Report_Table = Report_Time_Course.find("Table")
    headers = ["Time"]
    for elem in Report_Table[1:]:
        species_dict = ET.re.match(species_pattern, elem.get('cn')).groupdict()
        headers.append(species_dict["species"] + "-" + species_dict["compartment"])

    time_course_data = { key : [] for key in headers }
    
    with open(Outfilename) as fp:
        reader = csv.DictReader(fp, fieldnames = headers)
        for ii, row in enumerate(reader):
            if ii == 0:
                continue
            else:
                for key in row:
                    time_course_data[key].append(float(row[key]))
    os.remove(Outfilename)

    return time_course_data

def BoolRun(network):
    """
    Runs a Boolean network using the specified
    input configuration
    """
    states = dict((key,val["initial_state"]) for key, val in network.items())
    network_modified =  dict(((key, value['base'],value['initial_state']),value['input_nodes']) for key, value in network.items())
    for key, val in network_modified.items():
        species, weights = zip(*val)
        sumelem = sum(map(lambda xi,yi : xi*yi, [network[j]["initial_state"] for j in species],weights)) if species[0] != "None" else 0 + key[1]
        states[key[0]] = 1 if sumelem > 0 else (0 if sumelem < 0 else states[key[0]])

    return states

if __name__ == '__main__':

    Cpsfile = "ErbB4-JAK2-STAT5_Yamda_Combined_Exec.cps"
    out, err = OdeRun(Cpsfile)
    time_course_data = OdeData(Cpsfile)
    networkfile = "../io/p53_network.json"
    with open(networkfile) as fp: network = json.load(fp)
    orig_states = dict((key,val["initial_state"]) for key, val in network.items())
    print "Initial States: %s" % orig_states
    states = BoolRun(network)
    print "Final States: %s" % states
