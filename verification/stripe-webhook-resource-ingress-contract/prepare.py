#!/usr/bin/env python3
"""Author the proposal packet. Does not launch the proposed resource harness."""
import datetime
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


baseline_path = ROOT / "verification/stripe-webhook-transport-regressions/acceptance.json"
baseline = json.loads(baseline_path.read_text())
assert len(baseline["sourceInputs"]) == 73
assert baseline["sourceDigest"] == "1b2f03d474f825a6265e0a10f9baf2adda62dffe6c747542207f32753b4df997"
for path, expected in baseline["sourceInputs"].items():
    assert digest(ROOT / path) == expected, path

profile = {
    "schema": 1,
    "id": "mixer-private-webhook-linux-basic-comparison-v1",
    "selection": "proposal-root-selection-pending",
    "productionActivated": False,
    "publicTrailerPolicy": "unselected",
    "dependenciesAdded": [],
    "logical": {"connections": 16, "streamsPerConnection": 1, "requestsPerConnection": 1,
                "handshakeMs": 1000, "headersMs": 1000, "captureMs": 5000,
                "outerMs": 7000, "maxBodyBytes": 1048576},
    "cgroup": {"version": 2, "memory.max": 1073741824, "memory.high": 805306368,
               "memory.swap.max": 0, "memory.oom.group": 1,
               "cpu.max": "25000 100000", "cpu.weight": 100, "pids.max": 128},
    "rlimits": {"nofileSoft": 256, "nofileHard": 256, "coreSoft": 0,
                "coreHard": 0, "fsizeSoft": 0, "fsizeHard": 0},
    "beam": {"flags": ["+S", "2:2", "+SDcpu", "1", "+SDio", "1", "+A", "2",
                       "+P", "32768", "+Q", "1024", "-start_epmd", "false"],
             "distributed": False, "crashDump": "/dev/null", "crashDumpSeconds": 0},
    "isolation": {"network": "owned-loopback-only-namespace", "defaultRoutes": 0,
                  "externalEgress": False, "inheritedDescriptors": [0, 1, 2],
                  "capabilitiesAfterExec": [], "writableHostMounts": [],
                  "mountNamespace": "owned-private-propagation-readonly-sealed-root",
                  "pidNamespace": "owned-recorded-reaper",
                  "environment": "minimal-fixed-no-controller-inheritance",
                  "readOnlyRoot": True, "tmpfsBytes": 8388608,
                  "coreCollector": "must-verify-disabled-no-unknown-retention"},
    "controller": {"caseWallMs": 120000, "suiteWallMs": 900000,
                   "termGraceMs": 2000, "emptyCgroupByMs": 2500,
                   "sampleTargetMs": 20, "stdoutMaxBytes": 1048576,
                   "stderrMaxBytes": 1048576, "concurrentRoles": 1,
                   "unavailableExit": 78, "outsideStressedCgroup": True},
    "faultBounds": {"oomTouchMaxBytes": 1342177280, "oomInjectorWallMs": 30000,
                    "taskCreateAttempts": 160, "fdOpenAttempts": 320,
                    "cpuBurnWallMs": 5000, "overflowClients": 32,
                    "wireMaxSentBytesPerCase": 33554432},
    "reasonEnum": ["completed", "capability_unavailable", "profile_invalid", "source_mismatch",
                   "delegation", "cgroup_readback", "ancestor_limit", "namespace",
                   "descriptor_limit", "dump_policy", "output_schema", "output_overflow",
                   "deadline", "memory_pressure", "oom", "cpu_throttled", "task_limit",
                   "fd_limit", "shutdown", "ownership", "cleanup", "runtime_error", "ingress_mismatch"],
    "caseReceiptFields": ["caseId", "status", "reason", "profileDigest", "sourceDigest",
                          "releaseDigest", "environmentDigest", "startedMonotonicNs",
                          "elapsedNs", "cgroupBefore", "cgroupAfter", "samples",
                          "termination", "outputAudit", "cleanup"],
    "caseStatusEnum": ["passed", "failed", "unavailable"],
    "closedControlTuples": ["ready(generation,port)", "stop(generation)", "stopped(generation,reason)"]
}
write("profile.json", profile)
write("profile.schema.json", {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Closed fixed development proposal; no overrides",
    "type": "object", "const": profile,
    "description": "Exact JSON type and value equality required. A changed field needs root reselection."
})

