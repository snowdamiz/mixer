#!/usr/bin/env python3
"""Independent finite byte/patch/model checks. No Elixir or process/socket probes."""
import sys

BLOCKED = {
    "subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.fork",
    "os.forkpty", "pty.spawn", "os.kill", "os.killpg", "os.wait", "os.waitpid",
    "os.waitid", "time.sleep", "signal.pthread_kill", "signal.raise_signal",
}


def audit(event, args):
    if event in BLOCKED or event.startswith(("socket.", "signal.")):
        raise RuntimeError("independent source-only review denied " + event)


sys.addaudithook(audit)
import copy
import hashlib
import itertools
import json
from pathlib import Path
import re
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / "verification/identity-startup-socket-close-investigation"
RAW = ROOT / "verification/github-delivery-positive-timestamp/ci-review/network"
FIXTURE = "hosted/test/support/identity_tls_fixture.ex"
CONTROL = "hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs"
STARTUP = "hosted/test/mixer_hosted/identity/startup_linux_network_test.exs"
K03 = "hosted/test/mixer_hosted/identity/key_owner_linux_network_test.exs"
OLD = "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e"
NEW = "ab8f8dbec5894ca96dd673db828a01afdc39a54ad008a2a2d4e598c1c62ce2f7"
FIXTURE_SHA = "d3b55796a8baac4f9ebd37cc9ee5e44bde01ca346ce2dd00a0a5dd884711ba55"
CONTROL_SHA = "417704f8e805196f9546a508a770d23a55d40ce9d6214be5225f131c4bd2c7c6"
READSET = {}
CHECKS = []


def sha(body):
    return hashlib.sha256(body).hexdigest()


def row(body):
    return {"bytes": len(body), "sha256": sha(body)}


def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def read(path):
    body = path.read_bytes()
    READSET[str(path.relative_to(ROOT))] = row(body)
    return body


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def check(name, action):
    action()
    CHECKS.append(name)
    print("PASS " + name)


def require(value):
    if not value:
        raise AssertionError("independent control failed")


inventory = json.loads(read(PRODUCER / "artifact-inventory.json"))
for name, expected in inventory["files"].items():
    require(row(read(PRODUCER / name)) == expected)
check("producer packet files match its frozen inventory", lambda: require(len(inventory["files"]) == 12))

old = json.loads(read(RAW / "product-source-manifest.json"))
new = json.loads(read(PRODUCER / "candidate-product-source-manifest.json"))
proposal = json.loads(read(PRODUCER / "source-binding-proposal.json"))
archive_path = RAW / "prepared-source-dependencies-tools.tar"
archive_row = row(read(archive_path))
require(archive_row["sha256"] == "a0d9ec2cefbe62b0bfd22f3b1113b7880f5d53046a3419678f67d88f30bdc65e")
baseline = {}
with tarfile.open(archive_path) as archive:
    for path, expected in old.items():
        member = archive.getmember(path)
        require(member.isfile())
        body = archive.extractfile(member).read()
        require(row(body) == expected)
        baseline[path] = body
check("all 177 predecessor source bytes match retained execution archive", lambda: require(len(baseline) == 177 and canonical(old) == OLD))

candidate = dict(baseline)
candidate[FIXTURE] = read(PRODUCER / "candidate" / FIXTURE)
candidate[CONTROL] = read(PRODUCER / "candidate" / CONTROL)


def select(manifest, claimed_digest=NEW):
    require(claimed_digest == NEW)
    require(len(manifest) == 178 and set(manifest) == set(old) | {CONTROL})
    require(canonical(manifest) == NEW)
    require([path for path in old if old[path] != manifest[path]] == [FIXTURE])
    require(manifest[FIXTURE] == {"bytes": 9533, "sha256": FIXTURE_SHA})
    require(manifest[CONTROL] == {"bytes": 4387, "sha256": CONTROL_SHA})
    require(manifest["hosted/mix.lock"] == old["hosted/mix.lock"])


