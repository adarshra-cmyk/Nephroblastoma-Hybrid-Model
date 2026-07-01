#!/usr/bin/env python

import subprocess

slurm_jobstatus = {
    "BF" : "boot failed",
    "CA" : "cancelled",
    "CD" : "completed",
    "DL" : "terminated on deadline",
    "F" : "job failed",
    "NF" : "node failed",
    "OOM" : "out of memory error",
    "PD" : "pending",
    "PR" : "terminated due to preemption",
    "R" : "running",
    "RQ" : "job requeued",
    "RS" : "resizing",
    "RV" : "revoked",
    "S" : "suspended",
    "TO" : "terminated on time limit"
    }

def monitor(jobid):
    """
    Checks the status of a job previusly
    submitted on the cluster and returns
    relevant information
    """
    # sacct -j 1277 --long
    pstat = subprocess.Popen('sacct -Pj %s --format=jobname,jobid,state,exitcode,start,elapsed,allocnodes,nodelist,partition,cluster,timelimit' % jobid, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    outs, errs = pstat.communicate()
    jobinfo = {}
    if outs != "":
        jobinfo = convert_delimited(outs)
    elif "Unknown Job Id" in errs:
        pass
    else:
        raise Exception("Unknown squeue error %s" % errs)

    return jobinfo


def convert_delimited(outstring):
    """
    Returns the job information in the form of
    a dictionary
    """
    jobinfo = {}
    rows = outstring.split('\n')
    header = rows[0].split('|')
    data = rows[1].split('|')
    for name,value in zip(header,data):
        if name == 'State':
            if value in slurm_jobstatus:
                jobinfo['job_state'] = slurm_jobstatus[value]
            else:
                jobinfo['job_state'] = value.lower()
        else:
            jobinfo[name] = value

    return jobinfo

def run(jobfile):
    """
    Submits a specified jobfile and returns
    the jobid
    """
    p = subprocess.Popen('sbatch %s' % jobfile, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = p.communicate()
    if out == "":
        raise Exception("Jobscript %s submission failed with error %s" % (jobfile, err))

    return out.split()[-1].strip() # 'Submitted batch job ####\n'