matrix = []


def case(case_id, gate, environment, requirement, evidence):
    matrix.append({"id": case_id, "gate": gate, "environment": environment,
                   "status": "pending-runtime", "requirement": requirement,
                   "requiredEvidence": evidence})


for row in [
    ("R01", "Reject every profile/schema/unknown-field/type/source mismatch before launch", "Negative cases; no role PID/listener; fixed safe refusal"),
    ("R02", "Reject absent/delegation/controller/ancestor/readback/ownership or writable-limit ambiguity", "Effective cgroup files/ancestor inventory; exact unavailable versus failed reasons"),
    ("R03", "Boot one sealed Linux release and read back limits before opening private admission", "Linux architecture/libc/ERTS/OpenSSL/compiler/image digest; task/FD/cgroup baseline"),
    ("R04", "Replay selected exact capture/framing/signature arguments at 1 byte and 1 MiB", "H1 CL/chunked; H2 optional CL; only synthetic 418; prior matrix retained"),
    ("R05", "Exercise 16 occupied slots and 32 overflow clients without relaxing limits", "Client outcomes; live registry, socket FD, task and memory counters; no second verifier"),
    ("R06", "Exercise large DATA/CONTINUATION, decoded header expansion and bounded malformed floods", "At most 32 MiB sent per case; cgroup peak plus sampled heap/binary/mailbox/RSS; exact refusal"),
    ("R07", "Freeze/slow the original H2 reader and queue DATA while keeping control traffic active", "20ms-target sampled actual times; cgroup memory/current/peak; no claim sampled peak is absolute"),
    ("R08", "Replay 1s/5s/7s stage and whole-connection cancellation under fixed quota", "Original owners DOWN and peer closure; exact overshoot; no late success; failure does not widen deadlines"),
    ("R09", "Demonstrate CPU quota throttles a bounded 5s burner in the role cgroup", "cpu.stat usage/throttled deltas and wall time; distinguish throttling from deadline qualification"),
    ("R10", "Reach pids.max with at most 160 bounded task attempts", "pids.current/events and EAGAIN; BEAM processes distinguished from OS tasks; recovery or clean stop"),
    ("R11", "Reach inherited FD/socket-descriptor limit with at most 320 opens", "Per-process limits, EMFILE and socket-inode/FD counts; listener/supervisor recovery or clean stop"),
    ("R12", "Deny external IPv4/IPv6/DNS and inherited management sockets", "Owned namespace routes/caps/FD inventory and finite failed egress attempts; no external destination contacted"),
    ("R13", "Trigger cgroup OOM using bounded helper in the role cgroup", "memory.events oom_kill delta, peak, exit/signal, empty cgroup and peer closure; exit 137 alone insufficient"),
    ("R14", "SIGTERM during idle, H1 body, frozen H2 reader and blocked response", "Admission gate closed before shutdown; zero cgroup tasks/socket closure by 2500ms; exact duration"),
    ("R15", "Freeze whole VM or ignore TERM and invoke external kill fallback", "2000ms grace then whole-cgroup kill; controller survives; descendants gone by 2500ms"),
    ("R16", "Crash with raw body/signature/trailer sentinels present", "No core/erl_crash.dump; verified dump collector disabled; output allowlist and safe reason retained"),
    ("R17", "Inject unknown output, overflow or telemetry/Logger drift", "Terminate on unknown schema/1MiB pipe overflow; no rejected raw bytes persisted; drift not relabeled leak prevention"),
    ("R18", "Fail at each lifecycle stage and clean only identity-marked owned resources", "Zero tasks, no socket/listener/namespace/pipe holders, no raw dump; retained redacted receipt, scratch removed"),
]:
    case(row[0], "P11", "private-linux-cgroup-v2", row[1], row[2])
