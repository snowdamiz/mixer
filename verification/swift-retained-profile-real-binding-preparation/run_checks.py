"""Bounded data/schema host checks only. No product engine workload is run."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUSTC=Path("/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc")

def identity(path):
    data=Path(path).read_bytes()
    return {"path":str(path),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}

def main():
    logs=HERE/"logs"
    logs.mkdir(exist_ok=True)
    receipts=[]
    sources={p.name:identity(p) for p in [HERE/n for n in ("actual_data_records.rs","typed_wire_proposal.rs","context_contract.py","test_context_contract.py","run_checks.py")]}
    def run(label,args,cwd=HERE):
        start=time.monotonic()
        try:
            result=subprocess.run([str(x) for x in args],cwd=cwd,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},capture_output=True,timeout=30)
        except subprocess.TimeoutExpired as error:
            result=None
            out,error_out=error.stdout or b"",error.stderr or b""
        else:
            out,error_out=result.stdout,result.stderr
        (logs/(label+".stdout")).write_bytes(out)
        (logs/(label+".stderr")).write_bytes(error_out)
        receipts.append({"label":label,"argv":[str(x) for x in args],"cwd":str(cwd),"timeout_seconds":30,"elapsed_seconds":time.monotonic()-start,"exit_code":None if result is None else result.returncode,"terminally_waited":result is not None,"stdout":identity(logs/(label+".stdout")),"stderr":identity(logs/(label+".stderr"))})
        if result is None or result.returncode!=0:
            (HERE/"command-receipts.json").write_text(json.dumps(receipts,indent=2)+"\n")
            raise SystemExit("failed:"+label)
        return out.decode()
    revision=run("source-revision",["git","rev-parse","HEAD"],ROOT).strip()
    rust_version=run("rustc-version",[RUSTC,"-Vv"])
    scratch=Path(tempfile.mkdtemp(prefix="mixer-real-binding-data-"))
    binaries=[]
    try:
        for mode,flags in (("debug",[]),("optimized",["-O"])):
            binary=scratch/("typed-data-"+mode)
            run("compile-"+mode,[RUSTC,"--edition=2021","--test",HERE/"typed_wire_proposal.rs",*flags,"-o",binary])
            binaries.append(identity(binary))
            run("typed-data-"+mode,[binary,"--test-threads=1"])
        run("context-contract",[sys.executable,"-B","-m","unittest","-v","test_context_contract.py"])
    finally:
        shutil.rmtree(scratch)
    after={name:identity(HERE/name) for name in sources}
    assert sources==after,"source changed during checks"
    (HERE/"command-receipts.json").write_text(json.dumps(receipts,indent=2)+"\n")
    report={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"unselected-contract-data-controls-pass","scope":"actual released data declarations plus proposed wire/context grammar only; no validator/cache/exporter/loader/session or semantic replay implementation executed","source_revision":revision,"source_inputs":sources,"source_inputs_sha256":hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"python":sys.version,"python_identity":identity(Path(sys.executable).resolve()),"rustc":rust_version,"rustc_identity":identity(RUSTC),"platform":platform.platform(),"binaries_measured_then_removed":binaries,"commands":len(receipts),"rust_data_tests_each_mode":14,"python_contract_methods":12,"scratch_removed":not scratch.exists(),"producer_one_shot_scripts_rerun":False,"native_UI_capture_process_inventory_used":False,"canonical_or_index_mutation":False,"real_binding_semantic_replay_native_OTA_GA_accepted":False}
    (HERE/"receipt.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("status","commands","rust_data_tests_each_mode","python_contract_methods","scratch_removed")}))

if __name__=="__main__":main()
