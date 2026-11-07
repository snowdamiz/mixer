"""Pure source/transport/budget contracts. No child, network, or product imports."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
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

def relative_name(value):
    need(isinstance(value,str) and value and "\\" not in value and "\0" not in value,
         "Exact nonempty relative source name required")
    path = PurePosixPath(value)
    need(bool(path.parts) and not path.is_absolute() and ".." not in path.parts and path.as_posix() == value
         and all(part not in ("",".") for part in path.parts), "Source name escapes or changes topology")
    return value

def ordinary_root(root):
    root = Path(root)
    need(root.is_absolute() and root.resolve(strict=True) == root, "Canonical ordinary root required")
    need(stat.S_ISDIR(root.lstat().st_mode), "Ordinary root directory required")
    return root

def ordinary_file(root, name):
    root = ordinary_root(root)
    path = root / relative_name(name)
    cursor = root
    parts = Path(name).parts
    for part in parts[:-1]:
        cursor = cursor / part
        need(stat.S_ISDIR(cursor.lstat().st_mode), "Ordinary source ancestor required")
    need(stat.S_ISREG(path.lstat().st_mode), "Ordinary source file required")
    return path

class WallBudget:
    def __init__(self, active_seconds=420, retention_seconds=60, clock=time.monotonic):
        need(isinstance(active_seconds,int) and active_seconds > 0 and isinstance(retention_seconds,int)
             and retention_seconds > 0, "Positive finite integer wall budgets required")
        self.clock,self.started,self.active_seconds,self.retention_seconds = clock,clock(),active_seconds,retention_seconds
        self.phase,self.deadline = "active",self.started+active_seconds
    def check(self):
        need(self.clock() < self.deadline, self.phase+" wall-clock deadline exhausted")
    def reserve_child(self):
        self.check()
        # Preserve donor exact60+cleanup6+final-observation2. Never alter its bounds.
        need(self.phase == "active" and self.deadline-self.clock() >= 68,
             "Insufficient active wall time for complete unchanged child/cleanup bound")
    def begin_retention(self):
        need(self.phase == "active", "Retention can begin exactly once")
        self.phase = "retention"
        self.deadline = min(self.clock()+self.retention_seconds,
                            self.started+self.active_seconds+self.retention_seconds)
        self.check()
    def observation(self):
        return {"phase":self.phase,"elapsed_seconds":self.clock()-self.started,
                "deadline_seconds_from_start":self.deadline-self.started,
                "active_seconds":self.active_seconds,"retention_seconds":self.retention_seconds}

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

def file_identity(path, maximum=67108864, check=lambda:None):
    return bounded_file(path,maximum,check,False)[1]

def bounded_tree(root, maximum_nodes, maximum_bytes, maximum_file_bytes, check=lambda:None):
    root = ordinary_root(root)
    check()
    nodes,total,stack,rows,directories = 1,0,[root],[],[]
    while stack:
        check()
        directory = stack.pop()
        entries = []
        with os.scandir(directory) as iterator:
            for entry in iterator:
                check()
                nodes += 1
                need(nodes <= maximum_nodes,"Tree node bound exceeded")
                entries.append(entry.name)
        for name in sorted(entries):
            check()
            path = directory/name
            mode = path.lstat().st_mode
            relative = path.relative_to(root).as_posix()
            relative_name(relative)
            if stat.S_ISDIR(mode):
                directories.append(relative); stack.append(path)
            else:
                need(stat.S_ISREG(mode),"Tree symlink or special node refused")
                size = path.lstat().st_size
                total += size
                need(size <= maximum_file_bytes and total <= maximum_bytes,"Tree byte bound exceeded")
                row = file_identity(path,maximum_file_bytes,check)
                need(row["bytes"] == size,"Tree file changed size")
                rows.append({"path":relative,**row})
    check()
    return {"members":sorted(rows,key=lambda r:r["path"]),"directories":sorted(directories),
            "nodes":nodes,"bytes":total}

def expected_directories(names):
    result = set()
    for name in names:
        path = PurePosixPath(relative_name(name)).parent
        while path.as_posix() != ".":
            result.add(path.as_posix()); path = path.parent
    return sorted(result)

def read_json(path, maximum, check=lambda:None):
    data,identity = file_snapshot(path,maximum,check)
    check()
    value = json.loads(data)
    check()
    need(file_identity(path,maximum,check) == identity,"JSON changed during decode")
    return value,identity

def inspect_selected_dex(inspector, dex_path, api_path, selected_dex, selected_api, emitted_classes, check=lambda:None):
    data,identity = file_snapshot(dex_path,67108864,check)
    need(identity == selected_dex,"DEX snapshot differs from selected tree")
    api,api_identity = file_snapshot(api_path,10485760,check)
    need(api_identity == selected_api,"API snapshot differs from selected metadata")
    result = inspector.inspect(data,api,emitted_classes)
    check()
    need(result["dex_sha256"] == identity["sha256"],"Parsed DEX hash differs from selected snapshot")
    need(file_identity(dex_path,67108864,check) == identity,"DEX changed during inspection")
    need(file_identity(api_path,10485760,check) == api_identity,"API metadata changed during inspection")
    return result

def snapshot_closure(snapshot, expected_java, context, check=lambda:None):
    snapshot = ordinary_root(snapshot)
    topology = bounded_tree(snapshot,256,4194304,1048576,check)
    producer,producer_identity = read_json(ordinary_file(snapshot,"snapshot-receipt.json"),262144,check)
    started,started_identity = read_json(ordinary_file(snapshot,"started.json"),4096,check)
    need(producer.get("status") == "actual-snapshot-java-source-data-only", "Actual producer receipt required")
    for key,value in context.items():
        need(producer.get(key) == value,"Producer context changed: "+key)
    need(producer.get("producer_job") == "snapshot" and producer.get("run_attempt") == 1,"Exact snapshot producer job required")
    need(started.get("status") == "started" and started.get("source_head") == context["source_head"],"Started receipt binding required")
    need(started.get("source_manifest_sha256") == producer.get("source_manifest_sha256"),"Started source closure changed")
    need(producer.get("additional_app_owned_Java") == [],"Unselected application Java")
    need(producer.get("generated_java") == expected_java,"Exact generated Java map required")
    generated = producer.get("generated_tree")
    need(isinstance(generated,list) and 1 <= len(generated) <= 128,"Finite complete generated tree required")
    names = [relative_name(row["path"]) for row in generated]
    need(len(set(names)) == len(names) and names == sorted(names),"Sorted unique generated tree required")
    wanted = [{"path":"consumer/Generated/MixerAndroid/"+row["path"],"bytes":row["bytes"],"sha256":row["sha256"]} for row in generated]
    wanted += [{"path":"snapshot-receipt.json",**producer_identity},{"path":"started.json",**started_identity}]
    wanted.sort(key=lambda row:row["path"])
    need(topology["members"] == wanted,"Whole downloaded artifact namespace/identity changed")
    need(topology["directories"] == expected_directories(row["path"] for row in wanted),"Unexpected artifact directory topology")
    actual_java = [{"path":"Generated/MixerAndroid/"+row["path"],"bytes":row["bytes"],"sha256":row["sha256"]}
                   for row in generated if row["path"].endswith(".java")]
    need(actual_java == expected_java,"Closed generated Java membership changed")
    digest = hashlib.sha256()
    for row in generated:
        digest.update((row["path"]+"\0"+row["sha256"]+"\n").encode())
    need(digest.hexdigest() == producer.get("generated_snapshot_digest"),"Actual SourceDigest.tree recomputation differs")
    check()
    return {"producer":producer,"producer_receipt":producer_identity,"started_receipt":started_identity,
            "artifact":topology,"generated_snapshot_digest":digest.hexdigest()}

def source_manifest(root, manifest, overlay=False, check=lambda:None):
    root = ordinary_root(root)
    rows = manifest["members"]
    need(len(rows) == manifest["count"] == 142 and sum(r["bytes"] for r in rows) == manifest["bytes"] == 2779239,
         "Exact source manifest totals required")
    names = [relative_name(row["path"]) for row in rows]
    need(len(set(names)) == len(names),"Duplicate source manifest member")
    for row in rows:
        check()
        need(file_identity(ordinary_file(root,row["path"]),10485760,check)
             == {k:row[k] for k in ("bytes","sha256")},"Named source identity changed")
    for folder in manifest["closed_directories"]:
        relative_name(folder)
        tree = bounded_tree(root/folder,1024,16777216,10485760,check)
        expected = {row["path"]: {k:row[k] for k in ("bytes","sha256")} for row in rows if row["path"].startswith(folder+"/")}
        if overlay and manifest["overlay"]["target"].startswith(folder+"/"):
            target = manifest["overlay"]["target"]
            expected[target] = file_identity(ordinary_file(root,target),1048576,check)
            need(expected[target]["sha256"] == manifest["overlay"]["sha256"],"Overlay changed")
        observed = {folder+"/"+row["path"]: {k:row[k] for k in ("bytes","sha256")} for row in tree["members"]}
        need(observed == expected,"Closed source membership changed")
        need(tree["directories"] == expected_directories(name[len(folder)+1:] for name in expected),"Closed source directory topology changed")
    return {"count":len(rows),"bytes":manifest["bytes"]}

def unchanged_snapshot(snapshot, expected_java, context, baseline, check=lambda:None):
    current = snapshot_closure(snapshot,expected_java,context,check)
    need(current == baseline,"Downloaded producer receipt/source closure changed")
    return current

def artifact_inventory(output, budget, final=False):
    need(budget.phase == "retention","Artifact inventory requires retention phase")
    budget.check()
    result = bounded_tree(output,4096 if final else 4094,
                          268435456 if final else 260046848,67108864,budget.check)
    budget.check()
    return result
def fresh_download_root(temp):
    temp = ordinary_root(Path(temp))
    path = temp/"pair7-java-snapshot-input"
    need(not os.path.lexists(path),"Fresh absent download destination required")
    return path

def host_logs_inventory(root, check=lambda:None):
    tree = bounded_tree(root,9,134217728,67108864,check)
    allowed = {"stage.json","post.json","apple-toolchain.json","bash-file-limit.txt",
               "bash-version.txt","swift.stdout","swift.stderr","swift.exit"}
    need(tree["members"] and not tree["directories"]
         and {row["path"] for row in tree["members"]}.issubset(allowed),
         "Only bounded named host source/command evidence is uploadable")
    return tree

