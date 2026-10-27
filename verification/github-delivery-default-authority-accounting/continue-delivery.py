"""Deliver the accepted dispatcher CI correction, actual-default host evidence and finite accounting inventory."""
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
BASE = "6f116c6a41994fcab5fa0d203198dc139dae9829"
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


assert not (OUT / "manifest-v2.json").exists(), "One-shot continuation; do not replay"
assert command("resume-branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert command("resume-head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
assert command("resume-remote", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
old = read(OUT / "manifest.json")
correction = read(OUT / "authored-whitespace-correction.json")
rows = old["members"]
original_script = str((OUT / "deliver.py").relative_to(ROOT))
for expected in rows:
    actual = row(ROOT / expected["path"])
    if expected["path"] == original_script:
        assert expected["sha256"] == correction["before_sha256"]
        assert actual["sha256"] == correction["after_sha256"]
    else:
        assert actual == expected
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
old_paths = {r["path"] for r in rows} | {str((OUT / "manifest.json").relative_to(ROOT))}
index = set(filter(None, command("resume-index-before", ["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0")))
assert index == set(filter(None, (OUT / "index-selected.stdout").read_bytes().decode().split("\0")))
assert index <= old_paths
selected = {ROOT / r["path"] for r in rows}
selected.update(p for p in OUT.iterdir() if p.is_file() and not p.name.startswith("resume-"))
selected.add(Path(__file__).resolve())
current = [row(p) for p in sorted(selected)]
save("manifest-v2.json", {"schema": 1, "base": BASE, "members": current, "prior_manifest": row(OUT / "manifest.json"), "scope": old["scope"], "canonical_paths": old["canonical_paths"], "continuation_reason": correction["reason"]})
paths = [r["path"] for r in current] + [str((OUT / "manifest-v2.json").relative_to(ROOT))]
with (OUT / "resume-paths.nul").open("xb") as f:
    f.write(b"".join(p.encode() + b"\0" for p in paths))
command("resume-stage", ["git", "add", "--force", "--pathspec-from-file=" + str(OUT / "resume-paths.nul"), "--pathspec-file-nul"])
for expected in current:
    assert row(ROOT / expected["path"]) == expected
index = set(filter(None, command("resume-index-selected", ["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0")))
assert index <= set(paths) and set(old["canonical_paths"]) <= index
command("resume-authored-check", ["git", "diff", "--cached", "--check", "--", *old["canonical_paths"], "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json", original_script, str(Path(__file__).relative_to(ROOT))])
raw = command("resume-staged-objects", ["git", "diff", "--cached", "--raw", "--no-abbrev", "-z"]).split(b"\0")
for offset in range(0, len(raw) - 1, 2):
    header = raw[offset].decode().split(); path = raw[offset + 1].decode()
    assert len(header) == 5 and header[-1] in ("A", "M") and header[1] in ("100644", "100755")
    data = (ROOT / path).read_bytes()
    assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == header[3]
command("resume-commit", ["git", "commit", "-m", "Fix dispatcher admission test isolation and qualify default authority"])
head = command("resume-after-head", ["git", "rev-parse", "HEAD"]).decode().strip()
tree = command("resume-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
assert command("resume-parent", ["git", "rev-parse", "HEAD^"]).decode().strip() == BASE
committed = set(filter(None, command("resume-committed-paths", ["git", "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", "HEAD"]).decode().split("\0")))
assert committed == index
assert not command("resume-index-after", ["git", "diff", "--cached", "--name-only"])
command("resume-push", ["git", "push", "origin", "HEAD:main"])
assert command("resume-remote-after", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
for path, digest in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == digest
save("receipt.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "commit": head, "tree": tree, "parent": BASE, "committed_paths": len(index), "manifest": row(OUT / "manifest-v2.json"), "pushed": True, "force": False, "canonical_paths": old["canonical_paths"], "protected_work_unchanged": PROTECTED, "active_layout_preparation_and_preaccess_excluded": True, "CI_pending": True, "full_ownership_funding_session_provider_native_customer_or_GA_acceptance": False})
print(json.dumps({"commit": head, "tree": tree, "changed_paths": len(index), "pushed": True}))
