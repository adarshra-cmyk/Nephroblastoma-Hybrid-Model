#!/bin/bash

#source /mnt/io1/compbio/home/aghos/workdir/hybrid_systems_simulator/pyenv/bin/activate 

for i in $(seq $2)
do
    sleep $1
    date
    python batch_setup.py $3
done

#deactivate
