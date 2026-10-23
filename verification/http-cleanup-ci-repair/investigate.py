#!/usr/bin/env python3
"""Source-bound macOS HTTP fixture investigation. No product or device mutations."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
STATE = OUT / "investigation.json"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def manifest(root):
    entries = []
    for directory in ("sdk", "capabilities"):
        for path in sorted((root / directory).rglob("*")):
            if not path.is_file() or {".build", ".swiftpm", "verification", "__pycache__"}.intersection(path.relative_to(root).parts):
                continue
            entries.append(dict(path=str(path.relative_to(root)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size))
    entries.sort(key=lambda item: item["path"])
    return dict(digest=hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), files=entries)


def capture(args, cwd=ROOT, environment=None):
    return subprocess.run(args, cwd=cwd, env=os.environ | (environment or {}), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def save(state):
    STATE.write_text(json.dumps(state, indent=2) + "\n")


def run(state, name, args, environment=None, expected=0):
    started = now()
    result = capture(args, Path(state["snapshot"]), environment)
    output = OUT / (name + ".log")
    output.write_text(result.stdout)
    state["commands"].append(dict(name=name, command=args, cwd=state["snapshot"], environment=environment or {},
                                  startedAt=started, endedAt=now(), expectedExitCode=expected, exitCode=result.returncode,
                                  sourceDigest=manifest(Path(state["snapshot"]))["digest"], output=str(output.relative_to(ROOT)),
                                  outputSHA256=hashlib.sha256(output.read_bytes()).hexdigest()))
    save(state)
    print(json.dumps(dict(name=name, exitCode=result.returncode, expectedExitCode=expected, output=str(output)), indent=2), flush=True)
    return result


def init():
    if STATE.exists():
        raise RuntimeError("preserve existing investigation; do not replace its source-bound failed evidence")
    snapshot = Path(tempfile.mkdtemp(prefix="mixer-http-cleanup-ci-"))
    for directory in ("sdk", "capabilities"):
        shutil.copytree(ROOT / directory, snapshot / directory,
                        ignore=shutil.ignore_patterns(".build", ".swiftpm", "verification", "__pycache__"))
    original_test = capture(["git", "show", "f19cf9f:capabilities/Tests/MixerCapabilitiesTests/HTTPTransportTests.swift"])
    if original_test.returncode:
        raise RuntimeError("original hosted test source is required for the before/after reproduction")
    (snapshot / "capabilities/Tests/MixerCapabilitiesTests/HTTPTransportTests.swift").write_text(original_test.stdout)
    state = dict(createdAt=now(), snapshot=str(snapshot), sourceRevision=capture(["git", "rev-parse", "HEAD"]).stdout.strip(),
                 committedTree=capture(["git", "rev-parse", "HEAD^{tree}"]).stdout.strip(), initialSource=manifest(snapshot),
                 baselineTestSourceRevision="f19cf9f", sourceSnapshotOrigin="live sdk/capabilities source with the original hosted HTTP test restored from f19cf9f; all bytes bound by manifest",
                 environment=dict(swift=capture(["swift", "--version"]).stdout.strip(), xcode=capture(["xcodebuild", "-version"]).stdout.strip(),
                                  macOS=capture(["sw_vers"]).stdout.strip(),
                                  alternateSwift=capture(["/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift", "--version"]).stdout.strip()),
                 scope="Frozen sdk/capabilities macOS URLProtocol unit tests; no physical-device, production TLS, signing, or GA qualification", commands=[])
    (OUT / "original-HTTPTransportTests.swift.txt").write_bytes((snapshot / "capabilities/Tests/MixerCapabilitiesTests/HTTPTransportTests.swift").read_bytes())
    hosted = ROOT / "verification/github-ci-f19cf9f/swift.log"
    if hosted.exists():
        copy = OUT / "hosted-f19cf9f-swift.log"
        copy.write_bytes(hosted.read_bytes())
        state["hostedFailure"] = dict(revision="f19cf9f", runID=39988758316, jobID=120534733648,
                                       output=str(copy.relative_to(ROOT)), sha256=hashlib.sha256(copy.read_bytes()).hexdigest(),
                                       swift="6.2.4", xcode="26.3", exactHostedFailureBranch="unknown: original assertion combines activeRequests and stopCount without diagnostics")
    save(state)
    return state


def prove_pre_resume_expiry(state):
    snapshot = Path(state["snapshot"])
    path = snapshot / "capabilities/Tests/MixerCapabilitiesTests/HTTPTransportTests.swift"
    original = path.read_text()
    probe = """
