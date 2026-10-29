"""Independent bounded inspection of retained data. Imports no subject code."""
import sys
import os
import time
import signal
import _signal
import threading
import _thread
import subprocess
import socket
import importlib.abc
import encodings.cp437


def deny(*args, **kwargs):
    raise RuntimeError("independent offline review denies active APIs")


denied = []


def replace(module, names):
    for name in names:
        if hasattr(module, name) and callable(getattr(module, name)):
            setattr(module, name, deny)
            denied.append(module.__name__ + "." + name)


replace(os, [name for name in dir(os) if name in {
    "system", "popen", "fork", "forkpty", "kill", "killpg", "abort", "_exit",
    "startfile", "chdir", "setsid", "getsid", "setpgid", "getpgid", "getpgrp",
    "setpgrp", "getpid", "getppid", "tcgetpgrp", "tcsetpgrp",
} or name.startswith(("spawn", "posix_spawn", "exec", "wait"))])
replace(subprocess, ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput", "_fork_exec"))
replace(socket, ("socket", "SocketType", "socketpair", "fromfd", "fromshare", "create_connection", "create_server", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "getnameinfo", "setdefaulttimeout", "getdefaulttimeout"))
for module in (signal, _signal):
    replace(module, ("signal", "getsignal", "alarm", "setitimer", "getitimer", "pause", "raise_signal", "pthread_kill", "pthread_sigmask", "siginterrupt", "sigpending", "sigwait", "sigwaitinfo", "sigtimedwait", "set_wakeup_fd"))
replace(time, ("sleep",))
replace(threading.Thread, ("start", "join"))
replace(threading.Timer, ("start", "run"))
replace(threading.Event, ("wait",))
replace(threading.Condition, ("wait", "wait_for"))
replace(threading.Barrier, ("wait",))
replace(_thread, ("start_new_thread", "start_new", "exit", "exit_thread", "interrupt_main"))


class BlockImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"ctypes", "_ctypes", "multiprocessing", "asyncio", "concurrent", "http", "urllib", "ssl", "ftplib", "telnetlib", "select", "selectors", "_posixsubprocess"}:
            deny()
        return None


sys.meta_path.insert(0, BlockImports())


def guard(event, args):
    if event.startswith(("subprocess.", "socket.", "ctypes.", "os.exec", "os.spawn", "os.posix_spawn", "os.wait", "os.kill")) or event in {"os.system", "os.fork", "os.forkpty", "os.startfile", "signal.pthread_kill"}:
        deny()


sys.addaudithook(guard)

from pathlib import Path
from collections import Counter
import json
import hashlib
import zipfile
import io
import re
import stat

ROOT = Path("/Users/andreyyurlov/Documents/dev/mixer")
PACKET = ROOT / "verification/android-axis-refusal-binding-host-actual-review"
LOCAL = PACKET / "local"
OWN = PACKET / "independent-review"
HEAD = "2c751cbbc300efc9aa766b5d4add648610ca0341"
TREE = "f2df6833ee8e9ce85306210b63dc35d45747fa0d"
PROJECTION = "257ed4dfa93d43b15d4bfe2d51372d261e4fec5fd9e80c3f1ca62b1967a3a793"
checks = []
inputs = {}


def check(ok, reason):
    if not ok:
        raise ValueError(reason)
    checks.append(reason)


def eq(actual, expected, reason):
    if isinstance(actual, bytes) or isinstance(expected, bytes):
        check(type(actual) is type(expected) and actual == expected, reason)
    else:
        check(json.dumps(actual, sort_keys=True, ensure_ascii=False) == json.dumps(expected, sort_keys=True, ensure_ascii=False), reason)


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(path, cap=1048576):
    path = Path(path)
    rel = path.relative_to(ROOT)
    check(all(part not in {"", ".", ".."} for part in rel.parts), "safe path: " + str(rel))
    current = ROOT
    for part in rel.parts:
        current = current / part
        check(not current.is_symlink(), "no symlink: " + str(current.relative_to(ROOT)))
    st = path.stat()
    check(stat.S_ISREG(st.st_mode) and st.st_size <= cap, "bounded regular file: " + str(rel))
    with path.open("rb") as stream:
        raw = stream.read(cap + 1)
    check(len(raw) == st.st_size <= cap, "bounded complete read: " + str(rel))
    observed = identity(raw)
    if str(rel) in inputs:
        eq(observed, inputs[str(rel)], "stable reread: " + str(rel))
    inputs[str(rel)] = observed
    return raw


