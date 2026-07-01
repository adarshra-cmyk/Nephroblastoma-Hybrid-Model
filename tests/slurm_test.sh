#!/bin/bash
#SBATCH --job-name=serial_job_test    # Job name
#SBATCH --mail-type=END,FAIL          # Mail events (NONE, BEGIN, END, FAIL, ALL)
#SBATCH --mail-user=linzi12@gmail.com     # Where to send mail	
#SBATCH --ntasks=1                    # Run on a single CPU
#SBATCH --mem=1gb                     # Job memory request
#SBATCH --time=00:05:00               # Time limit hrs:min:sec
#SBATCH -o %j.out   # Standard output
#SBATCH -e %j.err   # Standard error

pwd; hostname; date

#module load python

echo "Running plot script on a single CPU core"

#python /data/training/SLURM/plot_template.py

date
