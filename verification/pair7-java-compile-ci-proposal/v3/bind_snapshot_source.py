"""v3 guarded data-only source helper. No product, tool or custody imports."""
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

class Refusal(RuntimeError):
    pass

def need(value, message):
    if not value:
        raise Refusal(message)

def stat_identity(value):
    return (value.st_dev,value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns)

def bounded_file(path, maximum, check=lambda:None, retain=False):
    """One nofollow, nonblocking descriptor; at most maximum+1 bytes are read."""
    need(type(maximum) is int and maximum >= 0, "Finite nonnegative byte cap required")
    path = Path(path)
    check()
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "Ordinary bounded file required")
    digest,total,chunks = hashlib.sha256(),0,[]
    descriptor = os.open(path,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor,"rb") as stream:
        opened = os.fstat(stream.fileno())
        need(stat.S_ISREG(opened.st_mode) and stat_identity(opened) == stat_identity(before),
             "File changed before nofollow open")
        while True:
            check()
            chunk = stream.read(min(1048576,maximum-total+1))
            if not chunk: break
            total += len(chunk)
            need(total <= maximum,"File grew beyond byte bound")
            digest.update(chunk)
            if retain: chunks.append(chunk)
        check()
        need(stat_identity(os.fstat(stream.fileno())) == stat_identity(before),
             "File descriptor changed during bounded read")
    check()
    need(stat_identity(path.lstat()) == stat_identity(before) and total == before.st_size,
         "File path changed during bounded read")
    return (b"".join(chunks) if retain else None),{"bytes":total,"sha256":digest.hexdigest()}

def file_snapshot(path, maximum, check=lambda:None):
    return bounded_file(path,maximum,check,True)


HERE = Path(__file__).resolve().parent

def checked_contract():
    deadline = time.monotonic()+30
    def check():
        if time.monotonic() >= deadline:
            raise RuntimeError("Data-contract bootstrap wall deadline exhausted")
    check()
    if HERE.resolve(strict=True) != HERE or not stat.S_ISDIR(HERE.lstat().st_mode):
        raise RuntimeError("Canonical flat v3 packet required")
    seal_data,seal_identity = file_snapshot(HERE/"seal.json",65536,check)
    seal = json.loads(seal_data)
    expected = {row["path"]:row for row in seal["members"]}
    if len(expected) != len(seal["members"]) or not 1 <= len(expected) <= 63:
        raise RuntimeError("Finite unique flat v3 seal required")
    observed,total = set(),0
    with os.scandir(HERE) as entries:
        for entry in entries:
            check()
            observed.add(entry.name)
            if len(observed) > 64:
                raise RuntimeError("V3 packet node bound exceeded")
            path = HERE/entry.name
            data,identity = file_snapshot(path,524288,check)
            total += identity["bytes"]
            if total > 1048576:
                raise RuntimeError("V3 packet byte bound exceeded")
            if entry.name == "seal.json":
                if identity != seal_identity:
                    raise RuntimeError("Seal changed during bootstrap")
            else:
                row = expected.get(entry.name)
                if row is None or identity != {k:row[k] for k in ("bytes","sha256")}:
                    raise RuntimeError("Sealed v3 helper/source changed")
                if entry.name == "source_contract.py": contract_data = data
    if observed != set(expected)|{"seal.json"}:
        raise RuntimeError("Sealed v3 namespace changed")
    path = HERE/"source_contract.py"
    spec = importlib.util.spec_from_file_location("pair7_v3_pure_contract",path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(contract_data,str(path),"exec"),module.__dict__)
    check()
    return module

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("stage","post"):
        raise RuntimeError("stage or post required")
    c = checked_contract()
    budget = c.WallBudget(60,15)
    context = c.ci_identity(dict(os.environ),"snapshot")
    root = c.ordinary_root(Path(os.environ["GITHUB_WORKSPACE"]))
    c.need(HERE == root/"verification/pair7-java-compile-ci-proposal/v3","Exact nested v3 packet required")
    manifest,manifest_id = c.read_json(c.ordinary_file(HERE,"snapshot-source-manifest.json"),65536,budget.check)
    verified = c.source_manifest(root,manifest,sys.argv[1] == "post",budget.check)
    overlay = manifest["overlay"]
    source = c.ordinary_file(root,overlay["source"])
    source_data,source_id = c.file_snapshot(source,1048576,budget.check)
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
            stream.write(source_data)
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