for row in [
    ("T01", "Replay declared Trailer and TE rejection on H1/H2", "No capture/verification success; privacy at every configured sink"),
    ("T02", "Send valid undeclared H1 chunked and H2 trailers", "Adapter discard observation only; exact unchanged body/signature; no raw values in outputs"),
    ("T03", "Send trailer signature/content-length/authority lookalikes", "Never replace original signature/headers or body; bounded outcome"),
    ("T04", "Send malformed/oversized trailers and slow trailer sequences", "Framework versus capture refusal; 7s outer owner/socket disposal; memory samples"),
    ("T05", "Independently review public discard-versus-reject choice after deployed evidence", "Root decision plus accountable ingress/privacy review; stays unselected in this packet"),
]:
    case(row[0], "P12", "private-linux-cgroup-v2" if row[0] != "T05" else "deployed-cloudflare-staging", row[1], row[2])
for row in [
    ("I01", "Local synthetic TLS 1.2/1.3 and ALPN H1/H2 separate from h2c", "Fixture cert and backend protocol record; same bytes/signature outcomes; no provider claim"),
    ("I02", "Pin Worker/DO/container source/config/image and qualify external-to-backend hop", "Real staging TLS/ALPN, Worker and backend negotiated protocols, exact versions and region"),
    ("I03", "Compare duplicate/case/whitespace signature, CL/TE and content-encoding translation", "Exact synthetic vectors and accepted/rejected outcome at each hop; no accidental joined-signature success"),
    ("I04", "Observe undeclared/declared/malformed trailers through each real edge path", "Hop visibility or explicit unobservability; chosen discard/reject capability proven before public activation"),
    ("I05", "Exercise stream backpressure, slow body, large chunks, timeout and disconnect", "Worker cancellation AND original backend owner/socket closure; memory/retention and no automatic replay"),
    ("I06", "Qualify Cloudflare resource, stop/OOM/monitor/restart and all logging collectors", "Provider-enforced effective allocation and observed failures; no inference of Linux cgroup/PID/FD/dump equivalence"),
    ("I07", "Qualify deny-all egress and keep native Neon/Stripe dependencies separate", "No private-slice DB/provider need; direct Neon TLS/notifier and Stripe test-mode remain P15/P16 external gates"),
]:
    case(row[0], "P14", "private-linux-synthetic-tls" if row[0] == "I01" else "deployed-cloudflare-staging", row[1], row[2])
write("matrix.json", {"schema": 1, "rootSelection": "pending", "runtimeCasesExecuted": 0,
                      "gaAccepted": False, "rows": matrix})

source_ranges = {
    "hosted/deps/plug/lib/plug/conn.ex": [(1133, 1172, "read_body options are approximate")],
    "hosted/deps/bandit/lib/bandit/http1/socket.ex": [(347, 355, "trailer parse uses default H1 header options then discard")],
    "hosted/deps/bandit/lib/bandit/http2/stream.ex": [(102, 104, "DATA delivered by process message"), (303, 319, "per-read timeout and logged discarded trailers")],
    "hosted/deps/bandit/lib/bandit/http2/connection.ex": [(160, 174, "decode before header-list check"), (208, 219, "connection receive-window updates"), (313, 321, "compressed block versus decoded header-list limits")],
    "hosted/deps/bandit/lib/bandit/http2/flow_control.ex": [(1, 38, "receive window grows toward 2^31-1")],
    "hosted/deps/thousand_island/lib/thousand_island/acceptor.ex": [(60, 83, "logical admission after socket accept"), (146, 153, "file descriptor exhaustion backoff")],
    "hosted/deps/thousand_island/lib/thousand_island/socket.ex": [(110, 142, "raw receive/send telemetry measurements")],
    "hosted/deps/bandit/mix.exs": [(1, 16, "installed package version and Elixir compatibility")],
    "hosted/deps/thousand_island/mix.exs": [(1, 14, "installed package version and Elixir compatibility")],
    "hosted/mix.exs": [(1, 39, "exact compiler and package pins; test support excluded from production")],
    "hosted/lib/mixer_hosted/billing/webhook_transport.ex": [(609, 686, "fixed private loopback listener/profile"), (687, 740, "capture/permit/dispose interface")],
    "hosted/lib/mixer_hosted/application.ex": [(1, 48, "ordinary API/processor children do not start transport")],
    "hosted/scripts/test-local.py": [(74, 91, "warning/error compile, release and exclusion collector")],
}
source_map = []
for path, ranges in source_ranges.items():
    lines = (ROOT / path).read_text().splitlines()
    source_map.append({"path": path, "sha256": digest(ROOT / path), "lineCount": len(lines),
                       "findings": [{"start": a, "end": min(b, len(lines)), "finding": finding,
                                     "excerpt": "\n".join(lines[a-1:min(b, len(lines))])}
                                    for a, b, finding in ranges]})
