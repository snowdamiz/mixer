"""One-shot root-authorized timestamp delivery. Never replay historical helpers."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import platform
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
BASE = "dfd0e3196543cc1749c9cc924cc7accf28c9dc25"
BASE_TREE = "3cc58d6744649fdd138b9d3963b436db62480ecf"
DEADLINE = time.monotonic() + 300
PROTECTED = {
    ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
    "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
}
CANONICAL = {
    "hosted/scripts/test-identity-network.py": "d9d750256b2734c80577f58b4eb9c8cfd0adf177ba12a453ecb1c050d0942c0e",
    "hosted/scripts/test_identity_network_collector.py": "8d3b37474fc132aa91d02f643956f87cfa2d177305aee167819ce3c5edd68691",
    "docs/hosted-identity-production-network-ci-contract.md": "37d2b3679bdedf9fbc7621f8ebaec81b27bb0d6de18b4d1dea0d3cfe3fc631db",
}
METADATA = ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]
PREEXECUTION = ["prepare.py", "deliver.py", "selection.json", "metadata-checkpoint.json", "preparation-observation.json", "prior-ci-observation.json", "fieldlog-public-fields-observation.json", "architecture-saved-observation.json"]
COMMANDS = []

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def save(name, data):
    with (OUT / name).open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")

def command(name, argv, cap=30):
    if argv[0] == "git":
        argv = ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", *argv[1:]]
    remaining = DEADLINE - time.monotonic()
    assert remaining > 8, "Delivery budget exhausted before " + name
    start = time.monotonic()
    timed_out = False
    with (OUT / (name + ".stdout")).open("xb") as stdout, (OUT / (name + ".stderr")).open("xb") as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            child.wait(timeout=min(cap, remaining - 7))
        except subprocess.TimeoutExpired:
            timed_out = True
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
    record = {"argv": argv, "exit": child.returncode, "timed_out": timed_out,
              "elapsed_seconds": time.monotonic() - start, "owned_pid": child.pid, "owned_pgid": child.pid,
              "direct_child_reaped": True, "owned_group_absent": absent,
              "stdout": row(OUT / (name + ".stdout")), "stderr": row(OUT / (name + ".stderr"))}
    save(name + ".command.json", record)
    COMMANDS.append({"name": name, "exit": child.returncode, "direct_child_reaped": True, "owned_group_absent": absent})
    assert not timed_out and absent and child.returncode == 0, name
    return (OUT / (name + ".stdout")).read_bytes()

assert not (OUT / "manifest.json").exists(), "One-shot; do not replay"
assert command("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert command("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
assert command("base-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip() == BASE_TREE
assert command("remote-before", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
assert not command("index-before", ["git", "diff", "--cached", "--name-only", "-z"])
command("git-version", ["git", "--version"])
for path, digest in {**CANONICAL, **PROTECTED}.items():
    assert row(ROOT / path)["sha256"] == digest, path
selection = read(OUT / "selection.json")
assert selection["basisRevision"] == BASE and selection["basisTree"] == BASE_TREE
assert not selection["runtime_or_GA_accepted"] and not selection["new_manual_dispatch_or_retry_selected"]
selected = {ROOT / path for path in [*CANONICAL, *METADATA]}
for expected in selection["producer_packet"]:
    path = ROOT / expected["path"]
    assert row(path) == expected
    selected.add(path)
independent = ROOT / "verification/identity-network-timestamp-independent"
assert row(independent / "packet-manifest.json") == selection["independent_manifest"]
packet = read(independent / "packet-manifest.json")
assert hashlib.sha256(json.dumps(packet["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest() == selection["independent_packet_map_digest"]
for path, expected in packet["files"].items():
    assert not Path(path).is_absolute() and ".." not in Path(path).parts
    actual = row(independent / path)
    assert {key: actual[key] for key in ("bytes", "sha256")} == expected
    selected.add(independent / path)
selected.add(independent / "packet-manifest.json")
for expected in read(OUT / "metadata-checkpoint.json")["after"]:
    assert row(ROOT / expected["path"]) == expected
w, g = read(ROOT / "work-graph.json"), read(ROOT / "gates/ga.json")
assert [sum(item["status"] == state for item in g["gates"]) for state in ("running", "planned", "verified")] == [8, 30, 0]
for wi, gi, key in [(13, 21, "identityProductionNetworkCI"), (7, 1, "empiricalCacheDeadlineCampaign")]:
    assert w["packages"][wi][key] == g["gates"][gi][key]
selected.update(OUT / name for name in PREEXECUTION)
selected.update(ROOT / "verification/github-delivery-architecture-comparison" / name for name in ("receipt.json", "dispatch-observation.json"))
relative_paths = {str(path.relative_to(ROOT)) for path in selected}
assert not set(PROTECTED) & relative_paths
assert all("/.codex" not in str(path) and "/.wrangler" not in str(path) and "/ci-review/" not in str(path) for path in selected)
assert len(selected) < 100 and sum(path.stat().st_size for path in selected) < 5 * 1024 * 1024
assert max(path.stat().st_size for path in selected) < 2 * 1024 * 1024
assert max(path.stat().st_size for path in selected if str(path.relative_to(ROOT)) not in METADATA) < 300000
members = [row(path) for path in sorted(selected)]
save("manifest.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
                       "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))], "python": platform.python_version(),
                       "base": BASE, "base_tree": BASE_TREE, "members": members, "canonical_paths": list(CANONICAL),
                       "scope": "Minimal deterministic positive prepared archive timestamp correction and independently accepted pure evidence; runtime pending",
                       "large_raw_CI_packet_local_only": True, "prior_helpers_not_replayed": True,
                       "native_compiler_runtime_custody_inventory_or_capture_actions": False,
                       "other_active_lanes_and_FieldLog_source_raw_excluded": True,
                       "protected_dirty_paths_excluded": list(PROTECTED), "GA_accepted": False})
paths = [member["path"] for member in members] + [str((OUT / "manifest.json").relative_to(ROOT))]
with (OUT / "paths.nul").open("xb") as stream:
    stream.write(b"".join(path.encode() + b"\0" for path in paths))
command("stage", ["git", "add", "--force", "--pathspec-from-file=" + str(OUT / "paths.nul"), "--pathspec-file-nul"])
for expected in members:
    assert row(ROOT / expected["path"]) == expected
index = set(filter(None, command("index-selected", ["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0")))
assert index <= set(paths) and set(CANONICAL) <= index and set(METADATA) <= index
command("authored-check", ["git", "diff", "--cached", "--check", "--", *CANONICAL, *METADATA, *[str((OUT / name).relative_to(ROOT)) for name in PREEXECUTION]])
raw = command("staged-objects", ["git", "diff", "--cached", "--raw", "--no-abbrev", "-z"]).split(b"\0")
for offset in range(0, len(raw) - 1, 2):
    header, path = raw[offset].decode().split(), raw[offset + 1].decode()
    assert len(header) == 5 and header[-1] in ("A", "M") and header[1] in ("100644", "100755")
    data = (ROOT / path).read_bytes()
    assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == header[3]
command("commit", ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "commit", "-m", "Fix deterministic prepared archive timestamp for JOSE compilation"])
head = command("committed-head", ["git", "rev-parse", "HEAD"]).decode().strip()
tree = command("committed-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
assert command("committed-parent", ["git", "rev-parse", "HEAD^"]).decode().strip() == BASE
committed = set(filter(None, command("committed-paths", ["git", "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", "HEAD"]).decode().split("\0")))
assert committed == index
assert not command("index-after", ["git", "diff", "--cached", "--name-only", "-z"])
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
command("push", ["git", "-c", "core.hooksPath=/dev/null", "-c", "pack.window=0", "push", "origin", "HEAD:refs/heads/main"], cap=120)
assert command("remote-after", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
save("receipt.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "commit": head, "tree": tree, "parent": BASE,
                      "committed_paths": len(index), "manifest": row(OUT / "manifest.json"), "canonical_paths": list(CANONICAL),
                      "pushed": True, "force": False, "CI_pending": True, "selected_files": len(members),
                      "selected_bytes": sum(member["bytes"] for member in members), "all_new_commands": COMMANDS,
                      "all_new_commands_reaped_and_groups_absent": all(item["direct_child_reaped"] and item["owned_group_absent"] for item in COMMANDS),
                      "other_active_lanes_and_FieldLog_source_raw_excluded": True, "large_raw_CI_packet_local_only": True,
                      "protected_work_unchanged": PROTECTED, "wrangler_untouched": True, "GA_accepted": False})
print(json.dumps({"commit": head, "tree": tree, "committed_paths": len(index), "selected_files": len(members), "selected_bytes": sum(member["bytes"] for member in members), "pushed": True, "new_commands": len(COMMANDS), "all_cleanup_verified": True}))
