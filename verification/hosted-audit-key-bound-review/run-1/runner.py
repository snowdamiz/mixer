#!/usr/bin/env python3
"""Independent, isolated correction review. Never writes candidate or live code."""
import datetime
import difflib
import hashlib
import io
import json
import os
import pathlib
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORRECTION = ROOT / "verification/hosted-audit-key-bound-correction"
ORIGINAL = ROOT / "verification/hosted-audit-codec-integration"
OLDREVIEW = ROOT / "verification/hosted-audit-codec-review"
RECEIPT_SHA = "c04cae984dd88344dc3933ad58b5f8c01c07eecf33cf22cf9266c494555d7c53"
MODULE_SHA = "daff6c6084be7094bc1a2b97ae386d5fcd4390e245c99f6de77f09572c07f6ad"
sha = lambda body: hashlib.sha256(body).hexdigest()


def read(path):
    return json.loads(path.read_text())


def verified_archive(path, manifest):
    result = {}
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        assert len(members) == len(manifest) == len({m.name for m in members})
        for member in members:
            name = pathlib.PurePosixPath(member.name)
            assert member.isfile() and not name.is_absolute() and ".." not in name.parts
            body = archive.extractfile(member).read()
            assert member.name in manifest and sha(body) == manifest[member.name], member.name
            result[member.name] = body
    return result


