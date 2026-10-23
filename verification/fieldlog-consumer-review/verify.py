#!/usr/bin/env python3
"""Independent scoped review of the frozen separate FieldLog consumer; no devices."""
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LOGS = OUT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
FIELDLOG = ROOT.parent / "fieldlog"
REVISION = "dd68d3dbd61be15860282d79f710a8f58b001e92"
IMPLEMENTATION = "d51adf50de7e20549e87062e4569609342cdfe25"
DEPENDENCY = "d8c6965a277ca21e685f3ef9e0f68a7d59b46156"
URL = "https://github.com/snowdamiz/mixer.git"


def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(data): return hashlib.sha256(data).hexdigest()
def capture(args, cwd=ROOT):
    return subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
def git(*args):
    result = capture(["git", *args], FIELDLOG)
    if result.returncode: raise ValueError(result.stdout)
    return result.stdout.strip()
def require(value, message):
    if not value: raise ValueError(message)


def manifest(folder, paths):
    entries = [{"path": str(path), "bytes": (folder / path).stat().st_size, "sha256": sha((folder / path).read_bytes())} for path in sorted(paths)]
    return dict(algorithm="SHA256 of canonical JSON source entries sorted by path", digest=sha(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()), files=entries)


def run(name, args, scope, expected_functions):
    started = now()
    result = capture(args)
    output = LOGS / (name + ".log")
    output.write_text(result.stdout)
    counts = re.findall(r"Test run with (\d+) tests? in", result.stdout)
    functions = sum(int(count) for count in counts)
    parameterized = re.findall(r"with (\d+) test cases passed", result.stdout)
    cases = functions + sum(int(count) - 1 for count in parameterized)
    return dict(name=name, command=args, cwd=str(ROOT), startedAt=started, endedAt=now(), exitCode=result.returncode,
                output=str(output.relative_to(ROOT)), outputSHA256=sha(output.read_bytes()), scope=scope,
                observedFunctions=functions, observedCases=cases, expectedFunctions=expected_functions,
                countMatches=functions == expected_functions)


before_head, before_status = git("rev-parse", "HEAD"), git("status", "--porcelain=v1")
archive = subprocess.check_output(["git", "archive", "--format=tar", REVISION], cwd=FIELDLOG)
source_tree = git("rev-parse", REVISION + "^{tree}")
review_test = OUT / "IndependentTaskEditorTests.swift"
commands = []
with tempfile.TemporaryDirectory(prefix="fieldlog-consumer-review-") as temporary:
    export = Path(temporary) / "fieldlog"
    export.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream: stream.extractall(export, filter="data")
    paths = [path.relative_to(export) for path in export.rglob("*") if path.is_file()]
    original = manifest(export, paths)
    require((export / "Package.swift").read_text().count(URL) == 1, "unexpected dependency origin")
    lock = json.loads((export / "Package.resolved").read_text())
    xcode_lock = json.loads((export / "ios/FieldLog.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved").read_text())
    for value in [lock, xcode_lock]:
        require(len(value["pins"]) == 1 and value["pins"][0]["kind"] == "remoteSourceControl" and value["pins"][0]["location"] == URL
                and value["pins"][0]["state"]["revision"] == DEPENDENCY, "package lock is not the frozen remote dependency")
    commands.append(run("baseline-host", ["swift", "test", "--package-path", str(export)], "unchanged frozen separate consumer; remote public package resolved through SwiftPM cache", 17))
    checkout = export / ".build/checkouts/mixer"
    resolved_revision = capture(["git", "-C", str(checkout), "rev-parse", "HEAD"]).stdout.strip()
    resolved_tree = capture(["git", "-C", str(checkout), "rev-parse", "HEAD^{tree}"]).stdout.strip()
    workspace_state = json.loads((export / ".build/workspace-state.json").read_text())
    resolved = workspace_state["object"]["dependencies"]
    require(len(resolved) == 1 and resolved[0]["packageRef"]["kind"] == "remoteSourceControl"
            and resolved[0]["packageRef"]["location"] == URL and resolved_revision == DEPENDENCY
            and resolved[0]["state"]["checkoutState"]["revision"] == DEPENDENCY, "resolved dependency differs from public pin")
    shutil.copyfile(review_test, export / "Tests/FieldLogTests/IndependentTaskEditorTests.swift")
    commands.append(run("combined-host", ["swift", "test", "--package-path", str(export)], "17 original plus10 independent functions/12 independent cases; original app sources unchanged", 27))
    commands.append(run("independent-release", ["swift", "test", "--package-path", str(export), "-c", "release", "--filter", "IndependentTaskEditorTests"], "ten independent functions/twelve cases under release optimization", 10))
    commands.append(run("independent-thread-sanitizer", ["swift", "test", "--package-path", str(export), "--scratch-path", str(Path(temporary) / "tsan"),
                         "--sanitize", "thread", "--filter", "IndependentTaskEditorTests"], "ten independent functions/twelve cases; owned consumer and public SDK code instrumented, system frameworks not instrumented", 10))
    original_unchanged = original == manifest(export, paths)
    review_unchanged = sha(review_test.read_bytes()) == sha((export / "Tests/FieldLogTests/IndependentTaskEditorTests.swift").read_bytes())

