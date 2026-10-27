"""Closed child commands,15s each, streams preserved regardless of result."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
logs=ROOT/"logs";logs.mkdir(exist_ok=True)
records=[]
def run(argv,cwd,name,expected):
    start=time.monotonic()
    with (logs/(name+".stdout")).open("wb") as out,(logs/(name+".stderr")).open("wb") as err:
        result=subprocess.run([os.path.realpath(sys.executable),"-B",*argv],cwd=cwd,stdout=out,stderr=err,timeout=15,env={"LC_ALL":"C","LANG":"C","PYTHONDONTWRITEBYTECODE":"1"})
    record={"argv":[os.path.realpath(sys.executable),"-B",*argv],"cwd":str(cwd),"name":name,"exit_code":result.returncode,"expected_exit":expected,"elapsed_seconds":time.monotonic()-start,"terminal_reaped":True}
    for stream in ("stdout","stderr"):
        path=logs/(name+"."+stream)
        record[stream]=str(path.relative_to(ROOT));record[stream+"_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    records.append(record)
    if result.returncode!=expected:print("UNEXPECTED",name,result.returncode,flush=True)
    return result.returncode

names=("test_closed_retained_wrapper_cannot_reauthorize_reused_descriptor","test_close_failure_still_accounts_for_and_closes_remaining_owned_descriptors","test_preclose_error_does_not_forget_known_open_descriptor")
for variant in ("old","corrected"):
    run(["test_preparation.py"],ROOT/"replay"/variant/"replay",variant+"-producer",0)
    for i,name in enumerate(names):
        run([str(ROOT/"replay/run_unchanged_witness.py"),variant,name],ROOT/"replay",variant+"-raw-"+str(i),0 if variant=="corrected" and i==0 else 1)
for case in ("lifecycle","multi-close","nested-primary","nested-result","number-reuse","stdio-close"):
    run([str(ROOT/"independent_case.py"),case],ROOT,"independent-"+case,1 if case=="stdio-close" else 0)
scratch=list((ROOT/"owned-scratch").iterdir())
assert not scratch
for variant in ("old","corrected"):
    assert not list((ROOT/"replay"/variant/"replay/owned-scratch").iterdir())
(ROOT/"command-receipts.json").write_text(json.dumps({"schema":1,"commands":records,"independent_cases":6,"independent_pass":5,"independent_required_failure":1,"raw_failures_remain_failures":True,"owned_scratch_entries_final":0,"actual_OS_close_ambiguity_resolution":False},indent=2,sort_keys=True)+"\n")
assert all(r["exit_code"]==r["expected_exit"] for r in records)
print(json.dumps({"commands":len(records),"producer_methods_each":26,"independent_pass":5,"independent_required_failure":1,"scratch_final":0},sort_keys=True))
