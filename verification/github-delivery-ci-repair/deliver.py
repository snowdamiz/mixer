"""Deliver two source-reviewed CI corrections; preserve active implementation."""
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
BASE = "d87ce0a1b05a9ad42cd2118bbf2ccc5491499663"
DEADLINE = time.monotonic() + 55
PROTECTED = {
    ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
    "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
    "hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex": "cdb7b901a8e521361e1578bf0b47ea521a31c61c681c27d1f164925081238ba2",
    "hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs": "712dac61a33dbe7805a1e5f41c1f648c5b9ba482ac23952e9bc1ef0136a6cea6"}
CANONICAL = ["hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex", "hosted/priv/browser_auth/relation_surface_v1_pg16.json", "hosted/priv/browser_auth/relation_surface_v1_pg17.json", "vm/tests/span_execution.rs"]
METADATA = ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]
LANES = ["github-delivery-dependency-model", "hosted-dependency-relation-binding-correction", "vm-cancellation-ci-correction", "vm-cancellation-ci-correction-independent", "vm-cancellation-ci-correction-root-review", "hosted-dependency-advisory-correction-independent/http2-plan-review"]
CONSOLE = ["hosted-relation-binding-correction-review.json", "hosted-http2-source-selection.json"]
SWIFT = []
PROTECTED.update({"hosted/test/support/http2_wire_fixture.ex": "965c38f6dac459de2baaf3fee98c66ee663a013ccc9401d14d233fbab27794af", "hosted/test/mixer_hosted/billing/raw_webhook_capture_http2_test.exs": "4656e1f05e20ddfe8767be837a38d8323313efd7ef77efa7176a748c518c8ce8"})

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
relation = read(ROOT / "verification/console-session-and-checkout-root-review/hosted-relation-binding-correction-review.json")
vm = read(OUT / "vm-source-selection.json")
for expected in relation["canonical_sources"] + [vm["source"]]:
    assert row(ROOT / expected["path"]) == expected
assert vm["product_or_observer_changed"] is False
assert read(ROOT / "verification/vm-cancellation-ci-correction-root-review/format-receipt.json")["status"] == "passed"
assert not command("product-diff", ["git", "diff", "--name-only", "--", "vm/src", "vm/tests/common/allocation_observer.rs"])
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
     "scope": "Refresh relation whole-lock integrity bindings after reviewed dependency patches; deterministic memory-growth cancellation test; full remote CI pending",
     "active_inflight_lifecycle_and_future_verifier_implementation_excluded": True,
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
command("commit", ["git", "commit", "-m", "Refresh relation lock bindings and make cancellation test deterministic"])
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
     "active_inflight_lifecycle_and_future_verifier_implementation_excluded": True,
     "protected_work_unchanged": PROTECTED, "GA_accepted": False})
print(json.dumps({"commit": head, "tree": tree, "changed_paths": len(index), "pushed": True}))
