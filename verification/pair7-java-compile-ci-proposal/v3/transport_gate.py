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

def transfer_identity(artifact_id, digest):
    need(isinstance(artifact_id,str) and artifact_id.isascii() and artifact_id.isdecimal()
         and 1 <= len(artifact_id) <= 20 and artifact_id[0] != "0"
         and int(artifact_id) <= 18446744073709551615, "Exact positive decimal artifact ID required")
    need(isinstance(digest,str) and len(digest) == 64
         and all(c in "0123456789abcdef" for c in digest), "Exact lowercase SHA256 artifact digest required")
    return {"artifact_id":artifact_id,"artifact_digest":digest}

def ci_identity(env, job):
    need(env.get("GITHUB_REPOSITORY") == "snowdamiz/mixer", "Exact repository required")
    need(env.get("GITHUB_EVENT_NAME") in ("push","pull_request"), "Ordinary CI required")
    need(env.get("GITHUB_JOB") == job, "Exact selected job required")
    need(env.get("GITHUB_RUN_ATTEMPT") == "1", "No retry allowance")
    run,head = env.get("GITHUB_RUN_ID"),env.get("GITHUB_SHA")
    need(isinstance(run,str) and run.isascii() and run.isdecimal() and run[0] != "0", "Exact run id required")
    need(isinstance(head,str) and len(head) == 40 and all(c in "0123456789abcdef" for c in head), "Exact immutable source head required")
    return {"repository":env["GITHUB_REPOSITORY"],"event":env["GITHUB_EVENT_NAME"],
            "job":job,"run_id":run,"run_attempt":1,"source_head":head}


def ordinary_root(root):
    root = Path(root)
    need(root.is_absolute() and root.resolve(strict=True) == root, "Canonical ordinary root required")
    need(stat.S_ISDIR(root.lstat().st_mode), "Ordinary root directory required")
    return root

def fresh_download_root(temp):
    temp = ordinary_root(Path(temp))
    path = temp/"pair7-java-snapshot-input"
    need(not os.path.lexists(path),"Fresh absent download destination required")
    return path

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
    need(len(sys.argv)==2 and sys.argv[1] in ("transfer","snapshot-upload","host-log-upload"),"Exact gate mode required")
    env = dict(os.environ)
    if sys.argv[1] == "transfer":
        # No subject helper imports can precede this transport gate.
        identity = transfer_identity(env.get("MIXER_PAIR7_SNAPSHOT_ARTIFACT_ID"),env.get("MIXER_PAIR7_SNAPSHOT_ARTIFACT_DIGEST"))
        context = ci_identity(env,"compile")
        fresh_download_root(env["RUNNER_TEMP"])
        print(json.dumps({"schema":2,"status":"exact-action-metadata-binding-only",**identity,"context":context},sort_keys=True))
        return
    context = ci_identity(env,"snapshot")
    c = checked_contract()
    budget = c.WallBudget(60,15)
    if sys.argv[1] == "host-log-upload":
        temp = c.ordinary_root(Path(env["RUNNER_TEMP"]))
        c.host_logs_inventory(temp/("pair7-java-source-"+context["run_id"]+"-1"),budget.check)
        budget.check()
        output_file = c.ordinary_file(temp,Path(env["GITHUB_OUTPUT"]).relative_to(temp).as_posix())
        descriptor = os.open(output_file,os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW)
        with os.fdopen(descriptor,"w") as stream: stream.write("host_logs_upload_ready=true\n")
        return
    closure,_ = c.read_json(c.ordinary_file(HERE,"exact-java-closure.json"),65536,budget.check)
    expected = [{"path":row["generated_path"],"bytes":row["bytes"],"sha256":row["sha256"]} for row in closure["members"]]
    temp = c.ordinary_root(Path(env["RUNNER_TEMP"]))
    snapshot = temp/("pair7-java-snapshot-"+context["run_id"]+"-1")
    c.snapshot_closure(snapshot,expected,{"repository":context["repository"],"source_head":context["source_head"],"run_id":context["run_id"]},budget.check)
    budget.check()
    output_file = c.ordinary_file(temp,Path(env["GITHUB_OUTPUT"]).relative_to(temp).as_posix())
    descriptor = os.open(output_file,os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW)
    with os.fdopen(descriptor,"w") as stream:
        stream.write("snapshot_upload_ready=true\n")
    print("Bounded exact snapshot source/receipt namespace admitted for upload; no archive-byte or provider-disposal attestation.")
if __name__ == "__main__":
    main()
