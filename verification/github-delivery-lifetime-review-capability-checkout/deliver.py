"""Explicit-path delivery; exclude all active authority and work/storage lanes."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "d04fd5cc71bc72061f18203e414b90869129b4ca"
PROTECTED = {
    ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
    "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
}


def row(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


def save(name, value):
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def command(name, argv, timeout=45):
    start = time.monotonic(); timed = False
    with (OUT / (name + ".stdout")).open("xb") as stdout, (OUT / (name + ".stderr")).open("xb") as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
    try:
        os.killpg(child.pid, 0); absent = False
    except ProcessLookupError:
        absent = True
    save(name + ".command.json", {"argv": argv, "exit": child.returncode, "timed_out": timed,
        "elapsed_seconds": time.monotonic() - start, "owned_pid": child.pid, "owned_pgid": child.pid,
        "direct_child_reaped": True, "owned_group_observed_absent": absent,
        "stdout": row(OUT / (name + ".stdout")), "stderr": row(OUT / (name + ".stderr"))})
    assert not timed and absent and child.returncode == 0, name
    return (OUT / (name + ".stdout")).read_bytes()


assert not (OUT / "manifest.json").exists(), "One-shot; do not replay"
assert command("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert command("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
assert command("remote", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
assert not command("index-before", ["git", "diff", "--cached", "--name-only"])
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
review = ROOT / "verification/console-session-and-checkout-root-review"
formatter = read(review / "fixed-dispatcher-format-acceptance.json")
checkout = read(review / "swift-capability-checkout-acceptance.json")
rust_review = ROOT / "verification/swift-semantic-adapter-root-review"
rust = read(rust_review / "guarded-snapshot-root-result-lifetime-acceptance.json")
assert formatter["syntax_and_normalized_AST_equal"] and formatter["explicit_six_file_formatter_check_passed"]
assert rust["status"] == "accepted-minimum-accessible-original-root-result-lifetime-source-slice-only"
assert not rust["canonical_source_integrated"] and not rust["GA_accepted"]
for expected in formatter["canonical_files"] + [checkout["workflow_after"]]:
    assert row(ROOT / expected["path"]) == expected
canonical = formatter["changed_canonical_files"] + [".github/workflows/verify.yml"]
selected = {ROOT / p for p in canonical + ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]}
for packet in rust["packets"]:
    directory = ROOT / packet["directory"]
    assert row(directory / "seal.json") == packet["seal"]
    seal = read(directory / "seal.json")
    for expected in seal["members"]:
        actual = row(directory / expected["path"])
        assert actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"]
        selected.add(directory / expected["path"])
    selected.add(directory / "seal.json")
    assert {p for p in directory.rglob("*") if p.is_file()} <= selected
for packet in checkout["packets"]:
    for expected in packet["members"] + [packet["manifest"]]:
        assert row(ROOT / expected["path"]) == expected
        selected.add(ROOT / expected["path"])
for expected in formatter["packet_members"] + [formatter["packet_seal"]]:
    assert row(ROOT / expected["path"]) == expected
    selected.add(ROOT / expected["path"])
for name in ["guarded-snapshot-root-result-lifetime-execution-release.json",
             "guarded-snapshot-root-result-lifetime-independent-execution-release.json",
             "accept-root-result-lifetime.py", "guarded-snapshot-root-result-lifetime-acceptance.json"]:
    selected.add(rust_review / name)
for directory in [review, ROOT / "verification/github-delivery-fixed-dispatcher-android-checkout"]:
    selected.update(p for p in directory.rglob("*") if p.is_file())
selected.update([Path(__file__).resolve(), OUT / "observe-ci.py"])
rows = [row(path) for path in sorted(selected)]
assert all(r["bytes"] < 100 * 1024 * 1024 for r in rows)
excluded = ("vm/", "native/", ".github/workflows/hosted.yml", "hosted/lib/mixer_hosted/browser_auth/",
            "verification/console-dispatcher-default-authority-slice/",
            "verification/console-dispatcher-authority-preaccess/", "verification/swift-root-bound-work-storage-delta/")
assert all(not r["path"].startswith(excluded) for r in rows)
w = read(ROOT / "work-graph.json"); g = read(ROOT / "gates/ga.json")
assert [p["id"] for p in w["packages"]] == [f"W{i:02}" for i in range(1, 19)]
assert [p["id"] for p in g["gates"]] == [f"G{i:02}" for i in range(1, 39)]
assert sum(p["status"] == "running" for p in g["gates"]) == 8
assert sum(p["status"] == "planned" for p in g["gates"]) == 30
assert w["packages"][7]["fixtureCacheStateContractCandidate"] == g["gates"][1]["fixtureCacheStateContractCandidate"]
assert w["packages"][4]["privateOwnerEffectContractCandidate"] == g["gates"][4]["privateOwnerEffectContractCandidate"]
assert [p["id"] for p in read(ROOT / "dogfood/receipts/milestones.json")["milestones"]] == [f"D{i}" for i in range(9)]
save("manifest.json", {"schema": 1, "base": BASE, "members": rows, "canonical_paths": canonical,
    "scope": "Four-file formatting-only dispatcher correction and accepted Swift capability checkout; bounded isolated IR02 lifetime repair/review and terminal parent CI evidence. Active authority and work/storage lanes excluded."})
paths = [r["path"] for r in rows] + [str((OUT / "manifest.json").relative_to(ROOT))]
(OUT / "paths.nul").write_bytes(b"".join(p.encode() + b"\0" for p in paths))
command("stage", ["git", "add", "--force", "--pathspec-from-file=" + str(OUT / "paths.nul"), "--pathspec-file-nul"])
for expected in rows:
    assert row(ROOT / expected["path"]) == expected
index = set(filter(None, command("index-selected", ["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0")))
assert index <= set(paths) and set(canonical) <= index
command("authored-check", ["git", "diff", "--cached", "--check", "--", *canonical,
    "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json", str(Path(__file__).relative_to(ROOT))])
raw = command("staged-objects", ["git", "diff", "--cached", "--raw", "--no-abbrev", "-z"]).split(b"\0")
for offset in range(0, len(raw) - 1, 2):
    header = raw[offset].decode().split(); path = raw[offset + 1].decode()
    assert len(header) == 5 and header[-1] in ("A", "M") and header[1] in ("100644", "100755")
    data = (ROOT / path).read_bytes()
    assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == header[3]
command("commit", ["git", "commit", "-m", "Fix dispatcher formatting and bound Swift capability checkout"])
head = command("after-head", ["git", "rev-parse", "HEAD"]).decode().strip()
tree = command("tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
assert command("parent", ["git", "rev-parse", "HEAD^"]).decode().strip() == BASE
committed = set(filter(None, command("committed-paths", ["git", "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", "HEAD"]).decode().split("\0")))
assert committed == index
assert not command("index-after", ["git", "diff", "--cached", "--name-only"])
command("push", ["git", "push", "origin", "HEAD:main"])
assert command("remote-after", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
save("receipt.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "commit": head,
    "tree": tree, "parent": BASE, "committed_paths": len(index), "manifest": row(OUT / "manifest.json"),
    "pushed": True, "force": False, "canonical_paths": canonical, "protected_work_unchanged": PROTECTED,
    "active_authority_and_work_storage_lanes_excluded": True, "CI_pending": True,
    "full_ownership_funding_default_Repo_session_provider_native_customer_or_GA_acceptance": False})
print(json.dumps({"commit": head, "tree": tree, "changed_paths": len(index), "pushed": True}))