def exact_delta():
    select(new)
    require({path: row(body) for path, body in candidate.items()} == new)
    require(proposal["selected_source_digest_sha256"] == NEW)
    require(proposal["selected_path_count"] == 178)
    require(proposal["predecessor_source_digest_sha256"] == OLD)
    for path in (STARTUP, K03):
        require(proposal["unchanged_tests"][path] == old[path] == new[path])


check("178-file candidate preserves all 176 other predecessor paths and lock", exact_delta)


def patch_in_memory(patch, sources):
    lines = patch.decode().splitlines(keepends=True)
    index = 0
    results = {}
    while index < len(lines):
        before = lines[index].removeprefix("--- ").strip()
        after = lines[index + 1].removeprefix("+++ ").strip()
        require(before == "/dev/null" or before.startswith("a/"))
        require(after.startswith("b/"))
        path = after[2:]
        require(path not in results)
        source = [] if before == "/dev/null" else sources[before[2:]].decode().splitlines(keepends=True)
        output = []
        cursor = 0
        index += 2
        while index < len(lines) and lines[index].startswith("@@ "):
            match = re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*\n", lines[index])
            require(match is not None)
            old_start, old_count, new_start, new_count = [int(v) if v is not None else 1 for v in match.groups()]
            target = max(old_start - 1, 0)
            require(target >= cursor)
            output.extend(source[cursor:target])
            cursor = target
            require(len(output) == max(new_start - 1, 0))
            consumed = emitted = 0
            index += 1
            while index < len(lines) and not lines[index].startswith(("@@ ", "--- ")):
                prefix, text = lines[index][0], lines[index][1:]
                require(prefix in " +-")
                if prefix in " -":
                    require(cursor < len(source) and source[cursor] == text)
                    cursor += 1
                    consumed += 1
                if prefix in " +":
                    output.append(text)
                    emitted += 1
                index += 1
            require((consumed, emitted) == (old_count, new_count))
        output.extend(source[cursor:])
        results[path] = "".join(output).encode()
    return results


def exact_patch():
    applied = patch_in_memory(read(PRODUCER / "integration-candidate.patch"), baseline)
    require(set(applied) == {FIXTURE, CONTROL})
    require(all(body == candidate[path] for path, body in applied.items()))


check("integration patch independently reconstructs the exact two selected files", exact_patch)


def rejection_controls():
    mutants = [(old, OLD)]
    for path in (FIXTURE, CONTROL, STARTUP, K03, "hosted/mix.lock"):
        changed = copy.deepcopy(new)
        changed[path]["sha256"] = "0" * 64
        mutants.append((changed, canonical(changed)))
    missing = copy.deepcopy(new)
    del missing[CONTROL]
    mutants.append((missing, canonical(missing)))
    extra = copy.deepcopy(new)
    extra["hosted/test/unselected_test.exs"] = row(b"unselected")
    mutants.append((extra, canonical(extra)))
    for manifest, claimed in mutants:
        for digest in (NEW, claimed):
            try:
                select(manifest, digest)
            except AssertionError:
                continue
            raise AssertionError("mutated source admitted")


check("16 stale/mutated/missing/extra/self-recomputed source decisions reject", rejection_controls)


def classify(stage, kind, value):
    if (kind, value) == ("error", "closed"):
        outcome, size = "peer_closed", 0
    elif (kind, value) == ("error", "timeout"):
        outcome, size = "timeout", 0
    elif kind == "ok" and isinstance(value, bytes):
        outcome, size = "unexpected_data", len(value)
    elif kind == "error":
        outcome, size = "transport_error", 0
    else:
        outcome, size = "unexpected_result", 0
    return {"stage": stage, "outcome": outcome, "unexpected_bytes": size}


def eof_model():
    for stage in ("handshake", "request", "peer_close"):
        for kind, value in (("error", "closed"), ("error", "timeout"), ("error", "reset"), ("ok", b"private-synthetic-payload"), ("other", None)):
            terminal = classify(stage, kind, value)
            require((terminal["outcome"] == "peer_closed") == (kind == "error" and value == "closed"))
            require("private-synthetic-payload" not in json.dumps(terminal))
            require(set(terminal) == {"stage", "outcome", "unexpected_bytes"})
    require(classify("peer_close", "ok", b"private-synthetic-payload")["unexpected_bytes"] == 25)


