#!/usr/bin/env python3
"""Submit one SLURM job per (patient, drug) memory-OFF condition.

Each job runs run_no_memory.py <patient> <drug> <num_seeds>, which
simulates num_seeds replicates in parallel (memory OFF / updatemodel=False)
and writes Cell_Fates_nomem_lifer_<patient>_<drug>.json.
"""

import os
import subprocess
from string import Template

IFACE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(IFACE))

PATIENT_ARM = "4L3YB6"
PATIENTS = ["Control", PATIENT_ARM]
DRUGS = [
    "Control", "Actinomycin", "Dox", "Actinomycin_Dox",
    "Vincristine", "Dox_Vincristine", "Actinomycin_Vincristine",
    "Actinomycin_Dox_Vincristine",
]
NUM_SEEDS = 100
NUM_CPUS  = 32   # workers per job; RM-shared cap is 64

slurm_template = Template("""#!/bin/bash
#SBATCH --job-name=${jobname}
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=adarshra@seas.upenn.edu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=${num_cpus}
#SBATCH --time=04:00:00
#SBATCH --account=mcb200052p
#SBATCH --partition=RM-shared
#SBATCH -o ${jobname}.out
#SBATCH -e ${jobname}.err

set -e
cd ${root}
export PATH=/jet/home/aramamur/bin/Copasi/COPASI-4.34.251-Linux-64bit/bin:$$PATH
PYTHON=/jet/home/aramamur/.conda/envs/nephro/bin/python
echo "Job ${jobname} started on $$(hostname) at $$(date)"
startime=$$(date +%s)
$$PYTHON run_no_memory.py ${patient} ${drug} ${num_seeds}
endtime=$$(date +%s)
runtime=$$(( $$endtime - $$startime ))
date -d@$$runtime -u +%%H:%%M:%%S > ${jobname}.time
echo "Job ${jobname} ended at $$(date)"
""")

submitted = []
failed = []

for patient in PATIENTS:
    for drug in DRUGS:
        jobname = "nomem_%s_%s" % (patient, drug)

        # Drop any stale output so it gets regenerated with the full,
        # consistent seed count.
        outfile = os.path.join(IFACE, "Cell_Fates_nomem_lifer_%s_%s.json" % (patient, drug))
        if os.path.exists(outfile):
            os.remove(outfile)

        script = slurm_template.substitute(
            jobname=jobname,
            patient=patient,
            drug=drug,
            num_seeds=NUM_SEEDS,
            num_cpus=NUM_CPUS,
            root=ROOT,
        )
        jobfile_path = os.path.join(IFACE, "Jobfile_%s.sh" % jobname)
        with open(jobfile_path, "w") as fp:
            fp.write(script)

        result = subprocess.run(
            ["sbatch", jobfile_path],
            cwd=IFACE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out = result.stdout.decode().strip()
        err = result.stderr.decode().strip()
        if result.returncode == 0:
            jobid = out.split()[-1]
            print("Submitted %s -> job %s" % (jobname, jobid))
            submitted.append((jobname, jobid))
        else:
            print("FAILED %s: %s" % (jobname, err))
            failed.append(jobname)

print("\nDone: %d submitted, %d failed." % (len(submitted), len(failed)))
