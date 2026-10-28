#!/usr/bin/env python3
"""Read-only verification of fetched CI evidence; never imports artifact code."""
import hashlib
import json
from pathlib import Path
import platform
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARTIFACT = HERE / "artifact"
HEAD = "fb7c7f20f8a308424ef4b7092d19d3d4de2c7627"
TREE = "509093e0fcc9f4c83583f8d0ecd61b8b3c9d83d4"
CORRECTION = ROOT / "verification/swift-cache-deadline-campaign-v2-correction"
checked = []


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, name):
    if not condition:
        raise AssertionError(name)
    checked.append(name)


run = read(HERE / "run-metadata.json")
campaign = read(ARTIFACT / "campaign.json")
check(run["id"] == 40747548560 and run["head_sha"] == HEAD and run["head_commit"]["tree_id"] == TREE,
      "remote run bound to selected commit and tree")
check(run["run_attempt"] == 1 and run["event"] == "workflow_dispatch" and run["status"] == "completed" and run["conclusion"] == "failure",
      "first dispatch completed with failure")
check(campaign["githubSHA"] == HEAD and campaign["githubRunId"] == str(run["id"]) and campaign["githubRunAttempt"] == "1",
      "artifact campaign identity matches run")
metadata = read(HERE / "artifact-metadata.json")["artifacts"]
check(len(metadata) == 1 and metadata[0]["id"] == 12842671384,
      "single expected artifact")
archive_hash = digest(HERE / "artifact.zip")
check(metadata[0]["digest"] == "sha256:" + archive_hash and (HERE / "artifact.zip").stat().st_size == metadata[0]["size_in_bytes"],
      "downloaded archive digest and bytes match GitHub metadata")
extraction = read(HERE / "extraction.json")
check(extraction["fileCount"] == 31 and extraction["expandedBytes"] == 87292,
      "bounded extraction inventory")
for item in extraction["files"]:
    path = ARTIFACT / item["path"]
    check(path.stat().st_size == item["bytes"] and digest(path) == item["sha256"], "extracted bytes: " + item["path"])
seal_path = CORRECTION / "seal.json"
check(digest(seal_path) == "d8079bacfbb5fee222ac55354ad5a9aaa2a320327d50acd181426fea0d46a2d3", "selected correction seal unchanged")
seal = read(seal_path)
check(len(seal["files"]) == 15, "selected correction contains 15 sealed files")
for name, item in seal["files"].items():
    path = CORRECTION / name
    check(path.stat().st_size == item["bytes"] and digest(path) == item["sha256"], "selected source seal: " + name)
bindings = read(CORRECTION / "bindings.json")
check(campaign["inputBindings"] == bindings, "artifact input bindings match sealed local bindings")
for name, item in bindings.items():
    path = ROOT / name
    check(path.stat().st_size == item["bytes"] and digest(path) == item["sha256"], "bound source: " + name)
check(digest(ROOT / "verification/swift-cache-capacity-campaign-v1/campaign.py") == "5266e70df6e79054ffdc1abfc64b300d9f6252f11e55eb340716ab346bc4c556",
      "frozen v1 driver unchanged")
check((ROOT / ".github/workflows/swift-cache-deadline-campaign-v2.yml").read_bytes() == (CORRECTION / "workflow.yml").read_bytes(),
      "workflow matches correction source")
preflight = read(ARTIFACT / "preflight/check.json")
check(preflight["artifact"] == {"bytes": 53777114, "sha256": "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"},
      "original full guest identity retained in preflight")
expected_profiles = ["2f0973fe11f5db5341d2896d0e9a25b30a11687dedea5914547f5897c8161d28", "fd27e6b68e3d57226ad14855166a33f359664cd848fcc1918f3b3e265ffc8a39"]
check([p["sourceSHA256"] for p in preflight["profiles"]] == expected_profiles,
      "both selected source profile identities match")
check(read(ARTIFACT / "deadline-60-work-64m/source.json")["sha256"] == expected_profiles[0],
      "compiled primary source identity matches selected profile")
check(campaign["fullAttempts"] == 0 and campaign["profiles"] == [] and campaign["status"] == "stopped" and campaign["error"] == "finite control failed: finite",
      "zero full attempts; failure remains finite control")
check(not any(p.name in ("full", "harness-control") for p in ARTIFACT.rglob("*")),
      "no full-target or harness-control artifacts")
check(not (ARTIFACT / "deadline-60-work-128m").exists() and "conditionalSecondSelected" not in campaign,
      "conditional profile was neither evaluated nor executed")
command_paths = ["tools/rustc", "tools/cargo", "tools/python", "deadline-60-work-64m/build", "deadline-60-work-64m/finite"]
commands = []
for name in command_paths:
    directory = ARTIFACT / name
    receipt = read(directory / "receipt.json")
    check(type(receipt["pid"]) is int and receipt["pid"] > 0 and type(receipt["exitCode"]) is int
          and receipt["processGroupEmpty"] is True and receipt["timedOut"] is False and receipt["cancelled"] is None,
          "actual child exit and empty group: " + name)
    check(digest(directory / "stdout") == receipt["stdoutSHA256"] and digest(directory / "stderr") == receipt["stderrSHA256"],
          "command output hashes: " + name)
    commands.append({"command": name, **{k: receipt[k] for k in ("argv", "pid", "exitCode", "processGroupEmpty", "timedOut", "cancelled", "wallSeconds", "userSeconds", "systemSeconds", "peakRSSBytes")}})
check([c["exitCode"] for c in commands] == [0, 0, 0, 0, 101], "only finite suite failed among five invoked commands")
check(campaign["cleanup"]["ownedScratchRemoved"] is True and campaign["cleanup"]["commandCustodyUnresolved"] is False
      and campaign["cleanup"]["commandCustody"]["pendingCommand"] is None and campaign["cleanup"]["commandCustody"]["provenClosedCommands"] == 5
      and read(ARTIFACT / "custody.json") == campaign["cleanup"]["commandCustody"],
      "all five commands closed; remote owned scratch removed")
stderr = (ARTIFACT / "deadline-60-work-64m/finite/stderr").read_text()
stdout = (ARTIFACT / "deadline-60-work-64m/finite/stdout").read_text()
check("cache_tests.rs:4291:5" in stderr and "left: (100000000, 1000000000, 60000)" in stderr
      and "right: (100000000, 1000000000, 30000)" in stderr
      and "test result: FAILED. 3 passed; 1 failed; 0 ignored" in stdout,
      "original finite panic and 3/1 result preserved")
controls = ROOT / "verification/swift-cache-capacity-campaign-v1/campaign-controls.rs"
assertion = "    assert_eq!((b.instruction_fuel, b.execution_work, b.deadline_ms), (100_000_000, 1_000_000_000, 30_000));"
check(controls.read_text().splitlines()[86] == assertion, "exact stale deadline assertion at v1 campaign-controls.rs:87")
check('Ran 17 tests in 0.774s' in (HERE / "job.log").read_text(), "remote pure source controls ran 17 tests")

result = {"schema": 1, "status": "verified", "checksPassed": len(checked), "checks": checked,
          "source": {"head": HEAD, "tree": TREE, "correctionSealSHA256": digest(seal_path), "selectedProfiles": expected_profiles},
          "commands": commands, "reviewTool": {"python": sys.version, "platform": platform.platform()},
          "scope": "offline evidence verification only; no artifact source execution, compiler, guest, native runtime, custody probes, UI or dispatch"}
(HERE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "checksPassed": len(checked), "fullAttempts": campaign["fullAttempts"], "firstFailure": campaign["error"]}))
