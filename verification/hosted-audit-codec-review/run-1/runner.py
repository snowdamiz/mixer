#!/usr/bin/env python3
"""Independent frozen overlay replay; writes only this review and owned scratch."""
import datetime
import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / "verification/hosted-audit-codec-integration"
sha = lambda b: hashlib.sha256(b).hexdigest()


def main():
    output = HERE / ("run-" + str(int(sys.argv[1])))
    output.mkdir(exist_ok=False)
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="mixer-audit-codec-review-"))
    project = scratch / "project"
    hosted = project / "hosted"
    hosted.mkdir(parents=True)
    env = dict(os.environ, ERL_FLAGS="+S 2:2", HEX_OFFLINE="1", MIX_ENV="test",
               GIT_DIR=str(ROOT / ".git"), GIT_WORK_TREE=str(ROOT))
    commands = []
    status = "failed"
    dependencies = []
    baseline = {}

    def run(label, argv, cwd=hosted, timeout=300):
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=timeout)
            code, log = result.returncode, result.stdout
        except subprocess.TimeoutExpired as error:
            code, log = 124, (error.stdout or b"") + b"\nREVIEW: timeout\n"
        path = output / (label + ".log")
        path.write_bytes(log)
        commands.append({"label": label, "argv": list(map(str, argv)), "cwd": str(cwd),
                         "startedUTC": started, "exitCode": code, "log": path.name, "sha256": sha(log)})
        print(json.dumps({"command": label, "exitCode": code}), flush=True)
        if code:
            raise RuntimeError(str(path))
        return log

    def snapshot(name):
        manifest = {str(p.relative_to(project)): sha(p.read_bytes()) for p in sorted(project.rglob("*"))
                    if p.is_file() and not {"deps", "_build", "__pycache__"}.intersection(p.relative_to(project).parts)}
        (output / (name + ".json")).write_text(json.dumps(manifest, indent=2) + "\n")
        with tarfile.open(output / (name + ".tar.gz"), "w:gz") as archive:
            for path in manifest:
                archive.add(project / path, arcname=path, recursive=False)
        return manifest

    try:
        revision = run("revision", ["git", "rev-parse", "HEAD"], ROOT).decode().strip()
        run("producer-check", ["python3", "-B", str(CANDIDATE / "check.py")], ROOT)
        producer = json.loads((CANDIDATE / "run-5/receipt.json").read_text())
        baseline = producer["baselineInputs"]
        assert set(baseline) == set(subprocess.check_output(["git", "ls-files", "hosted"], cwd=ROOT).decode().splitlines())
        for path, digest in baseline.items():
            body = (ROOT / path).read_bytes()
            assert sha(body) == digest, path
            destination = project / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
        overlay = json.loads((CANDIDATE / "receipt.json").read_text())["overlay"]
        for path, digest in overlay.items():
            body = (CANDIDATE / "candidate" / path).read_bytes()
            assert sha(body) == digest, path
            destination = hosted / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
        for name in ("signed-release-v3.json", "release-v3-cases.json"):
            path = "services/protocol/testdata/" + name
            destination = project / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / path).read_bytes())
        tested = snapshot("overlay-source")
        assert tested == producer["testedSource"]
        # The previously bound locked-package inventory is rechecked against archive bytes
        # and every extracted source file. No dependency source or version is changed.
        expected = json.loads((CANDIDATE / "run-5/dependencies.json").read_text())
        for package in expected:
            archive_path = pathlib.Path.home() / ".hex/packages/hexpm" / (package["name"] + "-" + package["version"] + ".tar")
            body = archive_path.read_bytes()
            assert sha(body) == package["archiveSHA256"]
            with tarfile.open(fileobj=io.BytesIO(body)) as archive:
                assert archive.extractfile("CHECKSUM").read().decode().strip().lower() == package["innerChecksum"]
                content = archive.extractfile("contents.tar.gz").read()
            files = {}
            with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
                for member in archive.getmembers():
                    if member.isdir():
                        continue
                    path = pathlib.PurePosixPath(member.name)
                    assert member.isfile() and not path.is_absolute() and ".." not in path.parts
                    value = archive.extractfile(member).read()
                    files[member.name] = sha(value)
                    destination = hosted / "deps" / package["name"] / member.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(value)
                    destination.chmod(member.mode & 0o777)
            assert files == package["files"]
            dependencies.append(package)
        assert len(dependencies) == 21
        (output / "dependencies.json").write_text(json.dumps(dependencies, indent=2) + "\n")
        run("python-version", ["python3", "--version"])
        run("elixir-version", ["elixir", "--version"])
        run("mix-version", ["mix", "--version"])
        run("platform", ["uname", "-a"])
        run("dependencies", ["mix", "deps.get", "--check-locked"])
        assert sha((hosted / "mix.lock").read_bytes()) == baseline["hosted/mix.lock"]
        for package in dependencies:
            for name, digest in package["files"].items():
                assert sha((hosted / "deps" / package["name"] / name).read_bytes()) == digest
        run("dependencies-compile", ["mix", "deps.compile"])
        run("compile", ["mix", "compile", "--warnings-as-errors"])
        run("producer-focused", ["mix", "test", "test/mixer_hosted/audit/upload_event_test.exs", "--warnings-as-errors", "--seed", "0", "--trace"])
        run("full-hosted", ["python3", "-B", "scripts/test-local.py", "--output", str(output / "full-hosted")], timeout=600)
        full = json.loads((output / "full-hosted/receipt.json").read_text())
        assert full["status"] == "passed" and all(full["cleanup"].values()) and full["inputs"] == tested
        # Keep the full regression replay at the original exact overlay; independent
        # reviewer tests are added only after it has completed.
        review = hosted / "test/independent_review"
        review.mkdir()
        for name in ("independent_test.exs", "independent-vectors.json"):
            shutil.copy2(HERE / name, review / name)
        run("review-format", ["mix", "format", str(review / "independent_test.exs")])
        shutil.copy2(review / "independent_test.exs", output / "formatted-independent_test.exs")
        independent_source = snapshot("independent-source")
        run("independent-focused", ["mix", "test", "test/independent_review/independent_test.exs", "--warnings-as-errors", "--seed", "0", "--trace"])
        env["REVIEW_VECTORS"] = str(HERE / "independent-vectors.json")
        run("key-bound-probe", ["mix", "run", "--no-start", str(HERE / "key-bound-probe.exs")])
        assert all(sha((ROOT / p).read_bytes()) == v for p, v in baseline.items())
        status = "passed"
    finally:
        shutil.rmtree(scratch)
        result = {"schema": 1, "status": status, "sourceRevision": locals().get("revision"),
                  "baselineInputs": baseline, "overlayInputs": locals().get("tested"),
                  "independentInputs": locals().get("independent_source"), "commands": commands,
                  "cleanup": {"ownedScratchRemoved": not scratch.exists()},
                  "dependencyCount": len(dependencies),
                  "environment": {"ERL_FLAGS": "+S 2:2", "HEX_OFFLINE": "1", "MIX_ENV": "test",
                                  "git": "Read-only original revision observation, no Git mutations."},
                  "scope": "Independent pure codec review; full accepted hosted regression/release replay. Captured audit SQL rows only; no fresh audit SQL, authorization composition, migration, HTTP, provider, native or GA acceptance."}
        (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": status, "cleanup": result["cleanup"]}), flush=True)


if __name__ == "__main__":
    main()
