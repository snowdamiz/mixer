"""Deliver isolated identity network CI and closed compiler capture/mapping evidence."""
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
BASE = "9e860ea12074ca31bef4087ce34177a03f295dd8"
DEADLINE = time.monotonic() + 180
PROTECTED = {'.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57', 'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
METADATA = ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]
CANONICAL = ['hosted/scripts/test-identity-network.py', 'hosted/scripts/test_identity_network_collector.py', '.github/workflows/identity-network.yml', 'docs/hosted-identity-production-network-ci-contract.md', 'THIRD_PARTY.yml']
LANES = ['github-delivery-owner-drain', 'swift-root-bound-dispatch-physical-capture-v1', 'swift-root-bound-dispatch-physical-capture-independent', 'swift-root-bound-dispatch-physical-capture-runtime-review-1', 'swift-physical-map-caller-closure', 'swift-physical-map-dispatch-body', 'swift-physical-map-independent', 'swift-physical-source-reachability', 'swift-root-bound-dispatch-retained-capture-v1', 'swift-root-bound-dispatch-retained-capture-independent', 'swift-retained-capture-terminal-mapping', 'identity-production-network-next-scope', 'identity-production-network-contract', 'identity-production-network-contract-independent', 'identity-production-network-implementation', 'identity-production-network-controls', 'identity-production-network-implementation-independent']
CONSOLE = ['identity-network-implementation-selection.json', 'identity-network-inventory-selection.json', 'identity-network-source-acceptance.json']
SWIFT = ['dispatch-physical-capture-release.json', 'dispatch-physical-capture-acceptance.json', 'dispatch-physical-mapping-selection.json', 'dispatch-physical-mapping-acceptance.json', 'dispatch-retained-physical-capture-release.json', 'dispatch-retained-physical-identity-acceptance.json']

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

HEAD = "756695fb9b0f6ec85d978202e2b3c586aa3db16f"
assert read(OUT / "push.command.json")["timed_out"] is True
assert command("recovery-head", ["git", "rev-parse", "HEAD"]).decode().strip() == HEAD
assert not command("recovery-index", ["git", "diff", "--cached", "--name-only"])
assert command("recovery-remote", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
command("push-recovery", ["git", "-c", "pack.window=0", "push", "--progress", "origin", "HEAD:main"], cap=150)
assert command("remote-after", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == HEAD
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
index = set(filter(None, (OUT / "index-selected.stdout").read_bytes().decode().split("\0")))
save("receipt.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "commit": HEAD,
     "tree": (OUT / "committed-tree.stdout").read_text().strip(), "parent": BASE,
     "committed_paths": len(index), "manifest": row(OUT / "manifest.json"), "canonical_paths": CANONICAL,
     "pushed": True, "force": False, "CI_pending": True,
     "first_push_timed_out_after_30s": True, "first_owned_child_reaped_and_group_absent": True,
     "remote_verified_base_before_recovery": True, "recovery_transport_only_pack_window": 0,
     "active_geometry_fact_preparations_excluded": True, "protected_work_unchanged": PROTECTED, "GA_accepted": False})
print(json.dumps({"commit": HEAD, "changed_paths": len(index), "pushed": True, "first_push_timeout_preserved": True}))