previous_path = FIELDLOG / "verification/mixer-core-consumer/receipt.json"
previous = json.loads(previous_path.read_text())
prior_source = []
for entry in previous["sourceFiles"]:
    actual = subprocess.check_output(["git", "show", REVISION + ":" + entry["path"]], cwd=FIELDLOG)
    prior_source.append(dict(path=entry["path"], sha256=sha(actual), matches=sha(actual) == entry["sha256"]))
prior_evidence = []
for entry in previous["evidenceFiles"]:
    data = (previous_path.parent / entry["path"]).read_bytes()
    prior_evidence.append(dict(path=str((previous_path.parent / entry["path"]).relative_to(FIELDLOG)), bytes=len(data), sha256=sha(data),
                               matches=sha(data) == entry["sha256"] and len(data) == entry["bytes"]))
summary = json.loads((previous_path.parent / "simulator-summary.json").read_text())
cross_path = FIELDLOG / "verification/mixer-core-consumer-cross/receipt.json"
cross = json.loads(cross_path.read_text())
cross_logs = []
for command in cross["commands"]:
    path = cross_path.parent / command["output"]
    cross_logs.append(dict(path=str(path.relative_to(FIELDLOG)), sha256=sha(path.read_bytes()), matches=sha(path.read_bytes()) == command["outputSHA256"]))
