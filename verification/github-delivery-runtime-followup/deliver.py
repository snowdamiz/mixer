"""Deliver reviewed tooling execution correction and the second empirical cache campaign."""
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
BASE = "cc350d3303ca71c5d57e87846f6a61304b658fa7"
DEADLINE = time.monotonic() + 240
PROTECTED = {'.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57', 'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
METADATA = ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]
CANONICAL = ['.github/workflows/identity-network.yml', 'docs/hosted-identity-production-network-ci-contract.md', 'hosted/scripts/test-identity-network.py', 'hosted/scripts/test_identity_network_collector.py', '.github/workflows/swift-cache-deadline-campaign-v2.yml']
LANES = ['github-delivery-blocker-campaign', 'identity-network-image-amendment-v2', 'identity-network-execution-amendment-independent', 'swift-cache-deadline-campaign-v2', 'swift-cache-deadline-campaign-v2-correction', 'swift-cache-deadline-campaign-root-review']
CONSOLE = ['identity-network-execution-selection.json']
SWIFT = ['cache-deadline-campaign-selection.json']
EXTRA = ['verification/fieldlog-public-sdk-root-review/private-host-ci-observation.json']

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
command("git-version", ["git", "--version"])
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
selection = read(ROOT / "verification/console-session-and-checkout-root-review/identity-network-execution-selection.json")
assert {r["path"] for r in selection["canonical_sources"]} == set(CANONICAL[:4])
for expected in selection["canonical_sources"] + [selection["independent_decision"], selection["independent_manifest"]]:
    assert row(ROOT / expected["path"]) == expected
assert selection["canonical_controls"] == 103 and selection["independent_controls"] == 16
assert selection["remote_execution_selected"] and not selection["runtime_or_GA_acceptance"]
campaign = read(ROOT / "verification/swift-semantic-adapter-root-review/cache-deadline-campaign-selection.json")
for key in ["workflow", "campaign", "review", "packet_seal"]:
    expected = campaign[key]
    assert row(ROOT / expected["path"]) == expected
assert campaign["maximum_full_attempts"] == 2 and campaign["full_attempts_run"] == 0
assert campaign["exceptional_unproven_command_retains_scratch_and_stops"]
assert campaign["first_campaign_closed_fifth_unselected"] and campaign["remote_execution_selected"]
assert not campaign["actual_feasibility_or_GA_accepted"]
assert not command("product-source-diff", ["git", "diff", "--name-only", "--", "vm/src", "vm/tests", "hosted/test", "hosted/lib/mixer_hosted/identity", "hosted/mix.exs", "hosted/mix.lock", "hosted/scripts/test-local.py"])
w, g = read(ROOT / "work-graph.json"), read(ROOT / "gates/ga.json")
assert len(w["packages"]) == 18 and len(g["gates"]) == 38
assert sum(x["status"] == "running" for x in g["gates"]) == 8
assert sum(x["status"] == "planned" for x in g["gates"]) == 30
for wi, gi, key in [(13,21,"fixedWorkspaceDispatcher"),(7,1,"physicalRegionVerifier"),(13,21,"identityProductionNetworkCI"),(4,4,"privateOwnerEffectContractCandidate"),(7,1,"empiricalCacheCapacityCampaign"),(7,1,"empiricalCacheDeadlineCampaign")]:
    assert w["packages"][wi][key] == g["gates"][gi][key]
selected = {ROOT / p for p in CANONICAL + METADATA + EXTRA}
for name in LANES:
    lane = ROOT / "verification" / name
    assert lane.is_dir(), lane
    selected.update(p for p in lane.rglob("*") if p.is_file())
selected.update(ROOT / "verification/console-session-and-checkout-root-review" / n for n in CONSOLE)
selected.update(ROOT / "verification/swift-semantic-adapter-root-review" / n for n in SWIFT)
selected.update(p for p in OUT.rglob("*") if p.is_file())
assert all("fieldlog-private-remote-delivery" not in str(p) and "fieldlog-public-sdk-next-flow" not in str(p) for p in selected)
assert len(selected) <= 2500 and sum(p.stat().st_size for p in selected) <= 96 * 1024 * 1024
assert max(p.stat().st_size for p in selected) < 100 * 1024 * 1024
members = [row(p) for p in sorted(selected)]
save("manifest.json", {"schema": 1, "base": BASE, "members": members, "canonical_paths": CANONICAL,
     "scope": "Reviewed bounded tooling execution amendment; closed first cache campaign with actual failures and second deadline comparison selected; ordinary exact-head Engine/Phoenix evidence; sanitized private FieldLog billing block only; no GA acceptance",
     "private_FieldLog_sources_raw_evidence_and_local_compiler_attempt_excluded": True,
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
command("commit", ["git", "commit", "-m", "Fix isolated tooling execution and test the cache runtime deadline"])
head = command("committed-head", ["git", "rev-parse", "HEAD"]).decode().strip()
tree = command("committed-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
assert command("committed-parent", ["git", "rev-parse", "HEAD^"]).decode().strip() == BASE
committed = set(filter(None, command("committed-paths", ["git", "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", "HEAD"]).decode().split("\0")))
assert committed == index
assert not command("index-after", ["git", "diff", "--cached", "--name-only"])
command("push", ["git", "-c", "pack.window=0", "push", "origin", "HEAD:main"], cap=120)
assert command("remote-after", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
save("receipt.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "commit": head, "tree": tree,
     "parent": BASE, "committed_paths": len(index), "manifest": row(OUT / "manifest.json"),
     "canonical_paths": CANONICAL, "pushed": True, "force": False, "CI_pending": True,
     "private_FieldLog_sources_raw_evidence_and_local_compiler_attempt_excluded": True,
     "protected_work_unchanged": PROTECTED, "GA_accepted": False})
print(json.dumps({"commit": head, "tree": tree, "changed_paths": len(index), "pushed": True}))
