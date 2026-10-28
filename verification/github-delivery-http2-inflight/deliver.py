"""Deliver reviewed HTTP2 and in-flight lifecycle tests; preserve the active physical verifier."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import time
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
BASE = "c51f67c5c51b4172d8cae03b966b43f891bddb2d"
DEADLINE = time.monotonic() + 55
PROTECTED = {'.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57', 'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
CANONICAL = ['hosted/scripts/test-local.py', 'hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex', 'hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs', 'hosted/test/support/http2_wire_fixture.ex', 'hosted/test/mixer_hosted/billing/raw_webhook_capture_http2_test.exs']
METADATA = ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]
LANES = ['github-delivery-ci-repair', 'hosted-http2-format-root-1', 'hosted-dependency-advisory-correction/http2-implementation-v1', 'hosted-dependency-advisory-correction/http2-implementation-v2', 'hosted-dependency-advisory-correction-independent/http2-implementation-review-1', 'hosted-dependency-advisory-correction-independent/http2-implementation-review-2', 'console-key-owner-inflight-lifecycle-implementation/prepared-7', 'console-key-owner-inflight-lifecycle-implementation/prepared-8', 'console-key-owner-inflight-lifecycle-implementation/executions/custody-controls-5', 'console-key-owner-inflight-lifecycle-independent/custody-implementation-review-7', 'console-key-owner-inflight-lifecycle-independent/custody-implementation-review-8', 'console-key-owner-inflight-lifecycle-independent/custody-controls-terminal-review-2', 'console-key-owner-inflight-lifecycle-implementation/remote-ci-assessment-1', 'console-key-owner-inflight-lifecycle-implementation/remote-ci-collector-1', 'console-key-owner-inflight-lifecycle-independent/remote-ci-collector-review-1']
CONSOLE = ['inflight-custody-controls-candidate-8-release.json', 'inflight-custody-controls-5-scratch-cleanup.json', 'inflight-remote-ci-source-selection.json', 'hosted-http2-implementation-selection.json']
SWIFT = []

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def save(name, value):
    with (OUT / name).open("x") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")

def command(name, argv, cap=30):
    remaining = DEADLINE - time.monotonic()
    assert remaining > 8, "Delivery time budget exhausted before " + name
    start = time.monotonic()
    timed = False
    with (OUT / (name + ".stdout")).open("xb") as stdout, (OUT / (name + ".stderr")).open("xb") as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            child.wait(timeout=min(cap, remaining - 7))
        except subprocess.TimeoutExpired:
            timed = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=2)
    try:
        os.killpg(child.pid, 0)
        absent = False
    except ProcessLookupError:
        absent = True
    save(name + ".command.json", {"argv": argv, "exit": child.returncode, "timed_out": timed,
         "elapsed_seconds": time.monotonic() - start, "owned_pid": child.pid, "owned_pgid": child.pid,
         "direct_child_reaped": True, "owned_group_absent": absent,
         "stdout": row(OUT / (name + ".stdout")), "stderr": row(OUT / (name + ".stderr"))})
    assert not timed and absent and child.returncode == 0, name
    return (OUT / (name + ".stdout")).read_bytes()

assert not (OUT / "manifest.json").exists(), "One-shot; do not replay"
assert command("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert command("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
assert command("remote-before", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
assert not command("index-before", ["git", "diff", "--cached", "--name-only"])
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
inflight = read(ROOT / "verification/console-session-and-checkout-root-review/inflight-remote-ci-source-selection.json")
http2 = read(ROOT / "verification/console-session-and-checkout-root-review/hosted-http2-implementation-selection.json")
expected_sources = inflight["canonical_sources"] + http2["canonical_sources"]
assert {x["path"] for x in expected_sources} == set(CANONICAL)
for expected in expected_sources:
    assert row(ROOT / expected["path"]) == expected
for expected in [inflight["collector_review"], http2["review"], http2["review_seal"], http2["formatter_receipt"], http2["formatter_application"]]:
    assert row(ROOT / expected["path"]) == expected
assert inflight["local_custody_released"] is False and http2["actual_wire_runtime_passed"] is False
assert not command("product-diff", ["git", "diff", "--name-only", "--", "vm/src", "vm/tests", "hosted/lib/mixer_hosted/identity/key_owner.ex", "hosted/lib/mixer_hosted/identity/fetch_flight.ex", "hosted/lib/mixer_hosted/identity/fetch_admission.ex"])
w, g = read(ROOT / "work-graph.json"), read(ROOT / "gates/ga.json")
assert len(w["packages"]) == 18 and len(g["gates"]) == 38
assert sum(x["status"] == "running" for x in g["gates"]) == 8
assert sum(x["status"] == "planned" for x in g["gates"]) == 30
for wi, gi, key in [(13,21,"fixedWorkspaceDispatcher"),(7,1,"fixtureCacheStateContractCandidate"),(4,4,"privateOwnerEffectContractCandidate"),(15,24,"hostedDependencyAdvisoryCorrection")]:
    assert w["packages"][wi][key] == g["gates"][gi][key]
selected = {ROOT / p for p in CANONICAL + METADATA}
for name in LANES:
    lane = ROOT / "verification" / name
    assert lane.is_dir(), lane
    selected.update(p for p in lane.rglob("*") if p.is_file())
selected.update(ROOT / "verification/console-session-and-checkout-root-review" / n for n in CONSOLE)
selected.update(ROOT / "verification/swift-semantic-adapter-root-review" / n for n in SWIFT)
selected.update(p for p in OUT.rglob("*") if p.is_file())
assert len(selected) <= 1400 and sum(p.stat().st_size for p in selected) <= 32 * 1024 * 1024
members = [row(p) for p in sorted(selected)]
save("manifest.json", {"schema": 1, "base": BASE, "members": members, "canonical_paths": CANONICAL,
     "scope": "Reviewed HTTP2 wire tests and nine in-flight key-owner lifecycle tests with ordinary CI evidence collection; actual remote validation pending",
     "future_physical_verifier_implementation_excluded": True,
     "protected_dirty_paths_excluded": list(PROTECTED), "GA_accepted": False})
paths = [r["path"] for r in members] + [str((OUT / "manifest.json").relative_to(ROOT))]
with (OUT / "paths.nul").open("xb") as handle:
    handle.write(b"".join(p.encode() + b"\0" for p in paths))
command("stage", ["git", "add", "--force", "--pathspec-from-file=" + str(OUT / "paths.nul"), "--pathspec-file-nul"])
for expected in members:
    assert row(ROOT / expected["path"]) == expected
index = set(filter(None, command("index-selected", ["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0")))
assert index <= set(paths) and set(CANONICAL) <= index
authored = CANONICAL + METADATA + [str(Path(__file__).relative_to(ROOT))]
authored += [str((ROOT / "verification/console-session-and-checkout-root-review" / n).relative_to(ROOT)) for n in CONSOLE if n.endswith(".py")]
authored += [str((ROOT / "verification/swift-semantic-adapter-root-review" / n).relative_to(ROOT)) for n in SWIFT if n.endswith(".py")]
command("authored-check", ["git", "diff", "--cached", "--check", "--", *authored])
raw = command("staged-objects", ["git", "diff", "--cached", "--raw", "--no-abbrev", "-z"]).split(b"\0")
for offset in range(0, len(raw) - 1, 2):
    header = raw[offset].decode().split()
    path = raw[offset + 1].decode()
    assert len(header) == 5 and header[-1] in ("A", "M") and header[1] in ("100644", "100755")
    data = (ROOT / path).read_bytes()
    assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == header[3]
command("commit", ["git", "commit", "-m", "Exercise HTTP2 body limits and in-flight key-owner teardown"])
head = command("committed-head", ["git", "rev-parse", "HEAD"]).decode().strip()
tree = command("committed-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
assert command("committed-parent", ["git", "rev-parse", "HEAD^"]).decode().strip() == BASE
committed = set(filter(None, command("committed-paths", ["git", "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", "HEAD"]).decode().split("\0")))
assert committed == index
assert not command("index-after", ["git", "diff", "--cached", "--name-only"])
command("push", ["git", "push", "origin", "HEAD:main"])
assert command("remote-after", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
save("receipt.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "commit": head, "tree": tree,
     "parent": BASE, "committed_paths": len(index), "manifest": row(OUT / "manifest.json"),
     "canonical_paths": CANONICAL, "pushed": True, "force": False, "CI_pending": True,
     "future_physical_verifier_implementation_excluded": True,
     "protected_work_unchanged": PROTECTED, "GA_accepted": False})
print(json.dumps({"commit": head, "tree": tree, "changed_paths": len(index), "pushed": True}))