def main():
    output = HERE / ("run-" + str(int(sys.argv[1])))
    output.mkdir(exist_ok=False)
    shutil.copy2(HERE / "run.py", output / "runner.py")
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="mixer-audit-key-independent-"))
    project = scratch / "project"
    hosted = project / "hosted"
    hosted.mkdir(parents=True)
    commands = []
    status = "failed"
    inputs = {}
    reviewed_inputs = {}
    integrity = {}
    dependencies = []
    env = dict(os.environ, ERL_FLAGS="+S 2:2", HEX_OFFLINE="1", MIX_ENV="test")
    # No source-control operation is needed inside the isolated project.
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)

    def run(label, argv, cwd=hosted, timeout=300):
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=timeout)
            code, log = result.returncode, result.stdout
        except subprocess.TimeoutExpired as error:
            code, log = 124, (error.stdout or b"") + b"\nINDEPENDENT REVIEW: timeout\n"
        path = output / (label + ".log")
        path.write_bytes(log)
        commands.append({"label": label, "argv": list(map(str, argv)), "cwd": str(cwd),
                         "startedUTC": started, "exitCode": code, "log": path.name,
                         "sha256": sha(log)})
        print(json.dumps({"command": label, "exitCode": code}), flush=True)
        if code:
            raise RuntimeError(str(path))
        return log

    def snapshot(name):
        manifest = {str(path.relative_to(project)): sha(path.read_bytes())
                    for path in sorted(project.rglob("*")) if path.is_file()
                    and not {"deps", "_build", "__pycache__"}.intersection(path.relative_to(project).parts)}
        (output / (name + ".json")).write_text(json.dumps(manifest, indent=2) + "\n")
        with tarfile.open(output / (name + ".tar.gz"), "w:gz") as archive:
            for name in manifest:
                archive.add(project / name, arcname=name, recursive=False)
        return manifest

    try:
        revision = run("revision", ["git", "rev-parse", "HEAD"], ROOT).decode().strip()
        run("python-version", ["python3", "--version"])
        run("elixir-version", ["elixir", "--version"])
        run("mix-version", ["mix", "--version"])
        run("platform", ["uname", "-a"])
        assert sha((CORRECTION / "receipt.json").read_bytes()) == RECEIPT_SHA
        run("correction-check", ["python3", "-B", str(CORRECTION / "check.py")], ROOT)
        run("original-check", ["python3", "-B", str(ORIGINAL / "check.py")], ROOT)
        run("original-review-check", ["python3", "-B", str(OLDREVIEW / "check.py")], ROOT)

        correction = read(CORRECTION / "receipt.json")
        corrected_run = read(CORRECTION / "run-1/receipt.json")
        inputs = read(CORRECTION / "run-1/overlay-source.json")
        assert inputs == corrected_run["overlayInputs"]
        corrected_source = verified_archive(CORRECTION / "run-1/overlay-source.tar.gz", inputs)
        independent_manifest = read(CORRECTION / "run-1/independent-source.json")
        independent_source = verified_archive(CORRECTION / "run-1/independent-source.tar.gz", independent_manifest)
        for name, digest in inputs.items():
            assert independent_manifest[name] == digest
        original_run = read(ORIGINAL / "run-5/receipt.json")
        original_source = verified_archive(ORIGINAL / "run-5/source.tar.gz", original_run["testedSource"])
        assert set(original_source) == set(corrected_source)
        changed = sorted(name for name in corrected_source if original_source[name] != corrected_source[name])
        source_name = "hosted/lib/mixer_hosted/audit/upload_event.ex"
        test_name = "hosted/test/mixer_hosted/audit/upload_event_test.exs"
        assert changed == [source_name, test_name]
        original_module = original_source[source_name].decode()
        corrected_module = corrected_source[source_name].decode()
        assert sha(corrected_source[source_name]) == MODULE_SHA
        expected = original_module.replace("Enum.sort(Map.keys(row)) == Enum.sort(@row_keys)",
                                           "Enum.all?(@row_keys, &Map.has_key?(row, &1))").replace(
                    "Enum.sort(Map.keys(d)) == Enum.sort(@display_keys)",
                    "Enum.all?(@display_keys, &Map.has_key?(d, &1))")
        assert expected == corrected_module
        for name in (source_name, test_name):
            diff = "".join(difflib.unified_diff(original_source[name].decode().splitlines(True),
                                               corrected_source[name].decode().splitlines(True),
                                               fromfile="original/" + name, tofile="corrected/" + name))
            (output / ("implementation.diff" if name == source_name else "focused-test.diff")).write_text(diff)
        assert corrected_run["baselineInputs"] == original_run["baselineInputs"]
        for name, body in independent_source.items():
            destination = project / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
        # Reused full-hosted/release evidence is accepted only for this exact
        # unchanged overlay, with all archive and command output hashes verified.
        full = read(CORRECTION / "run-1/full-hosted/receipt.json")
        assert full["status"] == "passed" and all(full["cleanup"].values())
        assert full["inputs"] == inputs
        assert verified_archive(CORRECTION / "run-1/full-hosted/source.tar.gz", full["inputs"]) == corrected_source
        for command in full["commands"]:
            assert command["exit_code"] == command.get("expected_exit_code", 0)
            assert sha((CORRECTION / "run-1/full-hosted" / command["log"]).read_bytes()) == command["sha256"]

        dependencies = read(CORRECTION / "run-1/dependencies.json")
        assert dependencies == read(ORIGINAL / "run-5/dependencies.json")
        assert dependencies == read(OLDREVIEW / "run-2/dependencies.json")
        assert len(dependencies) == 21
        for package in dependencies:
            package_archive = pathlib.Path.home() / ".hex/packages/hexpm" / (package["name"] + "-" + package["version"] + ".tar")
            body = package_archive.read_bytes()
            assert sha(body) == package["archiveSHA256"]
            with tarfile.open(fileobj=io.BytesIO(body)) as archive:
                assert archive.extractfile("CHECKSUM").read().decode().strip().lower() == package["innerChecksum"]
                content = archive.extractfile("contents.tar.gz").read()
            with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
                source = {}
                for member in archive.getmembers():
                    if member.isdir():
                        continue
                    path = pathlib.PurePosixPath(member.name)
                    assert member.isfile() and not path.is_absolute() and ".." not in path.parts
                    value = archive.extractfile(member).read()
                    source[member.name] = sha(value)
                    destination = hosted / "deps" / package["name"] / member.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(value)
                    destination.chmod(member.mode & 0o777)
                assert source == package["files"]
        shutil.copy2(CORRECTION / "run-1/dependencies.json", output / "dependencies.json")
        run("dependencies", ["mix", "deps.get", "--check-locked"])
        assert sha((hosted / "mix.lock").read_bytes()) == inputs["hosted/mix.lock"]
        for package in dependencies:
            assert all(sha((hosted / "deps" / package["name"] / name).read_bytes()) == digest
                       for name, digest in package["files"].items())
        run("dependencies-compile", ["mix", "deps.compile"])
        run("compile", ["mix", "compile", "--warnings-as-errors"])
        run("producer-focused", ["mix", "test", "test/mixer_hosted/audit/upload_event_test.exs",
                                 "--warnings-as-errors", "--seed", "0", "--trace"])
        run("retained-independent", ["mix", "test", "test/independent_review/independent_test.exs",
                                      "--warnings-as-errors", "--seed", "0", "--trace"])
        own = hosted / "test/key_bound_review"
        own.mkdir()
        shutil.copy2(HERE / "key_shape_review_test.exs", own / "key_shape_review_test.exs")
        renamed = original_module.replace("defmodule MixerHosted.Audit.UploadEvent do",
                                           "defmodule MixerHosted.Audit.OriginalUploadEventByReview do", 1)
        assert renamed != original_module
        (own / "original_upload_event.exs").write_text(renamed)
        run("review-format", ["mix", "format", str(own / "key_shape_review_test.exs")])
        shutil.copy2(own / "key_shape_review_test.exs", output / "formatted-key_shape_review_test.exs")
        reviewed_inputs = snapshot("review-source")
        run("new-independent", ["mix", "test", "test/key_bound_review/key_shape_review_test.exs",
                                 "--warnings-as-errors", "--seed", "0", "--trace"])
        env["REVIEW_VECTORS"] = str(hosted / "test/independent_review/independent-vectors.json")
        shutil.copy2(CORRECTION / "key-bound-probe.exs", output / "key-bound-probe.exs")
        timing = run("key-bound-probe", ["mix", "run", "--no-start", str(output / "key-bound-probe.exs")])
        measures = json.loads(timing)["measurements"]
        assert len(measures) == 36 and all(m["result"] == "rejected" and m["calls"] == 20 for m in measures)
        timing_medians = {label: {str(size): statistics.median(m["elapsed_microseconds"] for m in measures
                            if m["label"] == label and m["key_or_value_bytes"] == size)
                            for size in (1024, 1048576, 4194304)} for label in {m["label"] for m in measures}}
        # Confirm all tested accepted source bytes survived formatting and tests.
        assert all(sha((project / name).read_bytes()) == digest for name, digest in independent_manifest.items())
        assert sha((CORRECTION / "receipt.json").read_bytes()) == RECEIPT_SHA
        integrity = {"frozenCorrectionReceiptSHA256": RECEIPT_SHA,
                     "reviewedModuleSHA256": MODULE_SHA,
                     "baselineFilesUnchanged": len(corrected_run["baselineInputs"]),
                     "overlaySourceFiles": len(inputs), "onlyChangedFilesVersusOriginal": changed,
                     "implementationDelta": "Exactly two fixed-key membership expressions; no other module byte changed.",
                     "frozenOriginalModuleSHA256": sha(original_source[source_name]),
                     "artifactEncoderSHA256": inputs["hosted/lib/mixer_hosted/protocol/artifact_cbor.ex"],
                     "mixLockSHA256": inputs["hosted/mix.lock"],
                     "dependencyInventoryUnchanged": True,
                     "reusedFullHostedReceiptSHA256": sha((CORRECTION / "run-1/full-hosted/receipt.json").read_bytes()),
                     "reusedFullHostedSourceManifestExactMatch": True,
                     "reusedFullHostedResults": {"passed": 105, "linuxOnlySkipped": 2,
                       "releaseBuild": "passed", "missingConfigurationExpectedRejection": "passed",
                       "productionTestExportExclusion": "passed"}}
        (output / "integrity.json").write_text(json.dumps(integrity, indent=2) + "\n")
        status = "passed"
    finally:
        shutil.rmtree(scratch)
        result = {"schema": 1, "status": status, "sourceRevision": locals().get("revision"),
                  "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "sourceInputs": inputs, "reviewInputs": reviewed_inputs,
                  "commands": commands, "dependencyCount": len(dependencies), "integrity": integrity,
                  "timingMediansMicrosecondsPer20Calls": locals().get("timing_medians"),
                  "cleanup": {"ownedScratchRemoved": not scratch.exists(),
                              "noNativeInstancesStarted": True, "noDatabaseOrListenerStartedByReview": True},
                  "freshResults": {"focusedTests": 12, "retainedIndependentTests": 6,
                     "retainedCoherentCases": 107, "retainedEdges": 8, "newReviewTests": 2} if status == "passed" else None,
                  "environment": {"ERL_FLAGS": "+S 2:2", "HEX_OFFLINE": "1", "MIX_ENV": "test"},
                  "fullHostedAndRelease": "Exact-source correction evidence reused; not rerun by this review.",
                  "scope": "Independent pure codec correction review. Captured PostgreSQL rows only; no SQL authority, migration, provider, UI, native, physical phone, production publication, or GA acceptance."}
        (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": status, "cleanup": result["cleanup"]}), flush=True)


if __name__ == "__main__":
    main()
