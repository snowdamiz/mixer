#!/usr/bin/env python3
"""Immutable-source independent embedding review; emits auditable host evidence."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVISION = "ce8f2c921dab12a0e859cb93366cef74277c6ef4"
SWIFT = Path("/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift")

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.name): parser.error("bounded ASCII name required")
    work = HERE / ".build" / args.name; work.mkdir(parents=True, exist_ok=False)
    out = HERE / "evidence" / args.name; out.mkdir(parents=True, exist_ok=False)
    env = {k:v for k,v in os.environ.items() if k in {"HOME", "USER", "LOGNAME", "PATH", "TMPDIR", "LANG", "TERM"} or k.startswith("LC_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    receipt = {"schema": 1, "reviewer": {"model": "gpt-6.1-sol", "reasoning_effort": "xhigh"},
               "source_revision": REVISION, "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "commands": [], "status": "running"}
    def run(name, argv, expected=0, extra=None, timeout=240):
        argv = [str(x) for x in argv]; start = time.monotonic()
        result = subprocess.run(argv, cwd=ROOT, env=extra or env, capture_output=True, timeout=timeout)
        logs = {}
        for kind, data in [("stdout", result.stdout), ("stderr", result.stderr)]:
            path = out / (name + "." + kind); path.write_bytes(data)
            logs[kind] = {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path), "bytes": len(data)}
        executable = Path(shutil.which(argv[0]) or argv[0]).resolve()
        receipt["commands"].append({"name": name, "argv": argv, "exit_code": result.returncode,
            "host_development_elapsed_seconds": round(time.monotonic()-start, 6), "output": logs,
            "executable": {"resolved_path": str(executable), "sha256": digest(executable)}})
        print(name + ": " + str(result.returncode), flush=True)
        if result.returncode != expected: raise RuntimeError("unexpected result: " + name)
        return result.stdout.decode()
    try:
        run("revision", ["/usr/bin/git", "rev-parse", REVISION + "^{commit}"])
        archive = work / "source.tar"
        run("export", ["/usr/bin/git", "archive", "--format=tar", "--output=" + str(archive), REVISION,
                       "runtime-identity", "updates", "activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json"])
        receipt["archive_sha256"] = digest(archive)
        source = work / "source"
        with tarfile.open(archive) as stream: stream.extractall(source, filter="data")
        manifest = {p.relative_to(source).as_posix(): digest(p) for p in sorted(source.rglob("*")) if p.is_file()}
        receipt["source_manifest"] = manifest
        receipt["source_digest"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        provenance_path = ROOT / "verification/runtime-embedding-2026-10-22/receipt.json"
        provenance = json.loads(provenance_path.read_bytes())
        tool = ROOT / "verification/local/runtime-embedding-2026-10-22/source/runtime-identity/.build/out/Products/Debug/mixer-identity"
        if provenance["sourceRevision"] != REVISION or digest(tool) != provenance["identityToolSHA256"]:
            raise ValueError("trusted root CLI source/hash mismatch")
        if any(provenance["sourceFiles"].get(k) != v for k,v in manifest.items()): raise ValueError("CLI provenance source mismatch")
        receipt["trusted_cli"] = {"path": str(tool), "sha256": digest(tool), "bytes": tool.stat().st_size,
            "root_receipt": provenance_path.relative_to(ROOT).as_posix(), "root_receipt_sha256": digest(provenance_path),
            "root_receipt_status": provenance["status"], "provenance_scope": "real public Swift CLI reused from same frozen source; no independent binary attestation"}
        receipt["python"] = run("python-version", [sys.executable, "--version"]).strip()
        receipt["swift"] = run("swift-version", [SWIFT, "--version"]).strip()
        receipt["os"] = run("host-os", ["/usr/bin/sw_vers"]).strip()
        receipt["review_files"] = {}
        for name in ["ReviewTests.py", "CompileProbe.py", "run.py"]:
            shutil.copyfile(HERE / name, out / name); receipt["review_files"][name] = digest(HERE / name)
        probe_env = dict(env, EMBED_REVIEW_SOURCE=str(source), EMBED_REVIEW_TOOL=str(tool),
                         EMBED_REVIEW_WORK=str(work), EMBED_REVIEW_OUTPUT=str(out), EMBED_REVIEW_SWIFT=str(SWIFT))
        for mode, flags in [("normal", []), ("optimized", ["-O"])]:
            run("independent-" + mode, [sys.executable, *flags, "-B", HERE / "ReviewTests.py"], extra=probe_env)
            log = (out / ("independent-" + mode + ".stderr")).read_text()
            match = re.search(r"Ran (\d+) tests? in ", log)
            if not match or not log.rstrip().endswith("OK"): raise ValueError("test receipt missing")
            receipt[mode + "_test_functions"] = int(match[1])
        run("compiled-consumer", [sys.executable, "-B", HERE / "CompileProbe.py"], extra=probe_env, timeout=600)
        receipt["compiled_probe"] = {"path": str((out / "compiled-receipt.json").relative_to(ROOT)), "sha256": digest(out / "compiled-receipt.json")}
        if any(digest(source / p) != sha for p,sha in manifest.items()): raise ValueError("review export changed")
        if digest(tool) != receipt["trusted_cli"]["sha256"]: raise ValueError("trusted CLI changed")
        receipt["source_unchanged"] = True
        receipt["status"] = "passed independent frozen host adversarial and compiled consumer review"
    except BaseException as error:
        receipt["status"] = "failed"; receipt["error"] = str(error); raise
    finally:
        receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(out / "receipt.json")}, indent=2))

if __name__ == "__main__": main()
