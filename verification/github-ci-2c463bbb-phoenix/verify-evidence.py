#!/usr/bin/env python3
"""Verify downloaded CI bytes without executing or importing hosted sources."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent
REVISION = "2c463bbbacf196c564e2ca758381462353ef70a9"
ENGINE_REVISION = "e8ab06649f122862f3ef4e3c68124af2da1af744"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*argv):
    return subprocess.run(["git", *argv], cwd=ROOT, capture_output=True, check=True).stdout


def write(path, value):
    if path.exists():
        raise RuntimeError(f"Refusing to overwrite existing evidence: {path}")
    path.write_text(json.dumps(value, indent=2) + "\n")


observed = datetime.datetime.now(datetime.timezone.utc).isoformat()
artifact = DEST / "artifact"
receipt_bytes = (artifact / "receipt.json").read_bytes()
receipt = json.loads(receipt_bytes)
assert receipt["status"] == "passed"
inputs = receipt["inputs"]
assert sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_tree_sha256"]
assert sha((artifact / "source.tar.gz").read_bytes()) == receipt["source_archive_sha256"]
archive_inputs = {}
with tarfile.open(artifact / "source.tar.gz", "r:gz") as source:
    for member in source.getmembers():
        assert member.isfile() and member.name not in archive_inputs
        assert not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
        archive_inputs[member.name] = sha(source.extractfile(member).read())
assert archive_inputs == inputs

committed_files = git("ls-tree", "-r", "--name-only", REVISION, "--", "hosted").decode().splitlines()
expected_paths = set(committed_files) | {
    "services/protocol/testdata/signed-release-v3.json",
    "services/protocol/testdata/release-v3-cases.json",
}
assert set(inputs) == expected_paths
rows = []
for name, expected in inputs.items():
    committed = sha(git("show", f"{REVISION}:{name}"))
    assert committed == expected, name
    current = ROOT / name
    rows.append({"path": name, "receiptSHA256": expected,
                 "archiveSHA256": archive_inputs[name], "committedSHA256": committed,
                 "currentWorktreeSHA256": sha(current.read_bytes()) if current.is_file() else None})

current_inputs = {
    str(p.relative_to(ROOT)): sha(p.read_bytes())
    for p in sorted((ROOT / "hosted").rglob("*"))
    if p.is_file() and p.name != "erl_crash.dump"
    and not {"_build", "deps", "__pycache__", "cover"}.intersection(p.relative_to(ROOT / "hosted").parts)
}
for name in ("signed-release-v3.json", "release-v3-cases.json"):
    path = ROOT / "services/protocol/testdata" / name
    current_inputs[str(path.relative_to(ROOT))] = sha(path.read_bytes())
current_digest = sha(json.dumps(current_inputs, sort_keys=True, separators=(",", ":")).encode())
changed = [row["path"] for row in rows if row["currentWorktreeSHA256"] != row["receiptSHA256"]]
added = sorted(set(current_inputs) - set(inputs))
removed = sorted(set(inputs) - set(current_inputs))
head = git("rev-parse", "HEAD").decode().strip()
source_comparison = {
    "schema": 1, "observedUTC": observed, "revision": REVISION,
    "revisionTree": git("rev-parse", REVISION + "^{tree}").decode().strip(),
    "currentHEAD": head, "currentHEADTree": git("rev-parse", "HEAD^{tree}").decode().strip(),
    "sourceTreeSHA256": receipt["source_tree_sha256"],
    "currentHostedAndSharedFixturesSHA256": current_digest,
    "sourceArchiveSHA256": receipt["source_archive_sha256"],
    "committedAndArchivedInputsVerified": len(rows), "inputs": rows,
    "currentHostedAndSharedFixtureInputs": current_inputs,
    "currentWorktreeComparison": {"identical": not (changed or added or removed),
                                  "changed": changed, "added": added, "removed": removed},
    "commands": [["git", "ls-tree", "-r", "--name-only", REVISION, "--", "hosted"],
                 ["git", "show", REVISION + ":<each-receipt-input>"],
                 ["git", "rev-parse", "HEAD", "HEAD^{tree}", REVISION + "^{tree}"]],
    "scope": "Static byte hashing of archived, committed and current hosted inputs plus the two shared protocol fixtures. No hosted source or test was executed or imported. This does not extend CI coverage beyond its exact archived input set."
}
write(DEST / "source-comparison.json", source_comparison)

logs = []
for command in receipt["commands"]:
    path = artifact / command["log"]
    assert path.parent == artifact
    actual = sha(path.read_bytes())
    assert actual == command["sha256"], command["label"]
    assert command["exit_code"] == command.get("expected_exit_code", 0), command["label"]
    logs.append({"label": command["label"], "log": command["log"], "sha256": actual,
                 "exitCode": command["exit_code"], "expectedExitCode": command.get("expected_exit_code", 0)})
assert (artifact / "revision.log").read_text().strip() == REVISION
assert receipt["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
assert "server stopped" in (artifact / "postgres-stop.log").read_text()
tests = (artifact / "tests.log").read_text()
summaries = re.findall(r"^Result: (\d+) passed, (\d+) skipped$", tests, flags=re.MULTILINE)
assert len(summaries) == 1
passed, skipped = map(int, summaries[0])
skipped_tests = [line.strip() for line in tests.splitlines() if "(skipped)" in line]
assert len(skipped_tests) == skipped == 2
tests_command = next(row for row in receipt["commands"] if row["label"] == "tests")
assert tests_command["argv"] == ["mix", "test", "--warnings-as-errors", "--seed", "0", "--trace"]
for name in ("key_owner_linux_network_test.exs", "startup_linux_network_test.exs"):
    path = "hosted/test/mixer_hosted/identity/" + name
    source_text = git("show", f"{REVISION}:{path}").decode()
    assert 'System.get_env("MIXER_ISOLATED_NETNS") == "1"' in source_text
    assert ':os.type() == {:unix, :linux}' in source_text

workflow = git("show", REVISION + ":.github/workflows/hosted.yml")
(DEST / "workflow.yml").write_bytes(workflow)
assert "--additional-test" not in workflow.decode()
workflow_current = (ROOT / ".github/workflows/hosted.yml").read_bytes()
run = json.loads((DEST / "run.json").read_bytes())
run_command = json.loads((DEST / "run-command.json").read_bytes())
review = {
    "schema": 1, "observedUTC": observed, "status": "accepted-linux-host-ci",
    "revision": REVISION, "ciRun": "40149405000", "url": run["url"],
    "sourceTreeSHA256": receipt["source_tree_sha256"],
    "sourceArchiveSHA256": receipt["source_archive_sha256"],
    "committedAndArchivedInputsVerified": len(rows), "commandLogsVerified": len(logs),
    "commandLogs": logs, "testsPassed": passed, "testsSkipped": skipped,
    "testsCommand": tests_command["argv"], "skippedTests": skipped_tests,
    "skipReason": "The two identity tests require Linux and MIXER_ISOLATED_NETNS=1 from the isolated network namespace collector. Ordinary GitHub host CI does not activate that fixture; both tests remain skipped.",
    "testSelection": "Repository suite only: workflow supplied no --additional-test argument and recorded mix test argv supplied no explicit independent review test paths. Independently executed local review tests are separate evidence and are not included in this count.",
    "collectorTestSelectionField": receipt.get("test_selection"),
    "cleanup": receipt["cleanup"],
    "cleanupVerification": "Archived postgres-stop command exited 0 and log contains server stopped; archived collector receipt reports scratch_removed=true. No remote filesystem probe was performed after CI teardown.",
    "tools": {name: (artifact / name).read_text().strip() for name in
              ("elixir-version.log", "postgres-version.log", "postgres-timezone.log")},
    "reviewTools": {"gh": run_command["toolVersion"],
                    "git": subprocess.run(["git", "--version"], capture_output=True, text=True, check=True).stdout.strip(),
                    "python": subprocess.run(["python3", "--version"], capture_output=True, text=True, check=True).stdout.strip()},
    "workflow": {"path": ".github/workflows/hosted.yml", "archive": "workflow.yml",
                 "sha256": sha(workflow), "identicalToCurrentWorktree": workflow == workflow_current,
                 "runner": "ubuntu-24.04"},
    "artifactReceiptSHA256": sha(receipt_bytes),
    "currentWorktreeComparison": source_comparison["currentWorktreeComparison"],
    "currentHostedAndSharedFixturesSHA256": current_digest,
    "sourceComparison": "source-comparison.json",
    "verifier": "verify-evidence.py", "verifierSHA256": sha(Path(__file__).read_bytes()),
    "scope": "Exact pushed hosted sources and repository tests on Linux with real disposable PostgreSQL16 and packaged release checks. Independent local review tests are separate evidence. No isolated-network tests, native runtime, real provider, cloud operational, external-effect or GA acceptance.",
    "limitations": receipt["limitations"],
}
write(DEST / "host-evidence-review.json", review)

for folder, revision, workflow_path, scope in [
    ("github-ci-e8ab0664-engine", ENGINE_REVISION, ".github/workflows/verify.yml",
     "Engine host CI across GitHub macos-15 Swift and ubuntu-24.04 VM/services jobs. Job and step success are verified from GitHub run metadata; Engine artifact contents and detailed command logs were not downloaded or independently replayed in this review. No physical-native, simulator/emulator, production or GA qualification."),
    ("github-ci-2c463bbb-phoenix", REVISION, ".github/workflows/hosted.yml",
     "Linux host CI only; archived source, logs and disposable PostgreSQL receipt verified in host-evidence-review.json. No isolated-network, native runtime, cloud operational or GA qualification."),
]:
    dest = ROOT / "verification" / folder
    run = json.loads((dest / "run.json").read_bytes())
    command = json.loads((dest / "run-command.json").read_bytes())
    assert run["headSha"] == revision and run["status"] == "completed" and run["conclusion"] == "success"
    assert all(job["status"] == "completed" and job["conclusion"] == "success" for job in run["jobs"])
    steps = [step for job in run["jobs"] for step in job["steps"]]
    content = git("show", revision + ":" + workflow_path)
    if not (dest / "workflow.yml").exists():
        (dest / "workflow.yml").write_bytes(content)
    else:
        assert (dest / "workflow.yml").read_bytes() == content
    result = {
        "schema": 1, "observedUTC": command["observedUTC"], "revision": revision,
        "revisionTree": git("rev-parse", revision + "^{tree}").decode().strip(),
        "argv": command["argv"], "toolVersion": command["toolVersion"], "exitCode": command["exitCode"],
        "url": run["url"], "status": "passed", "runStatus": run["status"],
        "conclusion": run["conclusion"], "jobs": len(run["jobs"]),
        "successfulSteps": sum(step["conclusion"] == "success" for step in steps),
        "skippedSteps": sum(step["conclusion"] == "skipped" for step in steps),
        "runSHA256": sha((dest / "run.json").read_bytes()),
        "stderrSHA256": sha((dest / "run.stderr").read_bytes()),
        "workflow": {"path": workflow_path, "archive": "workflow.yml", "sha256": sha(content)},
        "jobNames": [job["name"] for job in run["jobs"]], "scope": scope,
    }
    write(dest / "receipt.json", result)

print(json.dumps({"status": "verified", "sourceTreeSHA256": receipt["source_tree_sha256"],
                  "inputs": len(rows), "logs": len(logs), "testsPassed": passed, "testsSkipped": skipped,
                  "currentWorktreeComparison": source_comparison["currentWorktreeComparison"]}, indent=2))
