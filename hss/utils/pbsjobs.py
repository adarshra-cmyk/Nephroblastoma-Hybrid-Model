#!/usr/bin/env python

import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta


pbs_jobstatus = {
    "R" : "running",
    "Q" : "queued",
    "C" : "completed",
    "E" : "exiting",
    "T" : "moved",
    "W" : "waiting",
    "H" : "held"
    }

def monitor(jobid):
    """
    Checks the status of a job previusly
    submitted on the cluster and returns
    relevant information
    """
    pstat = subprocess.Popen('qstat -x %s' % jobid, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    outs, errs = pstat.communicate()
    jobinfo = {}
    if outs != "":
        jobinfo = convert_xml(outs)
    elif "Unknown Job Id" in errs:
        pass
    else:
        raise Exception("Unknown qstat error %s" % errs)
    
    return jobinfo
            

def convert_xml(xmlstring):
    """
    Returns the job information in the form of
    a dictionary
    """
    jobinfo = {}
    root = ET.fromstring(xmlstring)
    for elem in root.getiterator("Job")[0]:
        if elem.tag in ["resources_used", "Resource_List","Walltime"]:
            jobinfo[elem.tag] = {}
            for subelem in elem.getiterator()[0]:
                if subelem.tag == "Remaining":
                    d = timedelta(seconds = float(subelem.text))
                    jobinfo[elem.tag][subelem.tag] = str(d)
                else:
                    jobinfo[elem.tag][subelem.tag] = subelem.text
        else:
            if "time" in elem.tag:
                try:
                    date_time = datetime.fromtimestamp(float(elem.text))
                    jobinfo[elem.tag] = date_time.strftime("%m/%d/%Y %H:%M:%S")
                except TypeError:
                    pass
                except Exception:
                    raise
            elif elem.tag == "job_state":
                jobinfo[elem.tag] = pbs_jobstatus[elem.text]
            else:
                jobinfo[elem.tag] = elem.text
        
    return jobinfo

def run(jobfile):
    """
    Submits a specified jobfile and returns
    the jobid
    """
    p = subprocess.Popen('qsub %s' % jobfile, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = p.communicate()
    if out == "":
        raise Exception("Jobscript %s submission failed with error %s" % (jobfile, err))

    return out.strip()