// Investigation-only scheduler analogue. On the fourth monotonic read the
// session/task exists, but task.resume has not happened. Expiry is legal here.
private final class PreResumeExpiryProbeClock: @unchecked Sendable {
    private let lock = NSLock()
    private let initial = ContinuousClock.now
    private var reads = 0
    func now() -> ContinuousClock.Instant {
        lock.lock(); defer { lock.unlock() }
        reads += 1
        return reads < 4 ? initial : initial.advanced(by: .seconds(60))
    }
    var clock: HTTPTransportClock {
        HTTPTransportClock(now: { self.now() }, sleepUntil: { _ in
            try await Task.sleep(nanoseconds: 60_000_000_000)
        })
    }
}

"""
    old = """        let deadline = HTTPFixtureProtocol.registry.install(HTTPFixture(stall: true))
        await requireHTTPFailure(.deadlineExceeded, transport: transport, arguments: httpArguments(deadline, timeout: 30))
        try await eventuallyHTTP { transport.activeRequests == 0 && HTTPFixtureProtocol.registry.stopCount(deadline) == 1 }
"""
    replacement = """        let deadline = HTTPFixtureProtocol.registry.install(HTTPFixture(stall: true))
        let probeClock = PreResumeExpiryProbeClock()
        let deadlineTransport = try nativeTransport(capacity: 1, clock: probeClock.clock)
        await requireHTTPFailure(.deadlineExceeded, transport: deadlineTransport, arguments: httpArguments(deadline, timeout: 30))
        try await eventuallyHTTP { deadlineTransport.activeRequests == 0 }
        print("pre-resume-expiry: active=\\(deadlineTransport.activeRequests), starts=\\(HTTPFixtureProtocol.registry.observed(deadline).count), stops=\\(HTTPFixtureProtocol.registry.stopCount(deadline))")
        try await eventuallyHTTP { deadlineTransport.activeRequests == 0 && HTTPFixtureProtocol.registry.stopCount(deadline) == 1 }
