"""One-shot delivery of accepted private host account and source146 composition."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import signal
import stat
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "f678177785accb9e74dbdcb7bbc84222b81c9448"
PROTECTED = {
    ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
    "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
}


def identity(path):
    assert stat.S_ISREG(path.lstat().st_mode), path
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save(name, data):
    with (OUT / name).open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def command(name, argv, timeout=60):
    start = time.monotonic()
    timed_out = False
    with (OUT / (name + ".stdout")).open("xb") as stdout, (OUT / (name + ".stderr")).open("xb") as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            if group_exists(child.pid):
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                until = time.monotonic() + 5
                while group_exists(child.pid) and time.monotonic() < until:
                    child.poll()
                    time.sleep(0.05)
                if group_exists(child.pid):
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            child.wait(timeout=5)
    absent = not group_exists(child.pid)
    save(name + ".command.json", {
        "argv": argv, "exit": child.returncode, "timed_out": timed_out,
        "elapsed_seconds": time.monotonic() - start,
        "finished": datetime.now(timezone.utc).isoformat(),
        "direct_child_reaped": True, "owned_group_observed_absent": absent,
        "stdout": identity(OUT / (name + ".stdout")),
        "stderr": identity(OUT / (name + ".stderr")),
    })
    assert not timed_out and absent and child.returncode == 0, name
    return (OUT / (name + ".stdout")).read_bytes()


assert __debug__ and not (OUT / "manifest.json").exists(), "One-shot; do not replay"
release = json.loads((OUT / "release-selection.json").read_bytes())
assert release["ready"] is True, "Root acceptance is not yet released"
assert len(release["packets"]) == 5
assert command("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert command("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
assert command("remote", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
assert not command("index-before", ["git", "diff", "--cached", "--name-only"])
for path, sha in PROTECTED.items():
    assert identity(ROOT / path)["sha256"] == sha
validation = json.loads((OUT / "metadata-validation.json").read_bytes())
assert validation["passed"] is True
for row in validation["metadata_files"]:
    assert identity(ROOT / row["path"]) == {key: row[key] for key in ("bytes", "sha256")}
work = json.loads((ROOT / "work-graph.json").read_bytes())
gates = json.loads((ROOT / "gates/ga.json").read_bytes())
assert [p["id"] for p in work["packages"]] == [f"W{i:02}" for i in range(1, 19)]
assert [g["id"] for g in gates["gates"]] == [f"G{i:02}" for i in range(1, 39)]
assert sum(g["status"] == "running" for g in gates["gates"]) == 8
assert sum(g["status"] == "planned" for g in gates["gates"]) == 30
assert work["packages"][4]["privateOwnerEffectContractCandidate"] == gates["gates"][4]["privateOwnerEffectContractCandidate"]
assert work["packages"][7]["fixtureCacheStateContractCandidate"] == gates["gates"][1]["fixtureCacheStateContractCandidate"]

selected = {ROOT / path for path in ("PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json")}
custody = []
for packet in release["packets"]:
    folder = ROOT / "verification" / packet["path"]
    assert identity(folder / "seal.json")["sha256"] == packet["seal_sha256"]
    seal = json.loads((folder / "seal.json").read_bytes())
    names = {"seal.json"}
    for row in seal["members"]:
        path = PurePosixPath(row["path"])
        assert not path.is_absolute() and ".." not in path.parts and ".git" not in path.parts
        assert str(path) == row["path"] and row["path"] not in names
        assert identity(folder / path) == {key: row[key] for key in ("bytes", "sha256")}
        names.add(row["path"])
    for row in packet.get("postseal_files", []):
        assert row["path"] == "freeze-receipt.json"
        assert identity(folder / row["path"]) == {key: row[key] for key in ("bytes", "sha256")}
        receipt = json.loads((folder / row["path"]).read_bytes())
        assert receipt["seal_sha256"] == packet["seal_sha256"]
        assert receipt["member_count"] == len(seal["members"])
        names.add(row["path"])
    for row in packet.get("historical_seal_files", []):
        assert packet["path"] == "swift-guarded-snapshot-host-account-entry"
        assert row == {"path": "attempts/02-parameter-parser-repair/seal.json", "bytes": 24852,
                       "sha256": "23f4ff890933621745b642c06f538d45f590503a501fc5f82c47cdd7c663e082"}
        assert row["path"] not in names
        assert identity(folder / row["path"]) == {key: row[key] for key in ("bytes", "sha256")}
        names.add(row["path"])
    actual = set()
    for directory, dirs, files in os.walk(folder, followlinks=False):
        for name in dirs + files:
            assert not (Path(directory) / name).is_symlink()
        actual.update(str((Path(directory) / name).relative_to(folder)) for name in files)
    assert actual - names == set(packet.get("excluded_nonmembers", [])), (packet["path"], actual - names)
    assert not names - actual
    assert all(name.startswith("__pycache__/") and name.endswith(".pyc") for name in packet.get("excluded_nonmembers", []))
    selected.update(folder / name for name in names)
    custody.append({"packet": packet["path"], "seal_sha256": packet["seal_sha256"], "members_verified": len(seal["members"])})

for row in release["root_and_source_files"]:
    assert identity(ROOT / row["path"]) == {key: row[key] for key in ("bytes", "sha256")}
    selected.add(ROOT / row["path"])
for row in release["parent_delivery_files"]:
    assert row["path"].startswith("verification/github-delivery-snapshot-admission-composition/")
    assert identity(ROOT / row["path"]) == {key: row[key] for key in ("bytes", "sha256")}
    selected.add(ROOT / row["path"])
for name in ("deliver-corrected.py", "release-selection.json", "metadata-validation.json"):
    selected.add(OUT / name)
rows = [{"path": str(path.relative_to(ROOT)), **identity(path)} for path in sorted(selected)]
assert all(row["bytes"] < 100 * 1024 * 1024 for row in rows)
assert all(not row["path"].startswith((
    "verification/swift-guarded-snapshot-parent-work/",
    "verification/swift-guarded-snapshot-loader-work/",
    "verification/swift-guarded-snapshot-loader-work-independent/",
    "verification/swift-guarded-snapshot-loader-work-correction/",
    "verification/swift-guarded-snapshot-loader-work-source146/",
    "verification/swift-guarded-snapshot-parent-work-independent/",
    "hosted/", ".github/", "android/",
)) for row in rows)
save("manifest.json", {"schema": 1, "base": BASE, "members": rows,
    "member_count": len(rows), "packet_custody": custody, "scope": release["scope"]})
paths = [row["path"] for row in rows] + [str((OUT / "manifest.json").relative_to(ROOT))]
(OUT / "paths.nul").write_bytes(b"".join(path.encode() + b"\0" for path in paths))
command("stage", ["git", "add", "--force", "--pathspec-from-file=" + str(OUT / "paths.nul"), "--pathspec-file-nul"])
for row in rows:
    assert identity(ROOT / row["path"]) == {key: row[key] for key in ("bytes", "sha256")}
index = set(filter(None, command("index-selected", ["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0")))
assert index <= set(paths)
assert set(release["canonical_paths"]) <= index
check = [path for path in index if path in {"PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"}
         or path.startswith("vm/") or path == str(Path(__file__).relative_to(ROOT))]
command("authored-index-check", ["git", "diff", "--cached", "--check", "--", *sorted(check)])
raw = command("staged-object-map", ["git", "diff", "--cached", "--raw", "--no-abbrev", "-z"]).split(b"\0")
for index_offset in range(0, len(raw) - 1, 2):
    header = raw[index_offset].decode().split()
    path = raw[index_offset + 1].decode()
    assert len(header) == 5 and header[-1] in ("A", "M") and header[1] in ("100644", "100755")
    data = (ROOT / path).read_bytes()
    assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == header[3]
command("commit", ["git", "commit", "-m", "Compose isolated snapshot host account and typed entry"])
head = command("after-head", ["git", "rev-parse", "HEAD"]).decode().strip()
tree = command("tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
assert command("parent", ["git", "rev-parse", "HEAD^"]).decode().strip() == BASE
committed = set(filter(None, command("committed-paths", ["git", "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", "HEAD"]).decode().split("\0")))
assert committed == index
assert not command("index-after", ["git", "diff", "--cached", "--name-only"])
command("push", ["git", "push", "origin", "HEAD:main"], timeout=300)
assert command("remote-after", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
for path, sha in PROTECTED.items():
    assert identity(ROOT / path)["sha256"] == sha
save("receipt.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "commit": head, "tree": tree, "parent": BASE, "committed_paths": len(index),
    "manifest_sha256": identity(OUT / "manifest.json")["sha256"], "pushed": True,
    "force": False, "canonical_paths": release["canonical_paths"],
    "protected_work_unchanged": PROTECTED, "parent_and_loader_work_lanes_excluded": True,
    "canonical_product_changed": False, "CI_pending": True, "native_OTA_GA_accepted": False})
print(json.dumps({"commit": head, "tree": tree, "paths": len(index), "pushed": True}))
