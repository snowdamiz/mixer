"""Source proposal: exact actual generated18 javac/D8 only. No Java product main."""
import sys
sys.dont_write_bytecode = True
if not (sys.flags.isolated == 1 and sys.flags.no_site == 1):
    raise RuntimeError("Run with -I -B -S")
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import stat
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DONOR = ROOT / "verification/android-view-api-package-runtime-host-preparation"
def need(value, message):
    if not value: raise RuntimeError(message)
def identity(path):
    path = Path(path)
    need(path.stat().st_size <= 268435456, "File byte bound")
    data = path.read_bytes()
    return {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value,stream,sort_keys=True,indent=2)
        stream.write("\n")
def regular(path, base):
    path, base = Path(path), Path(base)
    need(path.is_relative_to(base), "Path escapes selected root")
    cursor = path
    while cursor != base:
        need(not stat.S_ISLNK(cursor.lstat().st_mode), "Symlink source path")
        cursor = cursor.parent
    need(stat.S_ISREG(path.lstat().st_mode), "Ordinary file required")
    return path
def verify_packet():
    seal = json.loads((HERE / "seal.json").read_bytes())
    expected = {row["path"] for row in seal["members"]}
    observed = {p.relative_to(HERE).as_posix() for p in HERE.rglob("*") if p.is_file()}
    need(observed == expected | {"seal.json"}, "Proposal namespace changed")
    for row in seal["members"]:
        need(identity(regular(HERE / row["path"],HERE)) == {k:row[k] for k in ("bytes","sha256")}, "Proposal bytes changed")
    return identity(HERE / "seal.json")
