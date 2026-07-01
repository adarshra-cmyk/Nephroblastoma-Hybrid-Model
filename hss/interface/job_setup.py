#!/usr/bin/env python

"""
This script provides a class [SimulationBatch](#job_setup.SimulationBatch) that can be used
to setup, run, update and collect data using a PBS or SLURM based cluster
like compbio. It receives information about a specific sweep run
from an input file and for each of the sweep elements it sets up
jobs and submits them and monitors the jobs. It updates the run
status when it changes.

Example Run
-----------
Although this script can be run as standalone by running it
directly like

    $ python job_setup.py

However the preferred way of using this is as a module and importing
the `SimulationBatch` class.

    from job_setup import SimulationBatch

Then one should work with instances of the class to setup and
submit runs, update and cleanup.

Input Files
-----------
The necessary input files are explained in the documentation for
the `SimulationBatch` class.

Output Data
-----------
The class `SimulationBatch` has different methods that write
different temporary files per job. These are

- `<sim-id>.status` A status file indicating the completion status
of a particular job.
- A file that stores the arguments that will be used for the
`hybrid_run.py` script.
- Updated sweep information

Dependencies
------------

  - Python >= 2.7
  - Local modules [`pbsjobs`](../hss/utils/pbsjobs.py), [`slurmjobs`](../hss/utils/slurmjobs.py)

TODO
----

  - Generalize the script to work with other queue managers.
  - Decorate some of the classes for better logging.
"""

import os, sys, json, shutil
import pickle, copy, glob
import itertools, random
from string import Template
from datetime import datetime, date

script_dirs = ["solver", "interface", "visualization", "utils", "../tests"]
'''The list of directories which are added to system path for importing the modules.'''

for dirs in script_dirs:
    path = os.path.abspath("../%s" % dirs)
    if path not in sys.path:
        sys.path.append(path)

import pbsjobs
import slurmjobs

pbs_script = """#!/bin/bash
#PBS -l nodes=$node:ppn=$ppn,walltime=$walltime
#PBS -q opterons
#PBS -m n
#PBS -N $jobname
#PBS -o $jobname.out
#PBS -e $jobname.err
cd $PBS_O_WORKDIR
set -e
# conda activate
echo "Job $jobname started"
startime=$(date +%s)
python hybrid_run.py $argfile $modelfile
endtime=$(date +%s)
runtime=$(( $endtime - $startime ))
date -d@$runtime -u +%H:%M:%S > $jobname.time
echo "Job $jobname ended"
# conda deactivate
"""
'''A template string for the job submission scripts with PBS directives. Uses the syntax specified by [string.Template](https://docs.python.org/2/library/string.html#template-strings) class.'''

slurm_script = """#!/bin/bash
#SBATCH --job-name=$jobname
#SBATCH --mail-type=$mailtype
#SBATCH --mail-user=$mailuser
#SBATCH --nodes=$nodes
#SBATCH --ntasks=$ntasks
#SBATCH --cpus-per-task=$cpuspertask
#SBATCH --time=$time
#SBATCH --account=mcb200052p
#SBATCH --partition=RM-shared
#SBATCH -o $jobname.out
#SBATCH -e $jobname.err

set -e
cd $$SLURM_SUBMIT_DIR
export PATH=/jet/home/aramamur/bin/Copasi/COPASI-4.34.251-Linux-64bit/bin:$$PATH
PYTHON=/jet/home/aramamur/.conda/envs/nephro/bin/python
echo "Job $jobname started"
startime=$$(date +%s)
$$PYTHON hybrid_run.py $argfile $modelfile
endtime=$$(date +%s)
runtime=$$(( $$endtime - $$startime ))
date -d@$$runtime -u +%H:%M:%S > $jobname.time
echo "Job $jobname ended"
"""
'''A template string for the job submission scripts with SLURM directives. Uses the syntax specified by [string.Template](https://docs.python.org/2/library/string.html#template-strings) class.'''


