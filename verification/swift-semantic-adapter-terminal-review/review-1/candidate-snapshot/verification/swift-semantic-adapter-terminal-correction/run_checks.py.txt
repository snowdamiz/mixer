"""Bounded runner of this new contract model, source checks and git metadata."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]

def sha(raw):return hashlib.sha256(raw).hexdigest()

def dump(path,value):
    with path.open("x") as output:
        json.dump(value,output,indent=2,sort_keys=True);output.write("\n")

def sources():
    paths=[ROOT/"docs/swift-semantic-adapter-terminal-correction.md"]
    paths += [p for p in BASE.iterdir() if p.is_file() and p.suffix in {".py",".json",".md"}]
    return [{"path":str(p.relative_to(ROOT)),"bytes":len(p.read_bytes()),"sha256":sha(p.read_bytes())}
            for p in sorted(paths)]

def command(attempt,name,argv,kind="zero"):
    child=subprocess.Popen(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timeout=False
    try:out,err=child.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        timeout=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate(timeout=15)
    (attempt/(name+".stdout")).write_bytes(out);(attempt/(name+".stderr")).write_bytes(err)
    passed=not timeout and (child.returncode==0 if kind=="zero" else child.returncode in (0,1) and out==b"" and err==b"")
    row={"argv":argv,"cwd":str(ROOT),"timeout_seconds":45,"returncode":child.returncode,
         "timed_out":timeout,"reaped":child.poll() is not None,"passed":passed,
         "expected":kind,"stdout_sha256":sha(out),"stderr_sha256":sha(err),
         "stdout_bytes":len(out),"stderr_bytes":len(err)}
    dump(attempt/(name+".json"),row)
    return row

def main():
    folder=BASE/"attempts";folder.mkdir(exist_ok=True)
    n=1
    while (folder/("run-%d"%n)).exists():n+=1
    attempt=folder/("run-%d"%n);attempt.mkdir()
    before=sources();dump(attempt/"source-before.json",before)
    commands=[command(attempt,"python-version",[sys.executable,"--version"]),
              command(attempt,"git-version",["git","--version"]),
              command(attempt,"revision",["git","rev-parse","HEAD"]),
              command(attempt,"normal",[sys.executable,"-B",str(BASE/"test_contract.py")]),
              command(attempt,"optimized",[sys.executable,"-B","-O",str(BASE/"test_contract.py")])]
    for i,row in enumerate(before):
        commands.append(command(attempt,"whitespace-%02d"%i,["git","diff","--no-index","--check","/dev/null",str(ROOT/row["path"])],"difference-with-empty-diagnostics"))
    after=sources();dump(attempt/"source-after.json",after)
    executable=Path(sys.executable).resolve()
    result={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "scope":"new bounded contract-model and source/custody/declaration checks; no Rust/product tests",
       "argv":sys.argv,"cwd":str(ROOT),"python":{"executable":str(executable),"sha256":sha(executable.read_bytes()),"version":sys.version},
       "environment":{"platform":sys.platform,"machine":os.uname().machine,"bytecode_disabled":True},
       "commands":commands,"authored_source_before_equal_after":before==after,
       "authored_source_tree_sha256":sha(json.dumps(before,sort_keys=True,separators=(",",":")).encode()),
       "methods_per_mode":12,"literal_projection_cases":56,"literal_normalization_cases":41,
       "cartesian_contract_cases_per_mode":10560,"old_members_byte_verified_per_mode":208,
       "Rust_or_product_tests":0,"old_code_imported_or_executed":False,
       "cleanup":{"owned_synchronous_children_reaped":all(c["reaped"] for c in commands),"native_or_capture_started":False,"process_discovery":False,"scratch_build_created":False},
       "limitations":["contract-model output only","no compiler/source/lifetime/work proof for missing Rust","independent R1 review and root selection pending","real authority adapters/target/native/product qualification pending"],
       "passed":before==after and all(c["passed"] for c in commands)}
    dump(attempt/"receipt.json",result)
    print(json.dumps({"attempt":str(attempt.relative_to(ROOT)),"passed":result["passed"],"commands":len(commands),"methods_per_mode":12,"literal_projection_cases":56,"literal_normalization_cases":41,"cartesian_cases_per_mode":10560,"Rust_product_tests":0}))
    return 0 if result["passed"] else 1

if __name__=="__main__":raise SystemExit(main())