def pairs(items):
    result = {}
    for key, value in items:
        check(key not in result, "unique JSON key: " + key)
        result[key] = value
    return result


def invalid_number(value):
    raise ValueError("nonfinite JSON value: " + value)


def decode(raw):
    check(b"\x00" not in raw and not raw.startswith(b"\xef\xbb\xbf"), "unambiguous JSON encoding")
    return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=pairs, parse_constant=invalid_number)


def load(path):
    return decode(read(path))


def verify_rows(rows, label):
    for row in rows:
        eq(identity(read(ROOT / row["path"])), {k: row[k] for k in ("bytes", "sha256")}, label + ": " + row["path"])


check(sys.flags.isolated == sys.flags.no_site == sys.flags.dont_write_bytecode == 1, "review Python -I -B -S flags")
check("encodings.cp437" in sys.modules and len(denied) == len(set(denied)) == 105, "cp437 preloaded and 105 active API names denied before data imports")

seal_raw = read(PACKET / "seal.json")
eq(identity(seal_raw), {"bytes": 9036, "sha256": "1f3758daac935862e450b93fde11dfd5cc1e7cdf71ad33403f2ecf88c9494098"}, "exact producer seal")
seal = decode(seal_raw)
eq([len(seal[k]) for k in ("files", "local_files", "input_files")], [3, 23, 12], "26 sealed packet files and 12 unchanged input records")
verify_rows(seal["files"] + seal["local_files"] + seal["input_files"], "sealed identity")
eq(hashlib.sha256("".join(row["path"] + "\0" + row["sha256"] + "\n" for row in seal["files"]).encode()).hexdigest(), seal["public_projection"], "public packet projection independently reconstructed")
check(seal["all_existing_holds_preserved"] is True and seal["input_before_after_unchanged"] is True, "producer holds and unchanged-input declarations")
receipt = load(PACKET / "receipt.json")
eq(identity(read(PACKET / "receipt.json")), {"bytes": 13552, "sha256": "1b50668530fd7414c429c1575400d4bd6b5fcd7a2791d51956d6b464b2f75941"}, "exact producer receipt")
binding = load(LOCAL / "binding.json")
audit = load(LOCAL / "audit-attempt-1.json")
summary = load(PACKET / "result-summary.json")
eq([receipt["delivered_head"], receipt["delivered_tree"], summary["head"], summary["tree"]], [HEAD, TREE, HEAD, TREE], "source revision and tree metadata consistent")
eq(audit["status"], "ACTUAL_ISOLATED_HOST_19_TESTS_VERIFIED", "actual subject result status retained")
eq(identity(read(LOCAL / "audit-attempt-1.json")), {"bytes": 27398, "sha256": "99499fd26d4ae64a9844dbaebaf6ee1649ffd998555edde4c21705c6f9da3f21"}, "actual audit stdout identity")
eq(read(LOCAL / "audit-attempt-1.stderr"), b"", "actual audit stderr empty")

expected_names = sorted([
    "root-selection.json", "context.json", "binding.json", "source-before.json", "source-after.json",
    "apple-toolchain.json", "apple-toolchain.stdout", "apple-toolchain.stderr", "apple-bash-file-limit-blocks.txt",
    "apple-file-limit.json", "apple-file-limit.stdout", "apple-file-limit.stderr", "bash-file-limit-blocks.txt",
    "file-limit.json", "file-limit.stdout", "file-limit.stderr", "command.json", "swift.stdout", "swift.stderr", "result.json",
])
archive_raw = read(LOCAL / "artifact.zip")
eq(identity(archive_raw), {"bytes": 13968, "sha256": "2d30a722fd5047aaa363f14482d4cd66abc7f7b44011e4453c9433ba8c5355f9"}, "actual acquired ZIP identity")
files = {}
with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
    entries = archive.infolist()
    eq(sorted(entry.filename for entry in entries), expected_names, "exact 20 ZIP outputs")
    check(len(entries) == len({entry.filename for entry in entries}) == 20, "ZIP names unique")
    for entry in entries:
        check(not entry.is_dir() and not entry.flag_bits & 1 and entry.compress_type == zipfile.ZIP_DEFLATED and entry.file_size <= 8388608, "ZIP regular unencrypted bounded deflate member: " + entry.filename)
        check(stat.S_IFMT(entry.external_attr >> 16) in {0, stat.S_IFREG}, "ZIP no special filesystem member: " + entry.filename)
        with archive.open(entry) as stream:
            raw = stream.read(8388609)
        check(len(raw) == entry.file_size, "ZIP complete CRC-checked bounded payload: " + entry.filename)
        files[entry.filename] = raw
