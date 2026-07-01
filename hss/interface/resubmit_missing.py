#!/usr/bin/env python3
"""Submit missing replicates that have no .out or .pickle output."""

import os
import json
import subprocess
from string import Template

IFACE = os.path.dirname(os.path.abspath(__file__))

slurm_template = Template("""#!/bin/bash
#SBATCH --job-name=${jobname}
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=adarshra@seas.upenn.edu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=12:00:00
#SBATCH --account=mcb200052p
#SBATCH --partition=RM-shared
#SBATCH -o ${jobname}.out
#SBATCH -e ${jobname}.err

set -e
cd $$SLURM_SUBMIT_DIR
export PATH=/jet/home/aramamur/bin/Copasi/COPASI-4.34.251-Linux-64bit/bin:$$PATH
PYTHON=/jet/home/aramamur/.conda/envs/nephro/bin/python
echo "Job ${jobname} started"
startime=$$(date +%s)
$$PYTHON hybrid_run.py ${argfile} ${modelfile}
endtime=$$(date +%s)
runtime=$$(( $$endtime - $$startime ))
date -d@$$runtime -u +%%H:%%M:%%S > ${jobname}.time
echo "Job ${jobname} ended"
""")

conditions = [
    "4L3YB6_Actinomycin", "4L3YB6_Actinomycin_Dox_Vincristine", "4L3YB6_Actinomycin_Vincristine",
    "4L3YB6_Dox", "4L3YB6_Dox_Vincristine", "4L3YB6_Vincristine",
    "5XIHQG_Actinomycin", "5XIHQG_Actinomycin_Dox_Vincristine", "5XIHQG_Actinomycin_Vincristine",
    "5XIHQG_Control", "5XIHQG_Dox", "5XIHQG_Dox_Vincristine", "5XIHQG_Vincristine",
    "6Z34IQ_Actinomycin", "6Z34IQ_Actinomycin_Dox_Vincristine", "6Z34IQ_Actinomycin_Vincristine",
    "6Z34IQ_Control", "6Z34IQ_Dox", "6Z34IQ_Dox_Vincristine", "6Z34IQ_Vincristine",
    "Control_Actinomycin_Dox_Vincristine",
    "ECCOAH_Actinomycin", "ECCOAH_Actinomycin_Dox_Vincristine", "ECCOAH_Actinomycin_Vincristine",
    "ECCOAH_Control", "ECCOAH_Dox", "ECCOAH_Dox_Vincristine", "ECCOAH_Vincristine",
]

completed_out = set(
    f.replace("lifer_", "").replace(".out", "")
    for f in os.listdir(IFACE) if f.endswith(".out")
)
completed_pkl = set(
    f.replace("Model_Data_lifer_", "").replace(".pickle", "")
    for f in os.listdir(IFACE)
    if f.startswith("Model_Data_lifer_") and f.count("_") > 3
)

submitted = []
skipped = []

for cond in conditions:
    sweep_id = f"lifer_{cond}"
    sweepfile = os.path.join(IFACE, f"Sweepfile_{sweep_id}.json")
    modelfile = f"Run_Info_{sweep_id}.json"

    with open(sweepfile) as fp:
        sweepdata = json.load(fp)

    for i in range(16):
        key = f"{cond}_{i}"
        if key in completed_out or key in completed_pkl:
            continue

        elem_id = f"lifer_{key}"
        argfile = f"Arguments_{elem_id}.json"
        jobfile = f"Jobfile_{elem_id}.sh"
        args = sweepdata[str(i)]["args"]

        # Write Arguments JSON
        with open(os.path.join(IFACE, argfile), "w") as fp:
            json.dump({"sweep_id": elem_id, "args": args}, fp)

        # Write Jobfile
        script = slurm_template.substitute(
            jobname=elem_id,
            argfile=argfile,
            modelfile=modelfile,
        )
        jobfile_path = os.path.join(IFACE, jobfile)
        with open(jobfile_path, "w") as fp:
            fp.write(script)

        # Submit
        result = subprocess.run(
            ["sbatch", jobfile],
            cwd=IFACE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        result.stdout = result.stdout.decode()
        result.stderr = result.stderr.decode()
        if result.returncode == 0:
            jobid = result.stdout.strip().split()[-1]
            print(f"Submitted {elem_id} -> job {jobid}")
            submitted.append((elem_id, jobid))
        else:
            print(f"FAILED {elem_id}: {result.stderr.strip()}")
            skipped.append(elem_id)

print(f"\nDone: {len(submitted)} submitted, {len(skipped)} failed.")
