"""v3 source proposal: exact actual generated18 javac/D8 only. No product main."""
import sys
sys.dont_write_bytecode = True
if not (sys.flags.isolated == 1 and sys.flags.no_site == 1):
    raise RuntimeError("Run with -I -B -S")
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import resource
import stat
import time

# These pure definitions are copied byte-for-byte from source_contract.py.
# Guarded controls compare their ASTs. No helper import precedes transport admission.
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DONOR = ROOT/"verification/android-view-api-package-runtime-host-preparation"

def load(path, name):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def save(path, value, budget, maximum=4194304):
    budget.check()
    path = Path(path)
    need(path.parent.resolve(strict=True) == path.parent,"Ordinary output ancestors required")
    descriptor = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    total = 0
    with os.fdopen(descriptor,"wb") as stream:
        for piece in json.JSONEncoder(sort_keys=True,indent=2).iterencode(value):
            budget.check()
            data = piece.encode()
            total += len(data)
            need(total+1 <= maximum,"Bounded JSON output refused")
            stream.write(data)
        stream.write(b"\n")
    budget.check()

def verify_packet(budget):
    tree = bounded_tree(HERE,64,1048576,524288,budget.check)
    need(not tree["directories"],"Flat sealed v3 namespace required")
    seal,seal_id = read_json(ordinary_file(HERE,"seal.json"),65536,budget.check)
    wanted = [{"path":row["path"],"bytes":row["bytes"],"sha256":row["sha256"]} for row in seal["members"]]
    wanted.append({"path":"seal.json",**seal_id}); wanted.sort(key=lambda row:row["path"])
    need(tree["members"] == wanted,"Sealed v3 namespace/bytes changed")
    return seal_id

