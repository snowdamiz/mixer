#!/usr/bin/env python3
"""Verify source-bound fixture/output repair evidence without replaying it."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PARENT = "dd604eca4d3c01ade0dce084aedb2571978632ad"
bindings = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    path = ROOT / name
    bindings[name] = sha(path.read_bytes())
    return json.loads(path.read_text())


def verify_manifest(name):
    document = read(name)
    files = document["files"]
    assert sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()) == document["treeDigest"]
    for path, digest in files.items():
        assert sha((ROOT / path).read_bytes()) == digest, path
        bindings[path] = digest
    return files


one_line = verify_manifest("verification/hosted-tls-fixture-ci-repair/evidence-manifest.json")
final_linux = verify_manifest("verification/hosted-identity-metrics-output-check/evidence-manifest.json")
final = read("verification/hosted-identity-metrics-output-check/receipt.json")
assert final["observation"]["passed"] == 46
assert final["observation"]["invalid"] == final["observation"]["skipped"] == 0
assert final["observation"]["allNineMetricsInExplicitDirectory"]
assert not final["observation"]["legacyEvidencePathCreated"]
assert final["observation"]["privateTmpAbsentBeforeAndAfter"]
assert all(final["frozenPriorPacketsUnchanged"].values())
assert final["cleanup"]["scratchRemoved"] and not final["cleanup"]["ownedContainerRetained"]

sources = read("verification/hosted-identity-metrics-output-check/linux-final/source-manifest.json")["files"]
for path, digest in sources.items():
    assert sha((ROOT / path).read_bytes()) == digest, path

tracked = set(subprocess.check_output(["git", "ls-tree", "-r", "--name-only", PARENT, "hosted"], cwd=ROOT, text=True).splitlines())
generated = sorted(set(sources) - tracked)
assert generated == ["hosted/scripts/__pycache__/test-local.cpython-314.pyc"], generated
changed = []
for path, digest in sources.items():
    if path in generated:
        continue
    if sha(subprocess.check_output(["git", "show", PARENT + ":" + path], cwd=ROOT)) != digest:
        changed.append(path)
expected = {
    "hosted/test/support/identity_tls_fixture.ex",
    "hosted/scripts/test-local.py",
    "hosted/test/mixer_hosted/identity/key_owner_test.exs",
    "hosted/test/mixer_hosted/identity/key_owner_linux_network_test.exs",
}
assert set(changed) == expected, changed

for number in (1, 2):
    prefix = f"verification/hosted-tls-fixture-ci-root-review/host-{number}"
    result = read(prefix + "/receipt.json")
    assert result["status"] == "passed"
    assert result["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
    assert "Result: 73 passed, 1 skipped" in (ROOT / prefix / "tests.log").read_text()
    for command in result["commands"]:
        assert command["exit_code"] == command.get("expected_exit_code", 0), command
        assert sha((ROOT / prefix / command["log"]).read_bytes()) == command["sha256"]
    archive_path = ROOT / prefix / "source.tar.gz"
    assert sha(archive_path.read_bytes()) == result["source_archive_sha256"]
    with tarfile.open(archive_path) as archive:
        assert set(archive.getnames()) == set(result["inputs"])
        for member in archive.getmembers():
            assert member.isfile()
            assert sha(archive.extractfile(member).read()) == result["inputs"][member.name]
    if number == 2:
        delta = {name for name, digest in result["inputs"].items()
                 if sha((ROOT / name).read_bytes()) != digest}
        assert delta == {"hosted/test/mixer_hosted/identity/key_owner_linux_network_test.exs"}, delta
        assert len(list((ROOT / prefix / "identity-metrics").glob("*.json"))) == 8

unset = read("verification/hosted-tls-fixture-ci-root-review/unset-output/receipt.json")
assert unset["exitCode"] == 0 and unset["frozenPacketUnchanged"]
assert "Result: 1 passed, 28 excluded" in (OUT / "unset-output/tests.log").read_text()
for name, digest in unset["before"].items():
    assert sha((ROOT / name).read_bytes()) == digest, name
    assert sha(subprocess.check_output(["git", "show", PARENT + ":" + name], cwd=ROOT)) == digest

for path in sorted(OUT.rglob("*")):
    if path.is_file() and path.name != "acceptance.json":
        bindings[str(path.relative_to(ROOT))] = sha(path.read_bytes())
receipt = {
    "schema": 1,
    "status": "root-accepted-test-fixture-portability-and-run-local-observations",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "sourceRevision": PARENT,
    "finalSourceTreeSHA256": final["sourceTreeDigest"],
    "changedFiles": sorted(expected),
    "productionSourcesAndDependenciesUnchanged": True,
    "generatedInputsExcludedFromGitComparison": generated,
    "checks": {
        "oneLineRepair": "45 macOS and 46 Linux cases; /private/tmp absent on Linux",
        "fullHosted": "73 passed, 1 Linux-namespace case skipped; production release/missing-config and PostgreSQL cleanup passed",
        "finalLinux": "46 passed, no skips/invalids; all nine metrics in explicit run directory",
        "unsetOutput": "one actual publication fixture passes and leaves frozen packet unchanged; 28 other cases excluded",
        "composition": "host-2 predates only the Linux test output helper; final Linux matrix exercises that exact changed file. No full Mac rerun of the final Linux-only file is claimed",
        "sourceArchiveInputs": 56,
    },
    "scope": "Four test/collector files only. No identity algorithm, authenticated HTTP, membership, provider, native or GA acceptance. Hosted CI rerun remains pending push.",
    "review": "Root reviewed exact diff: platform tmp parent only; nine JSON output destinations moved behind explicit test-only environment setting; all assertions and measured expressions preserved. Original failed CI and collector failures remain retained.",
    "commands": [["python3", str(Path(__file__).relative_to(ROOT))]],
    "pythonVersion": sys.version,
    "bindings": bindings,
}
target = OUT / "acceptance.json"
assert not target.exists()
target.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "bindings": len(bindings)}))