write("source-map.json", {"schema": 1, "scope": "actual installed source inspection; no new runtime execution", "files": source_map})

extra = ["AGENTS.md", "mixer-product-plan.md", "PLAN.md", "THIRD_PARTY.yml", ".github/workflows/hosted.yml",
         "docs/stripe-webhook-transport-contract.md", "docs/stripe-webhook-transport-direction.md",
         "docs/stripe-webhook-transport-review.md", "docs/stripe-webhook-transport-integration.md",
         "docs/stripe-webhook-transport-regressions.md", str(baseline_path.relative_to(ROOT))]
extras = sorted(set(extra + list(source_ranges)) - set(baseline["sourceInputs"]))
write("source-bindings.json", {"schema": 1, "baselineSourceDigest": baseline["sourceDigest"],
                               "baselineInputCount": 73, "baselineInputs": baseline["sourceInputs"],
                               "additionalInputs": {p: digest(ROOT / p) for p in extras},
                               "noGitOperation": True, "revisionContextOnly": "bbed074d"})

commands = []
for label, argv in [("python", [sys.executable, "--version"]), ("elixir", [shutil.which("elixir"), "--version"]),
                    ("cc", [shutil.which("cc"), "--version"])]:
    p = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    commands.append({"label": label, "argv": argv, "cwd": str(ROOT), "exitCode": p.returncode,
                     "stdout": p.stdout, "stderr": p.stderr})
write("tools.json", {"schema": 1, "platform": platform.platform(), "machine": platform.machine(),
                     "python": platform.python_version(), "commands": commands,
                     "pathsOnlyNoDaemonContact": {k: shutil.which(k) for k in ["docker", "podman", "wrangler", "unshare", "prlimit", "systemd-run", "nft"]},
                     "linuxCgroupAvailable": pathlib.Path("/sys/fs/cgroup/cgroup.controllers").is_file(),
                     "runtimeHarnessExecuted": False})
write("authoring-receipt.json", {"schema": 1, "status": "proposal-contract-checks-pending",
                                "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "command": [sys.executable, "-B", str(HERE / "prepare.py")],
                                "cwd": str(ROOT), "scope": "Documentation, source/content inspection and contract checks only",
                                "runtimeCasesExecuted": 0, "productionActivated": False,
                                "providerContacted": False, "dependenciesAdded": [],
                                "cleanup": {"roleStarted": False, "listenerStarted": False,
                                            "stressHelperStarted": False, "databaseStarted": False,
                                            "daemonStarted": False, "nativeInstanceStarted": False,
                                            "ownedScratchCreated": False,
                                            "toolsProcesses": "version queries exited normally; no owned long-running process"},
                                "remaining": ["root selection", "private Linux implementation and runtime replay", "fresh independent review",
                                              "Cloudflare deployed resource/TLS/ingress/privacy", "public trailer choice",
                                              "Neon and Stripe staging", "authority and inbox/Oban", "G23"]})
print(json.dumps({"status": "prepared-proposal-only", "baselineInputs": 73, "additionalInputs": len(extras),
                  "matrixCases": len(matrix), "runtimeCasesExecuted": 0}, sort_keys=True))
