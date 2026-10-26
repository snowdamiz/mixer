#!/usr/bin/env python3
"""Bounded official-JDK leaf-only checks. No product source or native runtime."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
JDK = Path("/opt/homebrew/opt/openjdk/bin")
ROOT = HERE.parents[2]
CAP = 2 * 1024 * 1024


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(argv, stem, source_map, seconds=120):
    env = dict(os.environ)
    for name in ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH"):
        env.pop(name, None)
    start = time.monotonic()
    child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True)
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    selector = selectors.DefaultSelector()
    selector.register(child.stdout, selectors.EVENT_READ, "stdout")
    selector.register(child.stderr, selectors.EVENT_READ, "stderr")
    forced = None
    try:
        while selector.get_map():
            if time.monotonic() - start > seconds:
                forced = "wall-time-limit"
                break
            for key, _ in selector.select(timeout=.1):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                buffers[key.data].extend(chunk)
                if len(buffers[key.data]) > CAP:
                    forced = key.data + "-limit"
                    break
            if forced:
                break
        if forced:
            os.killpg(child.pid, signal.SIGKILL)
        status = child.wait(timeout=5)
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
        selector.close()
        child.stdout.close()
        child.stderr.close()
    for name, content in buffers.items():
        stem.with_suffix("." + name).write_bytes(bytes(content[:CAP]))
    record = dict(argv=[str(x) for x in argv], cwd=str(ROOT), exit_code=status,
                  forced_termination=forced, elapsed_seconds=round(time.monotonic()-start, 6),
                  limits=dict(wall_seconds=seconds, stdout_bytes=CAP, stderr_bytes=CAP, owned_children=1),
                  removed_environment=["JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH"],
                  executable_sha256=digest(Path(argv[0]).resolve()), source_map=source_map,
                  python=sys.version, at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  scope="leaf-only/synthetic instrumentation sanity; zero product classes or product tests")
    stem.with_suffix(".command.json").write_text(json.dumps(record, indent=2)+"\n")
    return record


def check_version(version):
    base = HERE if version == 1 else HERE / f"delta-{version}"
    manifest_name = "leaf-manifest.json" if version == 1 else f"leaf-manifest-{version}.json"
    manifest = json.loads((HERE / "admission" / manifest_name).read_text())
    out = HERE / "results" / f"leaf-{version}"
    out.mkdir(parents=True, exist_ok=True)
    inputs = [base/"inputs"/name for name in sorted(manifest["files"])]
    inputs.append(HERE/"IndependentLeafSanity.java")
    source_map = {str(p.relative_to(HERE)): dict(bytes=p.stat().st_size,sha256=digest(p)) for p in inputs}
    for name, expected in manifest["files"].items():
        p = base/"inputs"/name
        assert expected == dict(bytes=p.stat().st_size, sha256=digest(p)), name
    scratch_parent = HERE / "scratch"
    scratch_parent.mkdir(exist_ok=True)
    result = {"version":version,"product_tests":0,"scope":"leaf-only sanity"}
    with tempfile.TemporaryDirectory(prefix=f"leaf-{version}-",dir=scratch_parent) as temp:
        scratch = Path(temp); empty=scratch/"empty";classes=scratch/"classes"
        empty.mkdir();classes.mkdir()
        sources = out/"explicit-sources.list"
        sources.write_text("".join(str(p)+"\n" for p in inputs))
        argv = [str(JDK/"javac"),"--release","17","-g","-Xlint:all","-Werror","-proc:none",
                "-classpath",str(empty),"-sourcepath",str(empty),"-d",str(classes),"@"+str(sources)]
        compile_record = run(argv,out/"01-compile",source_map)
        result["compile"] = compile_record["exit_code"]
        if compile_record["exit_code"] == 0:
            hashes={str(p.relative_to(classes)):dict(bytes=p.stat().st_size,sha256=digest(p))
                    for p in sorted(classes.rglob("*.class"))}
            (out/"compiled-class-hashes.json").write_text(json.dumps(hashes,indent=2)+"\n")
            for index,name in enumerate(["dev.mixer.android.NativeRenderer$IndependentLeafTraceWitness",
                                         "dev.mixer.android.ConcreteHostProbe"]):
                run([str(JDK/"javap"),"-c","-p","-l","-s","-classpath",str(classes),name],
                    out/f"02-bytecode-{index}",source_map)
            runtime = run([str(JDK/"java"),"-Xms16m","-Xmx256m","-Xss512k","-XX:ActiveProcessorCount=2",
                           "-cp",str(classes),"dev.mixer.android.IndependentLeafSanity"],out/"03-run",source_map)
            result["run"] = runtime["exit_code"]
        result["cleanup"] = "all owned child commands reaped; exclusive compiled scratch removed by finally"
    assert not any(scratch_parent.iterdir()), "owned scratch has unexpected residual entries"
    scratch_parent.rmdir()
    result["compiled_scratch_absent"] = True
    (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))


def main():
    results = HERE/"results";results.mkdir(exist_ok=True)
    for index,tool in enumerate(["javac","java","javap"]):
        run([str(JDK/tool),"-version"],results/f"tool-{index}-{tool}",{})
    for version in [int(x) for x in sys.argv[1:]] or [1,2]:
        check_version(version)


if __name__ == "__main__":
    main()