unchanged_since_baseline = git("diff", "--name-only", IMPLEMENTATION + "^", IMPLEMENTATION, "--", "Sources/FieldLogModels", "Sources/FieldLogStorage", "ios/FieldLogUITests") == ""
implementation_unchanged = git("diff", "--name-only", IMPLEMENTATION, REVISION, "--", "AGENTS.md", "Package.swift", "Package.resolved", "Sources", "Tests", "ios", "README.md") == ""
after_head, after_status = git("rev-parse", "HEAD"), git("status", "--porcelain=v1")
receipt = dict(schemaVersion=1, createdAt=now(), reviewer=dict(model="gpt-6.1-sol", reasoningEffort="xhigh", independent=True),
    mixerHeadAtReview=capture(["git", "rev-parse", "HEAD"]).stdout.strip(),
    fieldlog=dict(repository=str(FIELDLOG), reviewedRevision=REVISION, implementationRevision=IMPLEMENTATION, committedTree=source_tree,
        archiveFormat="git archive --format=tar", archiveSHA256=sha(archive), exportedSource=original,
        sourceUnchangedDuringTests=original_unchanged, productionWorkingTreeUnchanged=before_head == after_head and before_status == after_status,
        observedHeadBefore=before_head, observedHeadAfter=after_head, observedStatusBefore=before_status, observedStatusAfter=after_status,
        changesSinceImplementationAreEvidenceOnly=implementation_unchanged),
    dependency=dict(url=URL, revision=DEPENDENCY, resolvedRevision=resolved_revision, resolvedTree=resolved_tree,
        declaredKind="remoteSourceControl", resolvedFrom="SwiftPM remote source-control cache; not a fresh independent network download", product="MixerCore", target="FieldLogFeatures",
        packageAndXcodeLocksMatch=True, localMixerOverride=False, privateSDKImports=False,
        xcodeOwnAppPackageReference="../ is FieldLog's own local package, not a Mixer checkout"),
    addedTests=dict(path=str(review_test.relative_to(ROOT)), sha256=sha(review_test.read_bytes()), unchangedDuringTests=review_unchanged,
        productionFilesModified=False, independentFunctions=10, independentCases=12), commands=commands,
    previousEvidence=dict(consumerReceipt=str(previous_path), consumerReceiptSHA256=sha(previous_path.read_bytes()),
        sourceEntries=prior_source, evidenceEntries=prior_evidence, sourceSchemaAndUITestUnchangedAcrossAdoption=unchanged_since_baseline,
        simulatorSummary=dict(result=summary["result"], totalTests=summary["totalTestCount"], failedTests=summary["failedTests"],
            skippedTests=summary["skippedTests"], runtimeWarnings=len(summary["runtimeWarnings"])),
        screenshotsVisuallyReviewed=["02-checklist-completed-and-reordered.png", "03-restored-lossless-draft.png"],
        screenshotScope="Previously recorded simulator evidence; no new UI or physical run in this independent review",
        crossReceiptSHA256=sha(cross_path.read_bytes()), crossLogs=cross_logs, crossExecuted=False),
    observations=[
        "TaskEditor uses only public pinned MixerCore FeatureStore/Effect APIs; native form remains SwiftUI, without MixerUI migration",
        "Native observer synchronously copies value state only; onChange(saved) dismisses, onDisappear removes observation then closes the owner. Independent synchronous saved observer removal/close is safe; reducer reentry rejects",
        "Actual save closure awaits WorkspaceModel.addTask -> enqueue task.value -> WorkspaceRepository.transact -> file sync/rename/directory sync before returning saved; no optimistic success path observed",
        "Failure preserves exact title/responsible input; retries can succeed after correction, duplicate submits cannot admit concurrent saves, and saved owners cannot resubmit",
        "Uncertain persistence faults before file sync/after rename/after directory sync never claim success. Poisoned repository refuses duplicate retry; reopen preserves old state or one complete new task/outbox",
        "Closing an unsaved form does not invoke persistence. Closing after an authorized commit suppresses late results while retaining the durable task. Closing may not prevent an already submitted cancellation-ignoring callback from starting; no rollback guarantee inferred"
    ],
    findings=[dict(id="FIELDLOG-REVIEW-01", severity="P3", status="confirmed documentation contradiction; coordinated with root for scoped follow-up",
        file="README.md", line=5, description="Opening paragraph says no Mixer SDK dependency, contradicting pinned public MixerCore adoption and the later correct README text",
        requestedChange="Replace stale opening sentence with precise public MixerCore adoption scope; no behavioral implementation change required")],
    behavioralBlockersConfirmed=0,
    tools=dict(host=platform.platform(), python=sys.version, swift=capture(["swift", "--version"]).stdout.strip(), xcode=capture(["xcodebuild", "-version"]).stdout.strip()),
    reviewRunnerSHA256=sha(Path(__file__).read_bytes()),
    limitations=[
        "Host tests cover actual TaskEditor and WorkspaceRepository through public APIs; NewTaskView/WorkspaceModel positive integration is supported by source review and prior unchanged simulator workflow, not fresh independent UI execution",
        "No new UI cancellation/storage-failure automation, physical iOS/Android run, performance, account/network/photo/upload/store/customer or production workflow qualification",
        "Existing Android/WASI receipts prove source/object compilation only; no guest linking, VM validation/execution, Android app or interpreted parity",
        "Public Git revision dependency consumption only, with no stable release tag/API guarantee; FieldLog remains local separate repository without remote publication claim",
        "MixerUI adoption, D0-D8, signed binary/store evidence and all GA gates remain open; this is a scoped independent adoption review"
    ], deviceCommandsAttempted=False, externalMessagesSent=False, fieldlogProductionChanges=False, D1Accepted=False, GAAccepted=False)
receipt["scopedChecksPassed"] = (original_unchanged and review_unchanged and receipt["fieldlog"]["productionWorkingTreeUnchanged"] and implementation_unchanged and unchanged_since_baseline
    and all(command["exitCode"] == 0 and command["countMatches"] for command in commands)
    and all(entry["matches"] for entry in prior_source + prior_evidence + cross_logs))
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(dict(passed=receipt["scopedChecksPassed"], revision=REVISION, tree=source_tree, archiveSHA256=sha(archive), sourceDigest=original["digest"],
                     commands=[dict(name=command["name"], exitCode=command["exitCode"], functions=command["observedFunctions"], cases=command["observedCases"]) for command in commands], findings=receipt["findings"]), indent=2))
sys.exit(0 if receipt["scopedChecksPassed"] else 1)