check("independent 15-case model distinguishes EOF from timeout/data/error", eof_model)


def ordering_model():
    unsafe = []
    valid = []
    for order in itertools.permutations(("accept_send", "go", "finish", "accept_receive", "finish_receive")):
        pos = {item: order.index(item) for item in order}
        if not (pos["accept_send"] < pos["go"] < pos["finish"] < pos["finish_receive"] and pos["accept_send"] < pos["accept_receive"]):
            continue
        if pos["finish_receive"] < pos["accept_receive"]:
            unsafe.append(order)
        if pos["accept_receive"] < pos["go"]:
            valid.append(order)
            require(pos["accept_receive"] < pos["finish_receive"])
    require(bool(unsafe) and bool(valid))
    terminals = []
    for _ in range(40):
        terminals = [classify("peer_close", "error", "closed"), *terminals][:16]
    require(len(terminals) == 16)


check("finite message-order model removes stale registration and bounds 40 outcomes to 16", ordering_model)


def source_scope():
    body = candidate[FIXTURE].decode()
    require("defp respond(_, :stall), do: :ok" in body)
    require("send(owner, {:closed, self()})" not in body)
    require(body.index("GenServer.call(owner, {:accepted, pid, socket})") < body.index("send(pid, :go)"))
    require("{:peer_close, :ssl.recv(socket, 0, 3_000)}" in body)
    require("closed: s.closed + if(peer_closed, do: 1, else: 0)" in body)
    tests = candidate[CONTROL].decode()
    require(len(re.findall(r'^  test "', tests, re.M)) == 4)
    require("@moduletag" not in tests and "@tag" not in tests)
    require("Process.sleep(10)" in tests and "remaining \\\\ 250" in tests)
    require("closed == 3" in baseline[STARTUP].decode())
    require("tries \\\\ 250" in baseline[STARTUP].decode())
    for path in ("hosted/mix.exs", "hosted/.formatter.exs", "hosted/scripts/test-local.py", ".github/workflows/hosted.yml", ".github/workflows/identity-network.yml", "hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py", "AGENTS.md"):
        read(ROOT / path)


check("source shape retains waits and exposes four unskipped ordinary-suite controls", source_scope)


def audit_negative():
    for event in sorted(BLOCKED | {"socket.__new__", "socket.connect"}):
        try:
            sys.audit(event, None)
        except RuntimeError:
            continue
        raise AssertionError("audit refusal missing")


check("synthetic child/socket/signal/wait audit events all refuse without execution", audit_negative)

for path in (FIXTURE, STARTUP, K03, "hosted/lib/mixer_hosted/identity/fetch_flight.ex", "hosted/lib/mixer_hosted/identity/bounded_tcp.ex"):
    target = HERE / "inputs/predecessor" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(baseline[path])
for path in (FIXTURE, CONTROL):
    target = HERE / "inputs/candidate" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(candidate[path])
read(RAW / "logs/0101.json")
read(RAW / "logs/0101.stdout")
write("readset.json", {"files": READSET, "predecessor_archive_source_members": old, "candidate_source_manifest": new})
write("source-controls.json", {
    "status": "passed-source-only", "checks": CHECKS, "count": len(CHECKS),
    "command": "python3 -B verification/identity-tls-fixture-independent/review_controls.py",
    "python_version": sys.version, "baseline_revision": "e9fc0e7d984c79bf2d3493f5d5d16a0b167b3af7",
    "baseline_run": 40770270255, "baseline_source_digest": OLD, "selected_source_digest": NEW,
    "selected_source_count": 178, "runtime_tests": "unrun",
    "model_limit": "Python accounting/order models are specification cross-checks, not Elixir, OTP, TLS or scheduling evidence.",
    "resources": "No child/runtime/socket/signal/wait, process inventory, native/UI/capture, Docker, PostgreSQL, Git mutation or dispatch invoked.",
})
print(f"Completed {len(CHECKS)} independent source/byte/model checks; runtime unrun.")
