"""v2 guarded data-only source helper. No product, tool or custody imports."""
import sys
sys.dont_write_bytecode = True
if not (sys.flags.isolated == 1 and sys.flags.no_site == 1):
    raise RuntimeError("Run with -I -B -S")
def source_guard(event,args):
    if event.startswith(("subprocess","socket","ctypes")) or event in (
        "os.system","os.posix_spawn","os.posix_spawnp","os.fork","os.forkpty","os.kill","os.killpg","os.exec","pty.spawn"):
        raise RuntimeError("Data-only helper denied "+event)
    if event == "import" and args[0].split(".")[0] not in sys.stdlib_module_names:
        raise RuntimeError("Non-stdlib import denied "+args[0])
sys.addaudithook(source_guard)
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import time

HERE = Path(__file__).resolve().parent

def checked_contract():
    deadline = time.monotonic()+30
    def check():
        if time.monotonic() >= deadline:
            raise RuntimeError("Data-contract bootstrap wall deadline exhausted")
    check()
    if HERE.resolve(strict=True) != HERE or not stat.S_ISDIR(HERE.lstat().st_mode):
        raise RuntimeError("Canonical flat v2 packet required")
    seal_path = HERE/"seal.json"
    if not stat.S_ISREG(seal_path.lstat().st_mode) or seal_path.stat().st_size > 65536:
        raise RuntimeError("Bounded ordinary v2 seal required")
    seal = json.loads(seal_path.read_bytes())
    expected = {row["path"]:row for row in seal["members"]}
    if len(expected) != len(seal["members"]) or not 1 <= len(expected) <= 63:
        raise RuntimeError("Finite unique flat v2 seal required")
    observed,total = set(),0
    with os.scandir(HERE) as entries:
        for entry in entries:
            check()
            observed.add(entry.name)
            if len(observed) > 64:
                raise RuntimeError("V2 packet node bound exceeded")
            path = HERE/entry.name
            status = path.lstat()
            total += status.st_size
            if not stat.S_ISREG(status.st_mode) or status.st_size > 524288 or total > 1048576:
                raise RuntimeError("V2 packet topology/byte bound exceeded")
            if entry.name != "seal.json":
                row = expected.get(entry.name)
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda:stream.read(1048576),b""):
                        check(); digest.update(chunk)
                if row is None or status.st_size != row["bytes"] or digest.hexdigest() != row["sha256"]:
                    raise RuntimeError("Sealed v2 helper/source changed")
    if observed != set(expected)|{"seal.json"}:
        raise RuntimeError("Sealed v2 namespace changed")
    path = HERE/"source_contract.py"
    spec = importlib.util.spec_from_file_location("pair7_v2_pure_contract",path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    check()
    return module

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("stage","post"):
        raise RuntimeError("stage or post required")
    c = checked_contract()
    budget = c.WallBudget(60,15)
    context = c.ci_identity(dict(os.environ),"snapshot")
    root = c.ordinary_root(Path(os.environ["GITHUB_WORKSPACE"]))
    c.need(HERE == root/"verification/pair7-java-compile-ci-proposal/v2","Exact nested v2 packet required")
    manifest,manifest_id = c.read_json(c.ordinary_file(HERE,"snapshot-source-manifest.json"),65536,budget.check)
    verified = c.source_manifest(root,manifest,sys.argv[1] == "post",budget.check)
    overlay = manifest["overlay"]
    source = c.ordinary_file(root,overlay["source"])
    source_id = c.file_identity(source,1048576,budget.check)
    c.need(source_id["sha256"] == overlay["sha256"],"Exact producer test bytes required")
    target_name = c.relative_name(overlay["target"])
    c.need(target_name == "cli/Tests/MixerBuildTests/Pair7JavaSnapshotExportTests.swift","Exact disposable overlay target required")
    target = root/target_name
    c.ordinary_root(target.parent)
    temp = c.ordinary_root(Path(os.environ["RUNNER_TEMP"]))
    evidence = temp/("pair7-java-source-"+context["run_id"]+"-1")
    if sys.argv[1] == "stage":
        evidence.mkdir(exist_ok=False)
        descriptor = os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(descriptor,"wb") as stream:
            stream.write(source.read_bytes())
    else:
        c.need(c.file_identity(c.ordinary_file(root,target_name),1048576,budget.check) == source_id,"Staged overlay changed")
    budget.check()
    payload = {"schema":2,"status":"exact-source-bound-data-only","mode":sys.argv[1],
               "context":context,"python":sys.version,"argv":sys.argv,
               "manifest":manifest_id,"source_members":manifest["members"],"verified":verified,
               "overlay":overlay,"producer":source_id,"wall":budget.observation(),
               "child_or_product_execution":False,
               "cleanup":"Only the selected disposable test overlay and CI-owned source receipts are written. No child started."}
    data = (json.dumps(payload,sort_keys=True,indent=2)+"\n").encode()
    c.need(len(data) <= 131072,"Source receipt byte bound")
    descriptor = os.open(evidence/(sys.argv[1]+".json"),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,"wb") as stream:
        stream.write(data)
    budget.check()
if __name__ == "__main__":
    main()