class SimulationBatch:
    """
    Class managing the run, update and collection
    of data from various simulations.

    This class provides methods for setting up and running specific
    jobs, updating the status of different jobs as "submitted",
    "completed", "pending" etc.
    """

    def __init__(self, sweep_id, sweepfile, jobfile, modelfile, cluster_manager="slurm"):

        self.sweep_id = sweep_id
        '''Id of the sweep element made up of patient id and specific drug combination'''
        self.modelfile = modelfile
        '''Name of the boolean model file containing details about the node initial status and base values.'''
        self.datafile = "Model_Data_%s.pickle" % sweep_id
        '''The name of the .pickle file containing the data for particular sweep elements.'''
        self.cluster_manager = cluster_manager
        '''Type of cluster manager. Currently PBS and SLURM are supported.'''

        with open(sweepfile) as fp: self.sweepdata = json.load(fp)
        with open(jobfile) as fp: self.jobdata = json.load(fp)
        if self.cluster_manager == "pbs":
            self.jobscript = Template(pbs_script).safe_substitute(self.jobdata)
            self.jobscript = Template(self.jobscript)
        if self.cluster_manager == "slurm":
            self.jobscript = Template(slurm_script).safe_substitute(self.jobdata)
            self.jobscript = Template(self.jobscript)


    def update(self, initial_run=False):
        """
        Sets up jobs for a particular list of sweep elements OR
        updates the status of already running jobs.

        Parameters
        ----------
        - `initial_run` : `bool` Flag to specify if the sweep
        elements need to be setup for the first time or not
        (default - False)
        """
        for key, value in sorted(self.sweepdata.items(), key = lambda x : int(x[0])):
            sweep_elem_id = self.sweep_id + "_" + key
            if value["status"] == "not submitted":
                self.sweepdata[key]["argfile"] = "Arguments_%s.json" % sweep_elem_id
                jobstring = self.jobscript.safe_substitute(jobname = sweep_elem_id, argfile = self.sweepdata[key]["argfile"], modelfile = self.modelfile)
                self.sweepdata[key]["jobstring"] = jobstring
                self.sweepdata[key]["status"] = "ready"
            elif value["status"] == "ready" :
                self.run(key)
                self.sweepdata[key]["status"] = "submitted"
            else:
                if self.cluster_manager == "pbs":
                    jobinfo = pbsjobs.monitor(self.sweepdata[key]["jobid"])
                elif self.cluster_manager == "slurm":
                    jobinfo = slurmjobs.monitor(self.sweepdata[key]["jobid"])

                if jobinfo != {} and jobinfo["job_state"] not in ["completed","exiting"]:
                    self.sweepdata[key]["jobinfo"] = jobinfo
                    self.sweepdata[key]["status"] = jobinfo["job_state"]
                else:
                    try:
                        self.sweepdata[key]["outfile"] = "%s.out" % sweep_elem_id
                        with open(self.sweepdata[key]["outfile"]) as fp: scriptout = fp.read()
                        if "Job %s ended" % sweep_elem_id in scriptout:
                            self.sweepdata[key]["status"] = "completed"
                            self.sweepdata[key]["scriptout"] = scriptout
                            self.sweepdata[key]["timefile"] = "%s.time" % sweep_elem_id
                            with open(self.sweepdata[key]["timefile"]) as fp: runtime = fp.read()
                            if "jobinfo" not in self.sweepdata[key].keys():
                                self.sweepdata[key]["jobinfo"] = {}
                            self.sweepdata[key]["jobinfo"]["runtime"] = runtime.strip()
                            self.sweepdata[key]["errfile"] = "%s.err" % sweep_elem_id
                            if os.path.isfile(self.sweepdata[key]["errfile"]):
                                with open(self.sweepdata[key]["errfile"]) as fp: self.sweepdata[key]["errmsg"] = fp.read().strip()
                            self.collect(key)
                            self.cleanup(key)
                        elif self.sweepdata[key]["status"] not in ["completed", "exiting"]:
                            self.sweepdata[key]["status"] = "failed"
                        else:
                            self.sweepdata[key]["failure_message"] = "Job status found to be %s" % self.sweepdata[key]["status"]
                    except IOError:
                        pass

                    if self.sweepdata[key]["status"] == "failed":
                        try:
                            with open("%s.err" % sweep_elem_id) as fp:
                                self.sweepdata[key]["failure_message"] = fp.read()
                            self.sweepdata[key]["errfile"] = "%s.err" % sweep_elem_id
                        except IOError:
                            self.sweepdata[key]["failure_message"] = "Run error, errorfile not foundation"
                try:
                    self.printjob(key)
                except Exception as exc:
                    print "Printing job %s failed, error error %s: %s" % (key, exc.__class__.__name__, exc.message)

        if len([ key for key in self.sweepdata if self.sweepdata[key]["status"] == "completed" ]) == len(self.sweepdata.keys()):
            self.batchstatus = "complete"
            with open(self.sweep_id + ".status", "w") as fp: fp.write(self.batchstatus)


    def run(self, num):
        """
        Runs a specified job using the [`run`](pbsjobs.run, slurmjobs.run)
        function.

        Parameters
        ----------
        - `num` : `int` The job number.
        """

        sweep_elem_id = self.sweep_id + "_" + num
        with open(self.sweepdata[num]["argfile"], "w") as fp: json.dump({ "args" : self.sweepdata[num]["args"], "sweep_id" : sweep_elem_id}, fp)
        self.sweepdata[num]["jobfile"] = "Jobfile_%s.sh" % sweep_elem_id
        with open(self.sweepdata[num]["jobfile"], "w") as fp: fp.write(self.sweepdata[num]["jobstring"])
        if self.cluster_manager == "pbs":
            self.sweepdata[num]["jobid"] = pbsjobs.run(self.sweepdata[num]["jobfile"])
        if self.cluster_manager == "slurm":
            self.sweepdata[num]["jobid"] = slurmjobs.run(self.sweepdata[num]["jobfile"])

    def collect(self, num):
        """
        Collects data for a specified job

        Parameters
        ----------
        `num` : `int` Number of specified jobs.
        """
        sweep_elem_id = self.sweep_id + "_" + num
        self.sweepdata[num]["datafile"] = "Model_Data_%s.pickle" % sweep_elem_id
        with open(self.sweepdata[num]["datafile"]) as fp: model_data = pickle.load(fp)
        if os.path.isfile(self.datafile):
            with open(self.datafile) as fp: combined_data = pickle.load(fp)
        else:
            combined_data = {}
        combined_data[num] = model_data
        with open(self.datafile, "wb") as fp: pickle.dump(combined_data, fp)

    def cleanup(self, num, backup=False):
        """
        Cleans up the directory by removing tempfiles generated
        for a specific job.

        Parameters
        ----------
        - `num` : `int` The number of the job.
        - `backup` : `bool` A flag indicating whether backups need
        to be made for the temporary files.
        """
        filekeys = ["argfile","datafile","jobfile","outfile","errfile","timefile"]
        datafiles = glob.glob("Sim_Data_%s_%s_*.pickle" % (self.sweep_id, str(num)))
        if backup:
            self.backupdir = "Backup_%s" % self.sweep_id
            Make_Directory(self.backupdir)
            for key in filekeys:
                if key in self.sweepdata[num] and os.path.isfile(self.sweepdata[num][key]):
                    try:
                        shutil.move(self.sweepdata[num][key], os.path.join(self.backupdir))
                    except shutil.Error:
                        os.remove(os.path.join(self.backupdir, seld.sweepdata[num][key]))
                        shutil.move(self.sweepdata[num][key], os.path.join(self.backupdir))
                    except Exception:
                        pass
        else:
            for key in filekeys:
                if key in self.sweepdata[num] and os.path.isfile(self.sweepdata[num][key]):
                    os.remove(self.sweepdata[num][key])

        for elem in datafiles:
            try:
                shutil.move(elem, "Temp_Data")
            except shutil.Error:
                os.remove(os.path.join("Temp_Data", elem))
                shutil.move(elem, "Temp_Data")
            except Exception:
                pass

    def write(self, sweepfile):
        """
        Writes the (updated) information about sweeps in a json
        file.
        """
        with open(sweepfile, "w") as fp: json.dump(self.sweepdata, fp)

    def printjob(self, num):
        """
        Prints the job id by getting the recent
        job status.

        Parameters
        ----------
        - `num` : `int` Number of the job.
        """

        jobinfo = self.sweepdata[num]["jobinfo"]

        if self.cluster_manager == 'pbs':
            if self.sweepdata[num]["status"] == "queued":
                print "Job %s (Job id: %s) is queued in %s since %s" % (jobinfo["Job_Name"], jobinfo["Job_Id"], jobinfo["queue"], jobinfo["qtime"])
            elif self.sweepdata[num]["status"] == "running":
                print "Job %s (Job id: %s) is running in %s, queue %s, runtime %s, time remaining = %s" % (jobinfo["Job_Name"],
                      jobinfo["Job_Id"], jobinfo["exec_host"], jobinfo["queue"], jobinfo["resources_used"]["walltime"],
                      jobinfo["Walltime"]["Remaining"])
            elif self.sweepdata[num]["status"] == "failed":
                print "Job %s (Job Id: %s) failed, error message is:\n%s" % (jobinfo["Job_Name"], jobinfo["Job_Id"], self.sweepdata[num]["failure_message"])
            elif self.sweepdata[num]["status"] == "completed":
                print "Job %s (Job Id: %s) completed, total duration is %s, " % (jobinfo["Job_Name"], jobinfo["Job_Id"], jobinfo["runtime"])
            else:
                print "Job %s (Job Id: %s) failed, unknown failure" % (jobinfo["Job_Name"], jobinfo["Job_Id"])

        elif self.cluster_manager == 'slurm':
            print 'hello'
            jobname, jobid, start, runtime, timelimit, queue, cluster = [
                jobinfo[i] for i in ['JobName', 'JobID', 'Start', 'Elapsed', 'Timelimit', 'Partition', 'Cluster']]
            if self.sweepdata[num]["status"] == "queued":
                print "Job %s (Job id: %s) is queued in %s since %s" % (jobname, jobid, queue, start)
            elif self.sweepdata[num]["status"] == "running":
                print "Job %s (Job id: %s) is running in %s, queue %s, runtime %s, time limit = %s" % (jobname, jobid, cluster, queue, runtime, timelimit)
            elif self.sweepdata[num]["status"] == "failed":
                print "Job %s (Job Id: %s) failed, error message is:\n%s" % (jobname, jobid, self.sweepdata[num]["failure_message"])
            elif self.sweepdata[num]["status"] == "completed":
                print "Job %s (Job Id: %s) completed, total duration is %s, " % (jobname, jobid, elapsed)
            else:
                print "Job %s (Job Id: %s) failed, unknown failure" % (jobname, jobid)


if __name__ == '__main__':

    sweep_id = "shorttest_Control_Control"
    sweepfile = "Sweepfile_%s.json" % sweep_id
    jobfile = "Slurm_Setup.json" # "Pbs_Setup.json"
    modelfile = "Run_Info_%s.json" % sweep_id
    run_mode = "update"

    batch = SimulationBatch(sweep_id, sweepfile, jobfile, modelfile)
    if run_mode == "initial":
        batch.update(initial_run=True)
        #batch.run()
    elif run_mode == "update":
        batch.update()
        #batch.run()
        # batch.collect()
    # else:
    #     batch.cleanup()
