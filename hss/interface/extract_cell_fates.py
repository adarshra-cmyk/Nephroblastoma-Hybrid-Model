"""
Extract Cell_Fates JSON files from completed Model_Data pickle files
for all conditions that don't already have one.
"""

import os, json, pickle, glob

wdir = os.path.dirname(os.path.abspath(__file__))

def extract_fates(pickle_path, out_path):
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f, encoding='latin1')

    results = data.values()
    Cell_Fates         = {"cell_death": [], "cell_growth": [], "cell_senescence": []}
    Cell_Fates_Total   = {"cell_death": 0.0, "cell_growth": 0.0, "cell_senescence": 0.0}
    Cell_Fates_Lookup        = {"cell_death": [], "cell_growth": [], "cell_senescence": []}
    Cell_Fates_Total_Lookup  = {"cell_death": 0.0, "cell_growth": 0.0, "cell_senescence": 0.0}
    total = 0
    total_lookup = 0

    for result in results:
        for key, value in result.items():
            if not isinstance(value, dict):
                continue
            if "cell_fate" in value:
                for k, v in value["cell_fate"].items():
                    Cell_Fates[k].append(v)
                    Cell_Fates_Total[k] += v
                    total += v
            if "cell_fate_lookup" in value:
                for k, v in value["cell_fate_lookup"].items():
                    Cell_Fates_Lookup[k].append(v)
                    Cell_Fates_Total_Lookup[k] += v
                    total_lookup += v

    if total == 0 or total_lookup == 0:
        print("  WARNING: no cell fate data found in %s" % pickle_path)
        return False

    probs        = {k: float(v) / total        for k, v in Cell_Fates_Total.items()}
    probs_lookup = {k: float(v) / total_lookup for k, v in Cell_Fates_Total_Lookup.items()}

    out = {
        "Cell_Fates":                  Cell_Fates,
        "Cell_Fate_Probabilities":     probs,
        "Cell_Fates_Lookup":           Cell_Fates_Lookup,
        "Cell_Fate_Probabilities_Lookup": probs_lookup,
    }
    with open(out_path, 'w') as f:
        json.dump(out, f)
    return True


pattern = os.path.join(wdir, "Model_Data_lifer_*.pickle")
# Only match aggregated files (no trailing _<number>)
import re
pickles = sorted([
    p for p in glob.glob(pattern)
    if not re.search(r'_\d+\.pickle$', p)
])

print("Found %d aggregated Model_Data pickle files" % len(pickles))
done, skipped, failed = 0, 0, 0

for pkl in pickles:
    run_id = re.search(r'Model_Data_(lifer_.+?)\.pickle$', pkl).group(1)
    out = os.path.join(wdir, "Cell_Fates_%s.json" % run_id)
    if os.path.isfile(out):
        print("SKIP  %s (already exists)" % run_id)
        skipped += 1
        continue
    print("EXTRACT %s ..." % run_id, end=' ')
    ok = extract_fates(pkl, out)
    if ok:
        # Verify
        with open(out) as f:
            d = json.load(f)
        p = d["Cell_Fate_Probabilities_Lookup"]
        print("death=%.3f  growth=%.3f  senescence=%.3f" % (
            p["cell_death"], p["cell_growth"], p["cell_senescence"]))
        done += 1
    else:
        failed += 1

print("\nDone: %d extracted, %d skipped, %d failed" % (done, skipped, failed))