"""
    if original.count(old) != 1:
        raise RuntimeError("probe must match exactly one original deadline branch")
    path.write_text(original.replace("@Suite(.serialized)\nstruct NativeHTTPTransportTests", probe + "@Suite(.serialized)\nstruct NativeHTTPTransportTests").replace(old, replacement))
    (OUT / "pre-resume-expiry-probe.diff").write_text(capture(["diff", "-u", str(OUT / "original-HTTPTransportTests.swift.txt"), str(path)]).stdout)
    try:
        run(state, "pre-resume-expiry-original-assertion", ["swift", "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-debug"),
                                                           "--filter", "cancellationDeadlineAndQuotaReleaseTheirNativeTasks"], expected=1)
    finally:
        path.write_text(original)
        state["snapshotRestoredAfterProbe"] = manifest(snapshot) == state["initialSource"]
        save(state)


if __name__ == "__main__":
    stage = sys.argv[1]
    state = init() if stage == "init" else json.loads(STATE.read_text())
    snapshot = Path(state["snapshot"])
    if stage == "baseline":
        run(state, "baseline-target-debug", ["swift", "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-debug"),
                                             "--filter", "cancellationDeadlineAndQuotaReleaseTheirNativeTasks"])
        run(state, "baseline-ci-filter-tsan", ["swift", "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-tsan"), "--sanitize", "thread",
                                               "--filter", "NativeCapabilityExitTests|NativeHTTPTransportTests|CapabilityHostDeadlineTests|CapabilityCarriedDeadlineTests"])
    elif stage == "probe":
        prove_pre_resume_expiry(state)
    elif stage == "repaired":
        if manifest(snapshot) != state["initialSource"]:
            raise RuntimeError("snapshot must contain the restored original before applying the owned test repair")
        relative = "capabilities/Tests/MixerCapabilitiesTests/HTTPTransportTests.swift"
        shutil.copy2(ROOT / relative, snapshot / relative)
        state["repairedSource"] = manifest(snapshot)
        state["repairDiff"] = capture(["git", "diff", "--", relative]).stdout
        save(state)
        run(state, "repaired-pre-resume-regression-debug", ["swift", "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-debug"),
                                                            "--filter", "deadlineBeforeNativeResumeReleasesLeaseWithoutProtocolStop"])
        run(state, "repaired-capability-debug", ["swift", "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-debug")])
        run(state, "repaired-capability-release", ["swift", "test", "--package-path", "capabilities", "-c", "release", "--scratch-path", str(snapshot / "build-release")])
        run(state, "repaired-ci-filter-tsan", ["swift", "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-tsan"), "--sanitize", "thread",
                                               "--filter", "NativeCapabilityExitTests|NativeHTTPTransportTests|CapabilityHostDeadlineTests|CapabilityCarriedDeadlineTests"])
        for iteration in range(1, 21):
            result = run(state, f"repaired-cleanup-tsan-repeat-{iteration:02}", ["swift", "test", "--skip-build", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-tsan"), "--sanitize", "thread",
                                                                                "--filter", "cancellationDeadlineAndQuotaReleaseTheirNativeTasks|deadlineBeforeNativeResumeReleasesLeaseWithoutProtocolStop"])
            if result.returncode:
                break
        state["repairedSourceUnchangedDuringRun"] = manifest(snapshot) == state["repairedSource"]
        save(state)
    elif stage == "alternate":
        environment = {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer", "TOOLCHAINS": "com.apple.dt.toolchain.XcodeDefault"}
        compiler = "/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
        run(state, "repaired-alternate-swift633-ci-filter-tsan", [compiler, "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-alternate-tsan"), "--sanitize", "thread",
                                                                 "--filter", "NativeCapabilityExitTests|NativeHTTPTransportTests|CapabilityHostDeadlineTests|CapabilityCarriedDeadlineTests"], environment)
        state["repairedSourceUnchangedDuringAlternateRun"] = manifest(snapshot) == state["repairedSource"]
        save(state)
    elif stage == "final":
        if manifest(snapshot) != state["repairedSource"]:
            raise RuntimeError("initial repair source changed before final assertion strengthening")
        relative = "capabilities/Tests/MixerCapabilitiesTests/HTTPTransportTests.swift"
        shutil.copy2(ROOT / relative, snapshot / relative)
        state["finalSource"] = manifest(snapshot)
        state["finalRepairDiff"] = capture(["git", "diff", "--", relative]).stdout
        save(state)
        run(state, "final-pre-resume-regression-debug", ["swift", "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-debug"),
                                                         "--filter", "deadlineBeforeNativeResumeReleasesLeaseWithoutProtocolStop"])
        run(state, "final-capability-debug", ["swift", "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-debug")])
        run(state, "final-capability-release", ["swift", "test", "--package-path", "capabilities", "-c", "release", "--scratch-path", str(snapshot / "build-release")])
        run(state, "final-ci-filter-tsan", ["swift", "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-tsan"), "--sanitize", "thread",
                                            "--filter", "NativeCapabilityExitTests|NativeHTTPTransportTests|CapabilityHostDeadlineTests|CapabilityCarriedDeadlineTests"])
        for iteration in range(1, 21):
            result = run(state, f"final-cleanup-tsan-repeat-{iteration:02}", ["swift", "test", "--skip-build", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-tsan"), "--sanitize", "thread",
                                                                             "--filter", "cancellationDeadlineAndQuotaReleaseTheirNativeTasks|deadlineBeforeNativeResumeReleasesLeaseWithoutProtocolStop"])
            if result.returncode:
                break
        environment = {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer", "TOOLCHAINS": "com.apple.dt.toolchain.XcodeDefault"}
        compiler = "/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
        run(state, "final-alternate-swift633-ci-filter-tsan", [compiler, "test", "--package-path", "capabilities", "--scratch-path", str(snapshot / "build-alternate-tsan"), "--sanitize", "thread",
                                                              "--filter", "NativeCapabilityExitTests|NativeHTTPTransportTests|CapabilityHostDeadlineTests|CapabilityCarriedDeadlineTests"], environment)
        state["finalSourceUnchangedDuringRun"] = manifest(snapshot) == state["finalSource"]
        state["finalSourceMatchesWorkspace"] = manifest(ROOT) == state["finalSource"]
        initial = {item["path"]: item["sha256"] for item in state["initialSource"]["files"]}
        final = {item["path"]: item["sha256"] for item in state["finalSource"]["files"]}
        state["changedSourceFiles"] = [path for path in sorted(set(initial) | set(final)) if initial.get(path) != final.get(path)]
        state["productTransportUnchanged"] = initial["sdk/Sources/MixerCapabilities/URLSessionHTTPTransport.swift"] == final["sdk/Sources/MixerCapabilities/URLSessionHTTPTransport.swift"]
        state["allCommandOutcomesExpected"] = all(command["exitCode"] == command["expectedExitCode"] for command in state["commands"])
        state["limitations"] = ["Exact hosted failed predicate remains unattributed because original assertion had no branch/state diagnostics.",
                                 "Deterministic probe establishes a legal ordering rejected by the old test; it does not prove that ordering caused the hosted incident.",
                                 "Hosted Swift6.2.4/Xcode26.3 is not locally installed; exact hosted compiler revalidation remains pending CI.",
                                 "macOS URLProtocol test evidence only; no physical iOS/Android, production TLS, signing, publication or GA gate claimed.",
                                 "TSan instruments owned compiled code; system URLSession implementation is opaque."]
        save(state)
    elif stage == "seal":
        final_commands = [command for command in state["commands"] if command["name"].startswith("final-")]
        repetitions = [command for command in final_commands if command["name"].startswith("final-cleanup-tsan-repeat-")]
        required = {"final-pre-resume-regression-debug", "final-capability-debug", "final-capability-release", "final-ci-filter-tsan", "final-alternate-swift633-ci-filter-tsan"}
        current = manifest(ROOT)
        probes = [command for command in state["commands"] if command["name"] == "pre-resume-expiry-original-assertion"]
        original_probe_rejected = (len(probes) == 1 and probes[0]["exitCode"] == probes[0]["expectedExitCode"] == 1
                                   and "pre-resume-expiry: active=0, starts=0, stops=0" in (ROOT / probes[0]["output"]).read_text()
                                   and "native transport did not acknowledge bounded cleanup" in (ROOT / probes[0]["output"]).read_text())
        records = []
        for command in final_commands:
            lines = (ROOT / command["output"]).read_text().splitlines()
            records.append(dict(name=command["name"], exitCode=command["exitCode"], sourceDigest=command["sourceDigest"],
                                observedSummary=next((line for line in lines if line.startswith("✔ Test run with ")), ""),
                                output=command["output"], outputSHA256=command["outputSHA256"]))
        scoped_pass = (state["allCommandOutcomesExpected"] and state["productTransportUnchanged"]
                       and original_probe_rejected and state["changedSourceFiles"] == ["capabilities/Tests/MixerCapabilitiesTests/HTTPTransportTests.swift"]
                       and state["finalSourceUnchangedDuringRun"] and current == state["finalSource"]
                       and len(repetitions) == 20 and required.issubset({command["name"] for command in final_commands})
                       and all(command["exitCode"] == 0 and command["sourceDigest"] == state["finalSource"]["digest"] for command in final_commands))
        receipt = dict(createdAt=now(), schemaVersion=1, scope=state["scope"], scopedChecksPassed=scoped_pass,
                       sourceRevision=state["sourceRevision"], committedTree=state["committedTree"],
                       initialSourceDigest=state["initialSource"]["digest"], finalSourceDigest=state["finalSource"]["digest"],
                       finalSourceMatchesWorkspace=current == state["finalSource"], changedSourceFiles=state["changedSourceFiles"],
                       productTransportUnchanged=state["productTransportUnchanged"], environment=state["environment"],
                       alternateXcode=capture(["xcodebuild", "-version"], environment={"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"}).stdout.strip(),
                       evidenceRunnerSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       detail="verification/http-cleanup-ci-repair/investigation.json", finalCommands=records,
                       originalAssertionProbeExpectedFailure=original_probe_rejected, exactHostedFailureBranchAttributed=False,
                       exactHostedCompilerRevalidation="pending CI; Swift6.2.4/Xcode26.3 not available locally", limitations=state["limitations"])
        (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(dict(scopedChecksPassed=scoped_pass, finalSourceDigest=receipt["finalSourceDigest"], finalCommands=len(records)), indent=2))
        sys.exit(0 if scoped_pass else 1)
    elif stage != "init":
        raise RuntimeError("unknown stage")
