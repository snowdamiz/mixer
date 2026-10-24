#!/usr/bin/env python3
"""Replay the exact two hosted candidates together without changing live source."""
from pathlib import Path
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = "552d4caecec6550c09af62f03fe6c4ab4842d251"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    number = 1
    while (HERE / f"run-{number}").exists():
        number += 1
    out = HERE / f"run-{number}"
    out.mkdir()
    scratch = Path(tempfile.mkdtemp(prefix="mixer-hosted-composed-", dir="/private/tmp"))
    commands, dependencies, sources, changed = [], [], {}, []
    status, cleanup = "failed", {}
    key_receipt = ROOT / "verification/hosted-key-owner-implementation/receipt.json"
    dep_selection = ROOT / "verification/hosted-key-owner-root-review/selection.json"
    artifact_seal = ROOT / "verification/hosted-artifact-admission-implementation/seal.json"
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in
              [Path(__file__).resolve(), key_receipt, dep_selection, artifact_seal,
               ROOT / "hosted/scripts/test-local.py", ROOT / ".github/workflows/hosted.yml"]}

    def run(label, argv, cwd, env=None):
        log = out / (label + ".log")
        started = time.monotonic()
        with log.open("wb") as stream:
            try:
                result = subprocess.run(argv, cwd=cwd, env=env, stdout=stream,
                                        stderr=subprocess.STDOUT, timeout=600)
                code = result.returncode
            except subprocess.TimeoutExpired:
                stream.write(b"\nROOT COLLECTOR: 600-second deadline exceeded\n")
                code = 124
        commands.append({"label": label, "argv": argv, "cwd": str(cwd),
                         "exitCode": code, "elapsedSeconds": time.monotonic() - started,
                         "log": log.name, "sha256": sha(log)})
        assert code == 0, f"{label} failed: {log}"

    try:
        archive = subprocess.check_output(["git", "archive", BASE, "--", "hosted",
                                           "services/protocol/testdata"], cwd=ROOT)
        tarfile.open(fileobj=io.BytesIO(archive)).extractall(scratch, filter="data")
        subprocess.run(["git", "init", "-q", str(scratch)], check=True)
        objects = subprocess.check_output(["git", "rev-parse", "--path-format=absolute",
                                           "--git-path", "objects"], cwd=ROOT, text=True).strip()
        (scratch / ".git/objects/info/alternates").write_text(objects + "\n")
        subprocess.run(["git", "-C", str(scratch), "update-ref", "refs/heads/main", BASE], check=True)
        subprocess.run(["git", "-C", str(scratch), "symbolic-ref", "HEAD", "refs/heads/main"], check=True)
        # The immutable key-owner receipt covers every new identity module and
        # fixture; accepted pure files are copied only after matching their hash.
        for name, expected in read(key_receipt)["bindings"].items():
            if name.startswith("hosted/") and "/deps/" not in name:
                source = ROOT / name
                assert sha(source) == expected, name
                destination = scratch / name
                if not destination.exists() or sha(destination) != expected:
                    changed.append(name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
        for name in ["hosted/mix.exs", "hosted/mix.lock"]:
            assert sha(ROOT / name) == read(dep_selection)["bindings"][name], name
            shutil.copyfile(ROOT / name, scratch / name)
            changed.append(name)
        overlay = ROOT / "verification/hosted-artifact-admission-implementation/overlay"
        for source in sorted(overlay.rglob("*")):
            if source.is_file():
                name = str(source.relative_to(overlay))
                destination = scratch / name
                assert not destination.exists(), name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                changed.append(name)
        shutil.copyfile(ROOT / "hosted/scripts/test-local.py", scratch / "hosted/scripts/test-local.py")
        changed.append("hosted/scripts/test-local.py")
        # Product fixtures write only observed metrics below their own isolated
        # checkout; never replay them against a frozen evidence directory.
        (scratch / "verification/hosted-key-owner-implementation").mkdir(parents=True)
        for source in sorted((scratch / "hosted").rglob("*")):
            if source.is_file():
                sources[str(source.relative_to(scratch))] = sha(source)
        for name in ["signed-release-v3.json", "release-v3-cases.json"]:
            p = scratch / "services/protocol/testdata" / name
            sources[str(p.relative_to(scratch))] = sha(p)
        with tarfile.open(out / "source.tar.gz", "w:gz") as tar:
            for name in sources:
                tar.add(scratch / name, arcname=name, recursive=False)
        for line in (scratch / "hosted/mix.lock").read_text().splitlines():
            match = re.match(r'  "([^"]+)": \{:hex, :[^,]+, "([^"]+)".*"([0-9a-f]{64})"\},', line)
            if not match:
                continue
            name, version, expected = match.groups()
            package = Path.home() / ".hex/packages/hexpm" / f"{name}-{version}.tar"
            assert sha(package) == expected, name
            with tarfile.open(package) as tar:
                payload = tar.extractfile("contents.tar.gz").read()
            destination = scratch / "hosted/deps" / name
            destination.mkdir(parents=True)
            tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz").extractall(destination, filter="data")
            dependencies.append({"name": name, "version": version, "archiveSHA256": expected})
        assert len(dependencies) == 21
        env = dict(os.environ, HEX_OFFLINE="1", MIX_ENV="test", ERL_CRASH_DUMP_SECONDS="0",
                   ERL_CRASH_DUMP=str(scratch / "erl_crash.dump"))
        run("python-version", ["python3", "--version"], scratch)
        run("offline-dependencies", ["mix", "deps.get", "--check-locked"], scratch / "hosted", env)
        run("full-hosted-integration", ["python3", "scripts/test-local.py", "--output",
                                       str(out / "hosted")], scratch / "hosted", env)
        receipt = read(out / "hosted/receipt.json")
        assert receipt["status"] == "passed" and receipt["inputs"] == sources
        assert receipt["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
        log = (out / "hosted/tests.log").read_text()
        match = re.search(r"(\d+) tests?, (\d+) failures?(?:, (\d+) skipped)?", log)
        assert match and tuple(int(n or 0) for n in match.groups()) == (74, 0, 1), match.groups() if match else log[-500:]
        assert all(sha(scratch / name) == h for name, h in sources.items())
        metrics = scratch / "verification/hosted-key-owner-implementation"
        shutil.copytree(metrics, out / "replayed-key-owner-metrics")
        status = "passed"
    finally:
        # The nested collector owns PostgreSQL cleanup. Preserve an unexpected
        # live-database failure for investigation rather than deleting its data.
        nested = out / "hosted/receipt.json"
        assert not nested.exists() or read(nested)["cleanup"]["postgres_stopped"], "Nested PostgreSQL cleanup failed"
        shutil.rmtree(scratch)
        cleanup = {"isolatedCheckoutRemoved": not scratch.exists(), "nativeInstancesStarted": False,
                   "otherProjectProcessesTouched": False, "liveHostedSourceUnchanged": True}
        result = {"schema": 1, "status": status, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "baseRevision": BASE, "collectorInputs": inputs, "sourceInputs": sources,
                  "changedSourcePaths": sorted(set(changed)), "dependencies": dependencies,
                  "commands": commands, "cleanup": cleanup,
                  "scope": "Composed key-owner and artifact-admission host regression, packaged release, evidence fixture coverage; no Application wiring, authenticated HTTP, membership/storage, provider, native or GA acceptance.",
                  "excluded": "One Linux production network-namespace test is skipped on macOS; its actual Linux executions are separately retained in producer/independent key-owner packets."}
        (out / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": status, "output": str(out), "cleanup": cleanup}))


if __name__ == "__main__":
    main()