def load(path, name):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def collect(snapshot, output):
    need(not getattr(sys,"_mixer_pair7_compile_entered",False),"Collector already entered")
    sys._mixer_pair7_compile_entered = True
    env = dict(os.environ)
    need(env.get("GITHUB_REPOSITORY") == "snowdamiz/mixer" and env.get("GITHUB_EVENT_NAME") in ("push","pull_request"),"Ordinary selected repository CI required")
    need(env.get("GITHUB_RUN_ATTEMPT") == "1", "No retry allowance")
    need(ROOT == Path(env["GITHUB_WORKSPACE"]), "Exact checkout required")
    temp = Path(env["RUNNER_TEMP"])
    need(temp.is_absolute() and temp.resolve() == temp,"Canonical runner temp required")
    run = env["GITHUB_RUN_ID"]
    need(run.isascii() and run.isdecimal(),"Exact run id required")
    need(output == temp / ("pair7-java-compile-"+run+"-1"),"Exact fresh output required")
    need(snapshot == temp / "pair7-java-snapshot-input", "Exact action download root required")
    need(snapshot.resolve() == snapshot and stat.S_ISDIR(snapshot.lstat().st_mode),"Ordinary fresh artifact download root required")
    output.mkdir(exist_ok=False)
    receipt = {"schema":1,"status":"refused-before-compile","accepted":False,"runtime_accepted":False,"commands":[],"errors":[],"scratch_disposition":"retained"}
    try:
        with (temp/(".pair7-java-compile-"+run+"-1.reservation.json")).open("xb") as stream:
            stream.write(json.dumps({"source_head":env["GITHUB_SHA"],"run_id":run,"attempt":1}).encode())
            stream.flush(); os.fsync(stream.fileno())
        parent_fd = os.open(temp, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(parent_fd)
        finally: os.close(parent_fd)
        resource.setrlimit(resource.RLIMIT_CPU,(420,420))
        resource.setrlimit(resource.RLIMIT_AS,(2147483648,8589934592))
        resource.setrlimit(resource.RLIMIT_FSIZE,(268435456,268435456))
        verify_packet()
        plan = json.loads((HERE / "compile-command-plan.json").read_bytes())
        for row in plan["donor_files"]:
            need(identity(regular(ROOT / row["path"],ROOT)) == {k:row[k] for k in ("bytes","sha256")},"Donor changed")
        # Exact inert helper import only. Old collect()/main() are never called.
        tools = load(DONOR/"collect.py","pair7_exact_tool_verifier")
        custody = load(DONOR/"custody.py","pair7_exact_linux_custody")
        inspector = load(HERE/"java_api_floor.py","pair7_java_floor_data")
        profile = json.loads((DONOR/"tool-profile.json").read_bytes())
        closure = json.loads((HERE/"exact-java-closure.json").read_bytes())
        manifest = json.loads((HERE/"snapshot-source-manifest.json").read_bytes())
        producer = json.loads(regular(snapshot/"snapshot-receipt.json",snapshot).read_bytes())
        need(producer["status"] == "actual-snapshot-java-source-data-only" and producer["source_head"] == env["GITHUB_SHA"] and producer["run_id"] == run and producer["run_attempt"] == 1,"Actual same-head producer binding required")
        need(producer["source_manifest_sha256"] == identity(HERE/"exact-java-closure.json")["sha256"],"Producer closure differs")
        need(producer["profile_id"] == closure["profile_id"] == "mixer.android-source-pair.7","Pair7 required")
        need(producer["additional_app_owned_Java"] == [],"Unselected application Java")
        need(producer["producer_package_source_manifest_sha256"] == identity(HERE/"snapshot-source-manifest.json")["sha256"],"Producer package manifest differs")
        need(producer["producer_source_sha256"] == identity(HERE/"Pair7JavaSnapshotExportTests.swift")["sha256"],"Producer test source differs")
        need(producer["generator_source_sha256"] == identity(ROOT/"cli/Sources/MixerBuild/AndroidProject.swift")["sha256"],"Actual generator source differs")
        need(producer["installed_workflow_sha256"] == identity(HERE/"workflow.DRAFT.yml")["sha256"],"Producer workflow differs")
        generated = snapshot/"consumer/Generated/MixerAndroid"
        expected_java = [{"path":r["generated_path"],"bytes":r["bytes"],"sha256":r["sha256"]} for r in closure["members"]]
        need(producer["generated_java"] == expected_java,"Producer generated18 map differs")
        api_row = plan["tool_profile"]["additional_api_xml"]
        api_xml = Path(api_row["path"])
        def source_flight():
            packet = verify_packet()
            need(identity(regular(ROOT/".github/workflows/pair7-java-compile.yml",ROOT)) == identity(HERE/"workflow.DRAFT.yml"),"Installed separate workflow changed")
            for row in plan["donor_files"]+manifest["members"]:
                need(identity(regular(ROOT/row["path"],ROOT)) == {k:row[k] for k in ("bytes","sha256")},"Named source drift")
            for row in closure["members"]:
                wanted = {k:row[k] for k in ("bytes","sha256")}
                need(identity(regular(ROOT/row["canonical_path"],ROOT)) == wanted,"Canonical Java drift")
                need(identity(regular(snapshot/("consumer/"+row["generated_path"]),snapshot)) == wanted,"Generated Java drift")
            actual = []
            for path in sorted(generated.rglob("*")):
                need(not path.is_symlink(),"Generated symlink")
                if path.is_file(): actual.append({"path":path.relative_to(generated).as_posix(),**identity(path)})
            need(actual == producer["generated_tree"],"Complete generated tree changed")
            need(identity(api_xml) == {k:api_row[k] for k in ("bytes","sha256")},"API metadata changed")
            return {"packet":packet,"source_head":env["GITHUB_SHA"],"generated_snapshot":producer["generated_snapshot_digest"],"tools":tools.verify_tools(profile)}
        before = source_flight()
        save(output/"preflight.json",before)
        scratch = output/"scratch"
        for name in ("tmp","home","empty","classes","dex"):
            (scratch/name).mkdir(parents=True,exist_ok=False)
        child_env = {"JAVA_HOME":profile["jdk"],"PATH":profile["jdk"]+"/bin:/usr/bin:/bin","HOME":str(scratch/"home"),"TMPDIR":str(scratch/"tmp"),"TMP":str(scratch/"tmp"),"TEMP":str(scratch/"tmp"),"LANG":"C","LC_ALL":"C","TZ":"UTC"}
        options = [x.replace("$"+"{SCRATCH}",str(scratch)) for x in plan["java_options"]]
        java,javac = str(Path(profile["jdk"])/"bin/java"),str(Path(profile["jdk"])/"bin/javac")
        jar = str(Path(profile["android_platform"])/"android.jar")
        d8jar = str(Path(profile["android_build_tools"])/"lib/d8.jar")
        vectors = [("java-version",[java,*options,"-version"]),("javac-version",[javac,*["-J"+x for x in options],"-version"]),("d8-version",[java,*options,"-cp",d8jar,"com.android.tools.r8.D8","--version"]),("sdk37-generated18-compile",[javac,*["-J"+x for x in options],"--release","17","-proc:none","-Xlint:all","-Werror","-sourcepath",str(scratch/"empty"),"-classpath",jar,"-d",str(scratch/"classes"),*[str(snapshot/("consumer/"+r["generated_path"])) for r in closure["members"]]])]
        def flight():
            current = source_flight()
            need(current == before,"Within-run source/tool drift")
            paths = list(scratch.rglob("*"))
            need(len(paths) <= 1024 and sum(p.stat().st_size for p in paths if p.is_file()) <= 134217728,"Scratch bound")
            return current
        def command(name,argv):
            result = custody.run_command(name,argv,scratch,child_env,output/"commands"/name,profile["bounds"],flight,flight)
            receipt["commands"].append({"name":name,"accepted":result["accepted"]})
            return output/"commands"/name
        for name,argv in vectors:
            directory = command(name,argv)
            if name.endswith("version"):
                key = {"java-version":"java_stderr","javac-version":"javac_stdout","d8-version":"d8_stdout"}[name]
                stream = key.split("_")[-1]
                need((directory/stream).read_text() == profile["versions"][key],"Version output changed")
                need(not (directory/("stdout" if stream=="stderr" else "stderr")).read_bytes(),"Unexpected version stream")
            else:
                need(not (directory/"stdout").read_bytes() and not (directory/"stderr").read_bytes(),"Compiler diagnostics retained and refused")
        classes = [{"path":p.relative_to(scratch/"classes").as_posix(),**identity(p)} for p in sorted((scratch/"classes").rglob("*.class"))]
        need(classes and len(classes) <= 1024,"Emitted class bound")
        save(output/"emitted-classes.json",classes)
        d8 = [java,*options,"-cp",d8jar,"com.android.tools.r8.D8","--min-api","28","--lib",jar,"--output",str(scratch/"dex"),*[str(scratch/"classes"/r["path"]) for r in classes]]
        command("d8-min28-generated18",d8)
        need([p.name for p in (scratch/"dex").iterdir()] == ["classes.dex"],"Exactly one DEX required")
        floors = inspector.inspect(scratch/"dex/classes.dex",api_xml,classes)
        save(output/"java-api-floor.json",floors)
        need(floors["accepted"],"Fresh emitted Java API-floor closure refused")
        need(classes == [{"path":p.relative_to(scratch/"classes").as_posix(),**identity(p)} for p in sorted((scratch/"classes").rglob("*.class"))],"Class bytes changed")
        save(output/"postflight.json",flight())
        receipt.update(status="passed-exact-generated18-javac-d8-java-floor-only",accepted=True,source_head=env["GITHUB_SHA"],producer_artifact_id=env["MIXER_PAIR7_SNAPSHOT_ARTIFACT_ID"],producer_artifact_digest=env["MIXER_PAIR7_SNAPSHOT_ARTIFACT_DIGEST"],java_sources=18,dex=identity(scratch/"dex/classes.dex"))
    except BaseException as error:
        receipt["errors"].append(type(error).__name__+": "+str(error)[:2000])
    finally:
        save(output/"receipt.json",receipt)
        members = [{"path":p.relative_to(output).as_posix(),**identity(p)} for p in sorted(output.rglob("*")) if p.is_file()]
        save(output/"artifact-manifest.json",{"schema":1,"members":members,"archive_hash_boundary":"GitHub action archive digest is separate metadata; no independent transport attestation."})
    need(receipt["accepted"],"Compile-only action refused; evidence retained")
if __name__ == "__main__":
    need(len(sys.argv)==3,"Exact snapshot input and output arguments required")
    collect(Path(sys.argv[1]),Path(sys.argv[2]))
