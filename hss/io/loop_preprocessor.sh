#!/bin/bash

module load anaconda3

drugs=("Control" "Dox" "Vincristine" "Actinomycin" "Dox,Vincristine" "Actinomycin,Vincristine" "Actinomycin,Dox,Vincristine")
radlevels=(0) # 5 10 15 20 25
patients=("Control" "4L3YB6" "5XIHQG" "6Z34IQ" "ECCOAH")
runname="lifer"

for p in ${patients[*]}; do
    for d in ${drugs[*]}; do
        for r in ${radlevels[*]}; do
            echo "python preprocessor.py -p $p -d $d -r $r -s $runname ../interface/Run_Info_$runname.json"
            conda run -n nephro python preprocessor.py -p $p -d $d -r $r -s $runname ../interface/Run_Info_$runname.json
        done
    done
done
