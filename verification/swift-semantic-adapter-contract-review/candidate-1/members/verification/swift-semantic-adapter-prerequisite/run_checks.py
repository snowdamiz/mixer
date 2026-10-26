"""Bounded own-source check runner. Executes only new checks and git metadata."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def dump(path, value):
    with path.open("x") as out:
        json.dump(value, out, indent=2, sort_keys=True)
        out.write("\n")

def source_rows():
    paths = [ROOT / "docs/swift-semantic-adapter-prerequisite.md"]
    paths += [p for p in BASE.iterdir() if p.is_file() and p.suffix in {".py", ".json", ".md"}]
    rows = []
    for path in sorted(paths):
        raw = path.read_bytes()
        rows.append({"path":str(path.relative_to(ROOT)),"bytes":len(raw),"sha256":digest(raw)})
    return rows

def execute(attempt, name, argv, expected):
    child = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate(timeout=15)
    (attempt / (name+".stdout")).write_bytes(stdout)
    (attempt / (name+".stderr")).write_bytes(stderr)
    row = {"argv":argv,"cwd":str(ROOT),"timeout_seconds":45,
           "returncode":child.returncode,"timed_out":timed_out,
           "stdout_bytes":len(stdout),"stderr_bytes":len(stderr),
           "stdout_sha256":digest(stdout),"stderr_sha256":digest(stderr),
           "reaped":child.poll() is not None,"expected":expected}
    if expected == "zero":
        row["passed"] = not timed_out and child.returncode == 0
    else:
        row["passed"] = not timed_out and child.returncode in (0,1) and stdout == b"" and stderr == b""
    dump(attempt / (name+".json"), row)
    return row

def main():
    attempts = BASE / "commands"
    attempts.mkdir(exist_ok=True)
    number = 1
    while (attempts / ("run-%d" % number)).exists():
        number += 1
    attempt = attempts / ("run-%d" % number)
    attempt.mkdir()
    before = source_rows()
    dump(attempt / "source-before.json", before)
    commands = []
    commands.append(execute(attempt,"python-version",[sys.executable,"--version"],"zero"))
    commands.append(execute(attempt,"git-version",["git","--version"],"zero"))
    commands.append(execute(attempt,"revision",["git","rev-parse","HEAD"],"zero"))
    script = str(BASE / "verify_proposal.py")
    commands.append(execute(attempt,"checks-normal",[sys.executable,"-B",script],"zero"))
    commands.append(execute(attempt,"checks-optimized",[sys.executable,"-B","-O",script],"zero"))
    authored = [ROOT/"docs/swift-semantic-adapter-prerequisite.md"]
    authored += [p for p in BASE.iterdir() if p.is_file() and p.suffix in {".py",".md",".json"}]
    for index,path in enumerate(sorted(authored)):
        commands.append(execute(attempt,"whitespace-%02d"%index,
                        ["git","diff","--no-index","--check","/dev/null",str(path)],
                        "zero-or-difference-with-empty-diagnostics"))
    after = source_rows()
    dump(attempt / "source-after.json", after)
    inputs = json.loads((BASE/"input-manifest.json").read_text())["members"]
    inputs += json.loads((BASE/"supplemental-inputs.json").read_text())["members"]
    tree = "".join("%s\t%d\t%s\n"%(r["path"],r["bytes"],r["sha256"])
                   for r in sorted(inputs,key=lambda r:r["path"]))
    executable = Path(sys.executable).resolve()
    git = Path(shutil.which("git")).resolve()
    receipt = {"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "scope":"New finite source/custody/declaration/arithmetic checks only; not semantic execution",
       "argv":sys.argv,"cwd":str(ROOT),"python":{"path":str(executable),"sha256":digest(executable.read_bytes()),"version":sys.version},
       "git":{"path":str(git),"sha256":digest(git.read_bytes())},
       "environment":{"platform":sys.platform,"machine":os.uname().machine,"bytecode_disabled":True},
       "source_rows_before_equal_after":before==after,
       "consulted_source_members":len(inputs),"consulted_source_tree_sha256":digest(tree.encode()),
       "authored_source_tree_sha256":digest(json.dumps(before,sort_keys=True,separators=(",",":")).encode()),
       "commands":commands,"source_checks_per_mode":12,"semantic_tests_executed":0,
       "source_checks_are_not_future_52_design_passes":True,
       "cleanup":{"all_owned_synchronous_children_reaped":all(x["reaped"] for x in commands),
                  "scratch_builds_created":False,"native_or_capture_started":False,"process_discovery":False,"old_harness_import_or_execution":False},
       "remaining":["independent contract/source accounting review","root selection","actual Rust semantic source/tests/layouts/caller lifetime reconciliation","real authority adapters","target/native/device and all product gates"],
       "passed":before==after and all(x["passed"] for x in commands)}
    dump(attempt/"receipt.json",receipt)
    print(json.dumps({"attempt":str(attempt.relative_to(ROOT)),"passed":receipt["passed"],"commands":len(commands),"source_checks_per_mode":12,"semantic_tests_executed":0,"consulted_source_tree_sha256":receipt["consulted_source_tree_sha256"]}))
    return 0 if receipt["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