def collect(snapshot, output):
    need(not getattr(sys,"_mixer_pair7_v3_compile_entered",False),"Collector already entered")
    sys._mixer_pair7_v3_compile_entered = True
    budget = WallBudget(420,60)
    env = dict(os.environ)
    # Both gates precede any helper import, output mutation, or tool child.
    transfer = transfer_identity(env.get("MIXER_PAIR7_SNAPSHOT_ARTIFACT_ID"),env.get("MIXER_PAIR7_SNAPSHOT_ARTIFACT_DIGEST"))
    context = ci_identity(env,"compile")
    ordinary_root(ROOT)
    need(ROOT == Path(env["GITHUB_WORKSPACE"]),"Exact checkout required")
    temp = ordinary_root(Path(env["RUNNER_TEMP"]))
    run = context["run_id"]
    need(output == temp/("pair7-java-compile-"+run+"-1"),"Exact fresh output required")
    need(snapshot == temp/"pair7-java-snapshot-input","Exact download root required")
    ordinary_root(snapshot)
    output.mkdir(exist_ok=False)
    receipt = {"schema":2,"status":"refused-before-compile","compile_commands_accepted":False,
               "runtime_accepted":False,"context":context,"transfer_binding":transfer,
               "archive_digest_scope":"Declared GitHub action metadata only; archive bytes are not retained or independently attested.",
               "commands":[],"errors":[],"scratch_disposition":"retained"}
    compiled,upload_ready = False,False
    try:
        reservation = temp/(".pair7-java-compile-"+run+"-1.reservation.json")
        with reservation.open("xb") as stream:
            stream.write(json.dumps({**context,**transfer}).encode())
            stream.flush(); os.fsync(stream.fileno())
        parent_fd = os.open(temp,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(parent_fd)
        finally: os.close(parent_fd)
        budget.check()
        reservation_data,reservation_id = file_snapshot(reservation,4096,budget.check)
        descriptor = os.open(output/"reservation.json",os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(descriptor,"wb") as stream: stream.write(reservation_data)
        receipt["durable_reservation"] = {"path":str(reservation),"identity":reservation_id,"artifact_copy":"reservation.json"}
        resource.setrlimit(resource.RLIMIT_CPU,(480,480))
        resource.setrlimit(resource.RLIMIT_AS,(2147483648,8589934592))
        resource.setrlimit(resource.RLIMIT_FSIZE,(67108864,67108864))
        verify_packet(budget)
        plan,_ = read_json(ordinary_file(HERE,"compile-command-plan.json"),1048576,budget.check)
        for row in plan["donor_files"]:
            need(file_identity(ordinary_file(ROOT,row["path"]),10485760,budget.check)
                 == {k:row[k] for k in ("bytes","sha256")},"Exact donor pin changed")
        # Only exact sealed helpers are loaded after transport/source admission.
        tools = load(HERE/"tool_data.py","pair7_v3_time_bounded_tool_data")
        tools.HERE,tools.CHECK,tools.file_identity,tools.file_snapshot = DONOR,budget.check,file_identity,file_snapshot
        custody = load(DONOR/"custody.py","pair7_v3_unchanged_linux_custody")
        inspector = load(HERE/"java_api_floor.py","pair7_v3_java_floor_data")
        inspector.CHECK = budget.check
        profile,_ = read_json(ordinary_file(DONOR,"tool-profile.json"),65536,budget.check)
        need(profile["id"] == plan["tool_profile"]["reuse_identity"] and profile["identity_mode"] == "package-observed-jdk-runtime-files-v1","Only selected exact existing tool profile is admitted")
        closure,closure_id = read_json(ordinary_file(HERE,"exact-java-closure.json"),65536,budget.check)
        manifest,manifest_id = read_json(ordinary_file(HERE,"snapshot-source-manifest.json"),65536,budget.check)
        need(closure["product_java_members"] == len(closure["members"]) == 18
             and closure["product_java_bytes"] == sum(row["bytes"] for row in closure["members"]) == 393165,"Exact18 source closure required")
        expected_java = [{"path":row["generated_path"],"bytes":row["bytes"],"sha256":row["sha256"]} for row in closure["members"]]
        producer_context = {"repository":context["repository"],"source_head":context["source_head"],"run_id":run}
        baseline_snapshot = snapshot_closure(snapshot,expected_java,producer_context,budget.check)
        producer = baseline_snapshot["producer"]
        need(producer["profile_id"] == closure["profile_id"] == "mixer.android-source-pair.7","Exact pair7 required")
        need(producer["source_manifest_sha256"] == closure_id["sha256"],"Producer Java manifest differs")
        need(producer["producer_package_source_manifest_sha256"] == manifest_id["sha256"],"Producer package manifest differs")
        need(producer["producer_source_sha256"] == file_identity(HERE/"Pair7JavaSnapshotExportTests.swift",1048576,budget.check)["sha256"],"Producer test source differs")
        need(producer["generator_source_sha256"] == file_identity(ROOT/"cli/Sources/MixerBuild/AndroidProject.swift",1048576,budget.check)["sha256"],"Actual generator source differs")
        workflow = ordinary_file(ROOT,".github/workflows/pair7-java-compile.yml")
        need(file_identity(workflow,1048576,budget.check) == file_identity(HERE/"workflow.DRAFT.yml",1048576,budget.check),"Installed separate workflow differs")
        need(producer["installed_workflow_sha256"] == file_identity(workflow,1048576,budget.check)["sha256"],"Producer workflow differs")
        api_row = plan["tool_profile"]["additional_api_xml"]
        api_xml = Path(api_row["path"])
        source_before = None
        def source_flight():
            budget.check()
            packet_id = verify_packet(budget)
            need(file_identity(reservation,4096,budget.check) == reservation_id
                 and file_identity(output/"reservation.json",4096,budget.check) == reservation_id,"Durable reservation/copy changed")
            named_sources = source_manifest(ROOT,manifest,False,budget.check)
            for row in plan["donor_files"]:
                need(file_identity(ordinary_file(ROOT,row["path"]),10485760,budget.check)
                     == {k:row[k] for k in ("bytes","sha256")},"Donor source drift")
            current_snapshot = unchanged_snapshot(snapshot,expected_java,producer_context,baseline_snapshot,budget.check)
            for row in closure["members"]:
                need(file_identity(ordinary_file(ROOT,row["canonical_path"]),1048576,budget.check)
                     == {k:row[k] for k in ("bytes","sha256")},"Canonical Java drift")
            need(file_identity(api_xml,10485760,budget.check) == {k:api_row[k] for k in ("bytes","sha256")},"Official API metadata drift")
            observed_tools = tools.verify_tools(profile)
            budget.check()
            return {"packet":packet_id,"source":named_sources,"snapshot":current_snapshot,
                    "tools":observed_tools,"source_head":context["source_head"]}
        source_before = source_flight()
        save(output/"preflight.json",source_before,budget)
        scratch = output/"scratch"
        for name in ("tmp","home","empty","classes","dex"):
            (scratch/name).mkdir(parents=True,exist_ok=False)
        child_env = {"JAVA_HOME":profile["jdk"],"PATH":profile["jdk"]+"/bin:/usr/bin:/bin",
                     "HOME":str(scratch/"home"),"TMPDIR":str(scratch/"tmp"),"TMP":str(scratch/"tmp"),"TEMP":str(scratch/"tmp"),"LANG":"C","LC_ALL":"C","TZ":"UTC"}
        options = [x.replace("$"+"{SCRATCH}",str(scratch)) for x in plan["java_options"]]
        java,javac = str(Path(profile["jdk"])/"bin/java"),str(Path(profile["jdk"])/"bin/javac")
        jar,d8jar = str(Path(profile["android_platform"])/"android.jar"),str(Path(profile["android_build_tools"])/"lib/d8.jar")
        vectors = [("java-version",[java,*options,"-version"]),("javac-version",[javac,*["-J"+x for x in options],"-version"]),("d8-version",[java,*options,"-cp",d8jar,"com.android.tools.r8.D8","--version"]),("sdk37-generated18-compile",[javac,*["-J"+x for x in options],"--release","17","-proc:none","-Xlint:all","-Werror","-sourcepath",str(scratch/"empty"),"-classpath",jar,"-d",str(scratch/"classes"),*[str(snapshot/("consumer/"+row["generated_path"])) for row in closure["members"]]])]
        def flight():
            current = source_flight()
            need(current == source_before,"Within-run source/tool drift")
            bounded_tree(scratch,1024,134217728,67108864,budget.check)
            return current
        def child_preflight():
            result = flight()
            budget.reserve_child()
            return result
        def command(name,argv):
            budget.reserve_child()
            result = custody.run_command(name,argv,scratch,child_env,output/"commands"/name,
                                         profile["bounds"],child_preflight,flight)
            receipt["commands"].append({"name":name,"accepted":result["accepted"]})
            budget.check()
            return output/"commands"/name
        for name,argv in vectors:
            directory = command(name,argv)
            if name.endswith("version"):
                key = {"java-version":"java_stderr","javac-version":"javac_stdout","d8-version":"d8_stdout"}[name]
                stream = key.split("_")[-1]
                need((directory/stream).read_text() == profile["versions"][key],"Exact version output changed")
                need(not (directory/("stdout" if stream=="stderr" else "stderr")).read_bytes(),"Unexpected version stream")
            else:
                need(not (directory/"stdout").read_bytes() and not (directory/"stderr").read_bytes(),"Compiler diagnostics retained and refused")
        class_tree = bounded_tree(scratch/"classes",1024,134217728,67108864,budget.check)
        classes = class_tree["members"]
        need(classes and all(row["path"].endswith(".class") for row in classes),"Only nonempty ordinary emitted class closure admitted")
        save(output/"emitted-classes.json",classes,budget)
        d8 = [java,*options,"-cp",d8jar,"com.android.tools.r8.D8","--min-api","28","--lib",jar,"--output",str(scratch/"dex"),*[str(scratch/"classes"/row["path"]) for row in classes]]
        command("d8-min28-generated18",d8)
        dex_tree = bounded_tree(scratch/"dex",2,67108864,67108864,budget.check)
        need([row["path"] for row in dex_tree["members"]] == ["classes.dex"] and not dex_tree["directories"],"Exactly one ordinary bounded DEX required")
        selected_dex = {k:dex_tree["members"][0][k] for k in ("bytes","sha256")}
        floors = inspect_selected_dex(inspector,scratch/"dex/classes.dex",api_xml,selected_dex,
                                     {k:api_row[k] for k in ("bytes","sha256")},classes,budget.check)
        budget.check()
        save(output/"java-api-floor.json",floors,budget)
        need(floors["accepted"],"Fresh emitted Java API-floor closure refused")
        need(bounded_tree(scratch/"classes",1024,134217728,67108864,budget.check) == class_tree,"Fresh class identity/topology changed")
        need(bounded_tree(scratch/"dex",2,67108864,67108864,budget.check) == dex_tree,"Fresh DEX identity/topology changed")
        save(output/"postflight.json",flight(),budget)
        receipt.update(status="exact-generated18-compile-work-complete",compile_commands_accepted=True,
                       java_sources=18,dex=dex_tree["members"][0],active_wall=budget.observation())
        compiled = True
    except BaseException as error:
        receipt["errors"].append(type(error).__name__+": "+str(error)[:2000])
    finally:
        # No tool child or product work can run during retention.
        try:
            budget.begin_retention()
            receipt["retention_started"] = budget.observation()
            if compiled:
                need(bounded_tree(scratch/"dex",2,67108864,67108864,budget.check) == dex_tree,"DEX changed before retention")
            save(output/"receipt.json",receipt,budget)
            inventory = artifact_inventory(output,budget,False)
            save(output/"artifact-manifest.json",{"schema":2,"inventory":inventory,
                 "acceptance":"Require upload.allow.json, successful bounded final scan and collector exit; this manifest alone is not acceptance.",
                 "archive_digest_scope":"GitHub action metadata only."},budget)
            save(output/"upload.allow.json",{"schema":2,"compile_accepted":compiled,
                 "artifact_manifest":file_identity(output/"artifact-manifest.json",4194304,budget.check),
                 "context":context,"wall":budget.observation()},budget,65536)
            final_inventory = artifact_inventory(output,budget,True)
            if compiled:
                retained_dex = [r for r in final_inventory["members"] if r["path"] == "scratch/dex/classes.dex"]
                need(retained_dex == [{"path":"scratch/dex/classes.dex",**selected_dex}],"Retained DEX differs from parsed snapshot")
            budget.check()
            output_file = ordinary_file(temp,Path(env["GITHUB_OUTPUT"]).relative_to(temp).as_posix())
            descriptor = os.open(output_file,os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW)
            with os.fdopen(descriptor,"w") as stream:
                stream.write("output_artifact_ready=true\n")
            upload_ready = True
        except BaseException as error:
            receipt["errors"].append("bounded retention: "+type(error).__name__+": "+str(error)[:1000])
            compiled = False
    if not (compiled and upload_ready):
        print(json.dumps({"status":"refused","errors":receipt["errors"],"bounded_artifact_ready":upload_ready})[:4096],file=sys.stderr)
    need(compiled and upload_ready,"Compile action refused; no unbounded upload admission is issued")

if __name__ == "__main__":
    need(len(sys.argv)==3,"Exact snapshot input and output arguments required")
    collect(Path(sys.argv[1]),Path(sys.argv[2]))