eq(sum(map(len, files.values())), 31099, "ZIP expanded total 31,099 bytes")
member_rows = [{"path": name, **identity(files[name])} for name in sorted(files)]
eq(member_rows, audit["archive"]["members"], "all 20 member lengths and hashes agree with actual audit")
eq(hashlib.sha256(json.dumps(member_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), audit["archive"]["member_map_sha256"], "archive member map digest independently reconstructed")
data = {name: decode(raw) for name, raw in files.items() if name.endswith(".json")}

manifest = load(ROOT / "verification/android-axis-refusal-host-preparation/source-manifest.json")
roster = load(ROOT / "verification/android-axis-refusal-host-admission-binding-correction/required-tests.json")
package = ROOT / "verification/android-axis-refusal-host-preparation/package"
source_rows = []
for row in manifest["source_rows"]:
    source_raw = read(package / row["path"])
    eq(identity(source_raw), {k: row[k] for k in ("bytes", "sha256")}, "current frozen package source: " + row["path"])
    source_rows.append({"path": row["path"], **identity(source_raw)})
source_rows.sort(key=lambda row: row["path"])
observed = []
queue = [package]
while queue:
    current = queue.pop()
    children = list(current.iterdir())
    check(len(children) <= 32, "bounded package directory membership")
    for child in children:
        check(not child.is_symlink(), "package member not symlink")
        if child.is_dir():
            check(len(child.relative_to(package).parts) < 10, "bounded package depth")
            queue.append(child)
        else:
            observed.append(child.relative_to(package).as_posix())
eq(sorted(observed), [row["path"] for row in source_rows], "no extra package source members")
check(len(source_rows) == 27 and sum(row["bytes"] for row in source_rows) == 284605, "27 source files total 284,605 bytes")
source_projection = hashlib.sha256("".join(row["path"] + "\0" + row["sha256"] + "\n" for row in source_rows).encode()).hexdigest()
eq(source_projection, PROJECTION, "independent frozen source projection")
snapshot = {"schema": 1, "status": "exact-27-source-members", "sourceManifestSHA256": identity(read(ROOT / "verification/android-axis-refusal-host-preparation/source-manifest.json"))["sha256"], "sourceReviewSHA256": identity(read(ROOT / "verification/android-axis-refusal-host-review/receipt.json"))["sha256"], "projection": PROJECTION, "rows": source_rows, "bytes": 284605}
eq(data["source-before.json"], snapshot, "all source-before fields independently reconstructed")
eq(data["source-after.json"], snapshot, "all source-after fields independently reconstructed")
verify_rows(receipt["source"]["all_live_pins_verified"], "nine live producer/auditor source pins")
eq(roster["suites"], [{key: suite[key] for key in ("suite", "framework", "names")} for suite in manifest["test_membership"]], "test roster and source manifest membership")

stdout = files["swift.stdout"].decode("utf-8", "strict")
stderr = files["swift.stderr"].decode("utf-8", "strict")
text = stdout + "\n" + stderr
check("\x1b" not in text and "\ufffd" not in text and stderr.count("Build complete! (38.35s)") == 1, "raw successful build completion without ambiguity")
check(not re.search(r"error:|warning:|fatal error|\bfailed\b|\bskipped\b|\bskips?\b|[✘✗]", text, re.I), "raw streams have zero failures skips and warning diagnostics")
xc_events = [line for line in stdout.splitlines() if line.startswith("Test Case ")]
xc_started, xc_passed = [], []
for line in xc_events:
    check(line.startswith("Test Case '-[MixerAndroidRuntimeTests.AndroidTextFieldAxisRefusalTests "), "exact XCTest event owner")
    name, tail = line.split("AndroidTextFieldAxisRefusalTests ", 1)[1].split("]' ", 1)
    if tail == "started.":
        xc_started.append(name)
    else:
        check(re.fullmatch(r"passed \([0-9.]+ seconds\)\.", tail) is not None, "exact XCTest passed event")
        xc_passed.append(name)
xc_expected = next(suite["names"] for suite in roster["suites"] if suite["framework"] == "XCTest")
eq(Counter(xc_started), Counter({name: 1 for name in xc_expected}), "all eight XCTest starts once")
eq(Counter(xc_passed), Counter({name: 1 for name in xc_expected}), "all eight XCTest passes once")
xc_summaries = [line.strip() for line in stdout.splitlines() if line.strip().startswith("Executed ")]
check(len(xc_summaries) == 3 and all(re.fullmatch(r"Executed 8 tests, with 0 failures \(0 unexpected\) in [0-9.]+ \([0-9.]+\) seconds", line) for line in xc_summaries), "three exact zero-failure XCTest summaries")
for suite in ["AndroidTextFieldAxisRefusalTests", "MixerAndroidAxisHostCheckPackageTests.xctest", "All tests"]:
    check(sum(line.startswith("Test Suite '" + suite + "' passed at ") for line in stdout.splitlines()) == 1, "one terminal XCTest suite: " + suite)
swift_started = [line[len("◇ Test "):-len("() started.")] for line in stdout.splitlines() if line.startswith("◇ Test ") and line.endswith("() started.")]
swift_pass_lines = [line for line in stdout.splitlines() if line.startswith("✔ Test ") and " passed " in line]
swift_summary = "✔ Test run with 11 tests in 2 suites passed after 0.063 seconds."
check(swift_pass_lines.count(swift_summary) == 1, "one exact Swift Testing terminal summary")
swift_passed = []
for line in swift_pass_lines:
    if line == swift_summary:
        continue
    match = re.fullmatch(r"✔ Test ([A-Za-z0-9_]+)\(\) passed after [0-9.]+ seconds\.", line)
    check(match is not None, "no extra quoted qualified display or malformed Swift success")
    swift_passed.append(match[1])
swift_expected = [name for suite in roster["suites"] if suite["framework"] == "Swift Testing" for name in suite["names"]]
eq(Counter(swift_started), Counter({name: 1 for name in swift_expected}), "all eleven Swift Testing starts once")
eq(Counter(swift_passed), Counter({name: 1 for name in swift_expected}), "all eleven Swift Testing passes once")
check(len(xc_passed) == 8 and len(swift_passed) == 11 and len(swift_pass_lines) == 12, "19 exact individual successes plus one Swift summary")
for suite in roster["suites"]:
    source_path = package / "Tests/MixerAndroidRuntimeTests" / (suite["suite"] + ".swift")
    source_text = read(source_path).decode()
    for name in suite["names"]:
        check(len(re.findall(r"\bfunc\s+" + re.escape(name) + r"\s*\(", source_text)) == 1, "named method present once in frozen source: " + name)
tests = {"XCTest": {"count": 8, "names": xc_passed, "summaryOccurrences": 3}, "Swift_Testing": {"count": 11, "successResultLines": 11, "names": swift_passed, "summary": swift_summary}, "total": 19, "warnings": [], "stdout": identity(files["swift.stdout"]), "stderr": identity(files["swift.stderr"])}
eq(tests, receipt["tests"], "independent raw census matches full public tests object")
eq(tests, audit["actual"]["tests"], "independent raw census matches actual auditor tests object")

wire_raw = read(LOCAL / "dispatch-selection-wire.json")
eq(identity(wire_raw), {"bytes": 1563, "sha256": "df6d057991d4492ef53129f2b9eb5fdb0928a3192eae0bb27c3309be5d2759a6"}, "actual dispatch wire bytes")
selection = decode(wire_raw)
template = load(ROOT / "verification/android-axis-refusal-host-admission-binding-correction/root-selection.template.json")
expected_selection = dict(template, selected=True, dispatch_authorized=True, source_revision=HEAD)
eq(selection, expected_selection, "complete dispatch selection has only three authorized template deltas")
eq(data["root-selection.json"], selection, "artifact selection preserves dispatch structure")
eq(binding["dispatch"]["root_selection"], selection, "root binding selection preserves dispatch structure")
ordered = json.dumps(data["root-selection.json"], separators=(",", ":"), ensure_ascii=False).encode()
eq(ordered, wire_raw, "producer insertion-order compact JSON equals actual wire bytes")
eq(data["binding.json"]["rootSelectionSHA256"], identity(ordered)["sha256"], "producer insertion-order root selection digest")
context = {"repository": "snowdamiz/mixer", "sha": HEAD, "event": "workflow_dispatch", "profile": "axis-refusal-host-v1", "run_id": "40943215863", "run_attempt": "1", "node_version": "v22.23.2"}
eq(data["context.json"], context, "entire actual host context")
producer_binding = {key: context[key] for key in ("event", "repository", "sha", "run_id", "run_attempt", "profile")}
workflow_raw = read(ROOT / ".github/workflows/android-axis-refusal-host.yml")
producer_binding.update(workflowSHA256=identity(workflow_raw)["sha256"], rootSelectionSHA256=identity(ordered)["sha256"])
eq(data["binding.json"], producer_binding, "entire producer binding independently reconstructed")

for name in ["apple-file-limit.json", "file-limit.json"]:
    limit = data[name]
    eq({key: limit[key] for key in ("schema", "soft_bytes", "hard_bytes", "bash_blocks", "bash_version", "operation")}, {"schema": 1, "soft_bytes": 67108864, "hard_bytes": 67108864, "bash_blocks": 65536, "bash_version": "3.2.57(1)-release", "operation": "resource.getrlimit(RLIMIT_FSIZE)"}, "actual 64MiB Python/Bash readback: " + name)
    check(limit["python_version"].startswith("3.14.7 "), "observed runner Python version retained: " + name)
eq(data["apple-file-limit.json"], data["file-limit.json"], "both phases exact equal file-limit readback")
for name in ["apple-bash-file-limit-blocks.txt", "bash-file-limit-blocks.txt"]:
    eq(files[name], b"65536\n", "actual Bash1024-byte-block readback: " + name)
for name in ["apple-toolchain.stderr", "apple-file-limit.stdout", "apple-file-limit.stderr", "file-limit.stdout", "file-limit.stderr"]:
    eq(files[name], b"", "empty successful probe stream: " + name)
tool = data["apple-toolchain.json"]
eq(files["apple-toolchain.stdout"], files["apple-toolchain.json"], "actual tool probe stdout byte-equals receipt")
eq(tool, receipt["host_tool"], "all observed tool fields retained")
eq(tool["swiftVersion"], [6, 2, 4], "actual Swift6.2.4")
eq(tool["xcode"], "Xcode 26.3\nBuild version 17C529", "actual Xcode26.3 build17C529")
check("Target: arm64-apple-macosx15.0" in tool["swift"] and "15.7.9" in tool["host"], "actual arm64 macOS15.7.9 host preserved")
eq(tool["runnerImageVersion"], "20260907.0337.1", "observed tool runner image version")
eq(tool["sdkVersions"], {"macosx": "26.2", "iphonesimulator": "26.2"}, "SDK probe values retained without runtime claim")
eq(tool["sourceRevision"], HEAD, "tool receipt source revision binding")
eq(tool["probeSHA256"], identity(read(ROOT / "scripts/ci/verify-apple-toolchain.py"))["sha256"], "exact Apple toolchain probe source binding")
command = data["command.json"]
eq(command, receipt["host_command"], "entire host command retained")
eq(command["argv"], [tool["swiftPath"], "test", "--package-path", "/Users/runner/work/mixer/mixer/verification/android-axis-refusal-host-preparation/package", "--scratch-path", "/Users/runner/work/_temp/android-axis-refusal-40943215863-1-scratch", "--jobs", "2"], "one exact unfiltered SwiftPM argv")
eq([command["exit_code"], command["shell_completion"]], [0, "returned-to-actions-shell"], "direct Actions shell exit0 only")
eq(command["file_limit_readback"], data["file-limit.json"], "command binds actual limit readback")
custody = {"hosted_step_completion": True, "direct_child_reap": None, "owned_group_absence": None, "separate_pipe_EOF": None, "arbitrary_descendants": None, "runner_disposal": None, "scratch_cleanup": "not-performed-or-established"}
producer_result = {"schema": 1, "status": "isolated-host-test-evidence-complete", "sourceProjection": PROJECTION, "sourceFiles": 27, "sourceBytes": 284605, "context": context, "tool": tool, "command": command, "tests": tests, "custody": custody, "pending": ["canonical SDK/engine package topology and C ABI integration", "Java decoder/combined source pair", "native/UI/capture and physical phones", "immutable published external FieldLog", "source-pair promotion, OTA and GA"], "binding": producer_binding, "apple_file_limit": data["apple-file-limit.json"], "tool_probe_streams": {name: identity(files[name]) for name in ["apple-toolchain.stdout", "apple-toolchain.stderr", "apple-file-limit.stdout", "apple-file-limit.stderr", "file-limit.stdout", "file-limit.stderr"]}}
eq(data["result.json"], producer_result, "complete producer result independently reconstructed from actual bytes")

jobs = load(LOCAL / "full-run-jobs.json")
check(jobs["total_count"] == len(jobs["jobs"]) == 1, "full API response exactly one actual host job")
job = jobs["jobs"][0]
eq([job["id"], job["run_id"], job["run_attempt"], job["head_sha"], job["name"], job["status"], job["conclusion"], job["labels"]], [123691711035, 40943215863, 1, HEAD, "axis-refusal", "completed", "success", ["macos-15"]], "full API actual job IDs head success and macos-15 label")
eq(binding["job"]["steps"], [{key: step[key] for key in ("conclusion", "name", "number", "status")} for step in job["steps"]], "all ten actual API job steps preserved in root binding")
connector = load(LOCAL / "connector-observations.json")
eq([connector["run"][key] for key in ("id", "workflow_id", "run_attempt", "head_sha", "path", "status", "conclusion", "event", "head_branch")], [40943215863, 400656207, 1, HEAD, ".github/workflows/android-axis-refusal-host.yml", "completed", "success", "workflow_dispatch", "main"], "retained full run connector response binds exact successful workflow run")
check(len(connector["artifacts"]["artifacts"]) == len(connector["jobs"]["jobs"]) == 1, "connector observes exactly one artifact and one host job")
artifact = connector["artifacts"]["artifacts"][0]
eq([artifact[key] for key in ("id", "name", "size_in_bytes", "expired", "digest")], [12926579616, binding["artifact"]["name"], 13968, False, "sha256:" + identity(archive_raw)["sha256"]], "retained artifact API bytes digest identity and expiry match acquired ZIP")
eq([artifact["workflow_run"][key] for key in ("id", "head_branch", "head_sha")], [40943215863, "main", HEAD], "retained artifact API bound to exact run and delivered revision")
eq(connector["jobs"]["jobs"][0]["steps"], binding["job"]["steps"], "connector and complete job API step projections agree")
selected_steps = ["Exact root binding and 27 source members", "Existing exact Apple toolchain verifier", "One unfiltered isolated SwiftPM test command", "Preserve all 27 postflight source identities", "Require every named result and both framework summaries", "Retain successful or failed evidence"]
for name in selected_steps:
    selected = [step for step in job["steps"] if step["name"] == name]
    check(len(selected) == 1 and selected[0]["status"] == "completed" and selected[0]["conclusion"] == "success", "selected terminal step success: " + name)
log = read(LOCAL / "job-123691711035.log").decode("utf-8", "strict")
plain_log = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", log)
log_lines = [re.sub(r"^\d{4}-\d\d-\d\dT\S+\s+", "", line).strip() for line in plain_log.splitlines()]
wire_appearances = [line[len("MIXER_AXIS_ROOT_SELECTION: "):] for line in log_lines if line.startswith("MIXER_AXIS_ROOT_SELECTION: ")]
check(len(wire_appearances) == 7 and all(value.encode() == wire_raw for value in wire_appearances), "all seven actual log appearances equal exact dispatch wire bytes")
workflow_lines = workflow_raw.decode().splitlines()
shell_blocks = {}
current_step = None
for index, line in enumerate(workflow_lines):
    if line.startswith("      - name: "):
        current_step = line[len("      - name: "):]
    if line == "        run: |":
        block = []
        for following in workflow_lines[index + 1:]:
            if following and not following.startswith("          "):
                break
            if following.strip():
                block.append(following.strip())
        shell_blocks[current_step] = block
eq(sorted(shell_blocks), sorted(selected_steps[:-1]), "workflow has five exact selected shell blocks")
for name, block in shell_blocks.items():
    for line in block:
        check(line in log_lines, "actual shell transcript source line: " + name + " / " + line)
for expected in ["Uploaded bytes 13968", "SHA256 digest of uploaded artifact zip is " + identity(archive_raw)["sha256"], "Artifact " + binding["artifact"]["name"] + ".zip successfully finalized. Artifact ID 12926579616", "Artifact " + binding["artifact"]["name"] + " has been successfully uploaded! Final size is 13968 bytes. Artifact ID is 12926579616", "Image: macos-15-arm64", "Version: 20260907.0337.1", "15.7.9"]:
    check(expected in log_lines, "actual Actions uploader/setup observation: " + expected)
check("Node.js 20" in plain_log or "Node.js20" in plain_log, "Actions Node20 deprecation observation preserved separately from Swift warnings")

recovery = ROOT / "verification/github-delivery-axis-binding-stage-recovery"
post_path = recovery / "review/postdelivery-actual/seal.json"
post_raw = read(post_path)
eq(identity(post_raw), {"bytes": 1375, "sha256": "be81918d534058e73ad5a800469102574ead733a65fc37bd206a5fac3b38553d"}, "accepted independent postdelivery seal identity")
post_seal = decode(post_raw)
eq(post_seal["decision"], "accept-exact-21-command-postdelivery-binding-observation", "prior postdelivery review accepted exact bounded observation")
check(post_seal["checksFailed"] == 0 and post_seal["subjectExecution"] is False and post_seal["laterAuthorityGranted"] is False, "prior postdelivery acceptance grants no later authority or subject execution")
for key in ("rows", "files", "input_files"):
    if key in post_seal:
        verify_rows(post_seal[key], "accepted postdelivery review seal member")
once = load(recovery / "manual-axis-stage-recovery-once.json")
submitted = load(recovery / "manual-axis-stage-recovery-submitted.json")
run_binding = load(recovery / "manual-axis-stage-recovery-run-binding.json")
eq(binding["dispatch"]["marker_sha256"], identity(read(recovery / "manual-axis-stage-recovery-once.json"))["sha256"], "actual once marker bound by producer data review")
check(once["allowanceConsumedBeforeSubmit"] is True and once["dispatchLimit"] == once["runAttemptLimit"] == 1 and once["retryRerunFallbackAllowed"] is False and once["oldAllowancesReused"] == 0, "durable once marker consumed single nonreplayed allowance")
check(submitted["retryAllowed"] is False and submitted["submitTerminal"]["exit"] == 0, "root submitted record no retry")
eq(run_binding["head"], HEAD, "late four-command run binding head")
check(len(run_binding["commands"]) == 4 and run_binding["dispatches"] == run_binding["attempt"] == 1 and run_binding["retries"] == 0, "late binding exactly four selected observations no replay")
eq([run_binding["manual"][key] for key in ("id", "run_attempt", "workflow_id", "head_sha", "status", "conclusion")], [40943215863, 1, 400656207, HEAD, "completed", "success"], "run workflow attempt and delivered revision coherent")
eq(load(recovery / "manual-axis-stage-recovery-input.json"), selection, "root submitted input structure equals artifact and exact wire")
adapter = load(LOCAL / "acquisition-adapter-observation.json")
acquired = load(LOCAL / "acquisition.json")
eq([adapter["connectorCalls"], adapter["directConsumerInvocations"], adapter["directConsumerAttempts"], adapter["remainingConsumerAttempts"], adapter["workflowResubmissions"]], [2, 1, 1, 0, 0], "two connector reads one direct artifact consumer zero remaining/replay")
check(adapter["signedURLPrintedOrSavedToFiles"] is False and acquired["signedURLPrintedOrPersisted"] is False and acquired["success"] is True and acquired["elapsedMs"] == 203 and acquired["retryAllowed"] is False, "successful 203ms acquisition observation preserves signed-URL and retry limits")
eq({"bytes": acquired["observedBytes"], "sha256": acquired["sha256"]}, identity(archive_raw), "acquisition result binds retained archive bytes")

invocation = load(LOCAL / "audit-attempt-1-invocation.json")
outcome = load(LOCAL / "audit-attempt-1-outcome.json")
guard_observation = load(LOCAL / "guard-observation-attempt-1.json")
check(outcome["guarded_actual_audit_invocations"] == 1 and outcome["subject_source_adaptations"] == 0 and outcome["exit_code"] == 0, "recorded exact auditor invoked once unchanged and exited0")
eq(invocation["argv"], receipt["audit"]["exact_argv"], "actual invocation vector fully preserved")
eq(invocation["argv"][1:4], ["-I", "-B", "-S"], "actual subject invocation isolated no-site no-bytecode")
eq(guard_observation["denied_api_names"], sorted(denied), "actual outer guard names match 105 installed independent guard denials")
check(guard_observation["guards_before_subject_import"] is True and guard_observation["cp437_preloaded_before_guards"] is True, "actual guard observation before subject import cp437 preloaded")
eq(guard_observation["flags"], {"bytecode_disabled": True, "isolated": 1, "no_site": 1}, "actual guard observation flags")
check(guard_observation["python"]["version"].startswith("3.14.8 "), "actual subject Python3.14.8 observed")
guard_source = read(LOCAL / "run_guarded_audit.py").decode()
check(guard_source.index("import encodings.cp437") < guard_source.index("replace(os,") < guard_source.index("sys.addaudithook(guard_event)") < guard_source.index("raw = auditor.read_bytes()") < guard_source.index("exec(compile(raw,"), "guard source installs cp437 and active denials before exact subject load")
eq(guard_observation["subject"]["sha256"], "126ba814e8c42cfaafe970bf31dd63e211be8aadd37750d326e3fa784823df66", "actual invocation exact reviewed source hash")
before = read(LOCAL / "prepare_binding.attempt-1.py").decode()
after = read(LOCAL / "prepare_binding.py").decode()
eq(before.replace('== 6 and all(value.encode() == wire_raw for value in logged_wires), "all six actual environment appearances', '== 7 and all(value.encode() == wire_raw for value in logged_wires), "all seven actual environment appearances'), after, "only owned preparatory expected count changes from six to seven")
check("all six actual environment appearances preserve the exact wire" in read(LOCAL / "binding-prepare-attempt-1.stderr").decode(), "original pre-subject preparation failure preserved")
check(all(item["subject_imported"] is False for item in outcome["binding_preparation_attempts"]), "both preparation attempts retained as pre-subject data work")
eq([item["exit_code"] for item in outcome["binding_preparation_attempts"]], [1, 0], "failed first and successful corrected preparation preserved")
eq(receipt["canonical_source_pair"], {"SDK_inputs": 22, "adapter_inputs": 23, "changed_by_this_lane": False, "promotion": False, "selection": ".5"}, "public actual review does not claim canonical promotion")
eq(receipt["custody_limits"], {"both_pipe_EOF": None, "direct_actions_shell_completion_only": True, "kernel_reap": None, "owned_group_absence": None, "provider_disposal": None, "scratch_cleanup": None}, "remote host custody limits explicitly preserved")

before_inputs = dict(inputs)
for rel, expected in sorted(before_inputs.items()):
    eq(identity(read(ROOT / rel)), expected, "all reviewed input bytes unchanged at completion: " + rel)
check(inputs == before_inputs, "review input roster stable across final reread")
OWN.mkdir(parents=True, exist_ok=True)
report = {
    "schema": 1,
    "status": "ACCEPTED_ACTUAL_ISOLATED_HOST_19_TESTS",
    "findings": [],
    "scope": "Independent offline actual-data review of isolated 27-file host behavior only",
    "command": ["python3.14", "-I", "-B", "-S", str(OWN / "review_data.py")],
    "python": {"executable": sys.executable, "version": sys.version},
    "guard": {"active_api_names_denied": sorted(denied), "cp437_preloaded": True, "subject_imports": 0, "subject_auditor_or_helper_invocations": 0, "containment": "known data path guard; no OS sandbox claim"},
    "head": HEAD, "tree": TREE, "metadata_trust": "Retained root-observed metadata, not independent Git or network attestation",
    "run": 40943215863, "attempt": 1, "job": 123691711035, "workflow": 400656207, "artifact": 12926579616,
    "producer_seal": {"path": str((PACKET / "seal.json").relative_to(ROOT)), **identity(seal_raw)},
    "archive": {**identity(archive_raw), "files": 20, "expanded_bytes": 31099, "members": member_rows},
    "source": {"files": 27, "bytes": 284605, "projection": PROJECTION, "before_after_equal": True},
    "tests": tests,
    "environment": {"job_labels": job["labels"], "setup_image": "macos-15-arm64", "image_version": tool["runnerImageVersion"], "host": tool["host"], "xcode": tool["xcode"], "swift": tool["swift"], "SDK_versions": tool["sdkVersions"], "Bash": command["bash_version"], "both_file_limit_bytes": 67108864},
    "dispatch": {"count": 1, "remaining": 0, "replay": False, "logged_exact_wire_appearances": 7, "wire": identity(wire_raw), "producer_insertion_order_digest": identity(ordered)["sha256"]},
    "recorded_auditor": {"invocations": 1, "adaptations": 0, "bytes": 32574, "sha256": guard_observation["subject"]["sha256"], "Python": "3.14.8", "exit_code": 0, "stderr_bytes": 0},
    "preparation_failure_preserved": True,
    "acquisition": {"connector_calls": 2, "direct_consumers": 1, "elapsed_ms": 203, "remaining": 0, "signed_URLs_printed_or_saved": False},
    "custody_limits": receipt["custody_limits"],
    "pending": receipt["pending"],
    "canonical_source_pair_observed_declaration": receipt["canonical_source_pair"],
    "standard_CI": "Separate parent investigation reports five successes and Swift analyzer-envelope prerequisite failure at this head; this review makes no all-green claim and did not independently query standard CI.",
    "all_existing_holds_preserved": True,
    "restrictions": {"Git_gh_network": 0, "compiler_product_native_UI_capture": 0, "process_probes_signals_cleanup": 0, "subject_auditor_helper_reexecution": 0, "writes_outside_owned_directory": 0},
    "check_count": len(checks),
    "inputs_before_after_unchanged": [{"path": rel, **row} for rel, row in sorted(before_inputs.items())],
}
(OWN / "actual-review.json").write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
(OWN / "checks.json").write_text(json.dumps({"schema": 1, "count": len(checks), "passed": checks}, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"status": report["status"], "checks": len(checks), "input_files_rechecked": len(before_inputs), "tests": 19, "subject_reexecutions": 0}))
