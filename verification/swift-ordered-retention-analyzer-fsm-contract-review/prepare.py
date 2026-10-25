"""Owned finite pre-access runner. Does not open the producer FSM packet."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    p = ROOT / path
    if not stat.S_ISREG(p.lstat().st_mode):
        raise ValueError(f"not regular: {path}")
    return p.read_bytes()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify_seal(prefix, expected, count):
    raw = regular(prefix + "/seal.json")
    if sha(raw) != expected:
        raise ValueError("seal hash " + prefix)
    doc = json.loads(raw)
    if len(doc["members"]) != count:
        raise ValueError("seal member count")
    paths = set()
    for row in doc["members"]:
        path = row["path"]
        if path in paths or Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("bad seal member")
        paths.add(path)
        content = regular(path)
        if len(content) != row["bytes"] or sha(content) != row["sha256"]:
            raise ValueError("seal member mismatch " + path)
    return {"seal_sha256": expected, "members": count,
            "bytes": sum(r["bytes"] for r in doc["members"]),
            "manifest_sha256": sha(json.dumps(doc["members"], sort_keys=True,
                                               separators=(",", ":")).encode())}


def main():
    if (OWN / "preparation-seal.json").exists():
        raise RuntimeError("preparation already frozen")
    at = datetime.datetime.now(datetime.UTC).isoformat()
    commands = OWN / "commands" / "preparation"
    commands.mkdir(parents=True, exist_ok=True)
    inputs = OWN / "inputs"
    inputs.mkdir(exist_ok=True)
    accepted = {}
    for name, expected, count in (
        ("swift-ordered-retention-analyzer-design", "c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8", 67),
        ("swift-ordered-retention-analyzer-review", "da87dd37e0983e212bbaf9658bc3177cb47c146bb13d82ddd2fea948c1966ebc", 212),
    ):
        accepted[name] = verify_seal("verification/" + name, expected, count)
    paths = ["AGENTS.md", "mixer-product-plan.md",
             "docs/swift-ordered-retention-analyzer.md",
             "docs/swift-ordered-retention-analyzer-review.md",
             "docs/swift-ordered-retention-analyzer-library.md",
             "verification/swift-ordered-retention-analyzer-root-review/acceptance.json",
             "verification/swift-ordered-retention-analyzer-library-root-review/acceptance.json",
             "verification/swift-ordered-retention-analyzer-design/interface_schema.py",
             "verification/swift-ordered-retention-analyzer-library/src/analyzer.rs",
             "verification/swift-ordered-retention-analyzer-library/logical-inventory.md"]
    authority = "verification/swift-ordered-retention-analyzer-design/inputs/"
    copied = ["candidate__src__experimental__cache__borrowed.rs",
              "candidate__src__experimental_swift_reactor__cache.rs",
              "candidate__src__experimental_swift_reactor__control.rs",
              "verification__swift-ordered-retention-diagnostic-rust__observer.rs",
              "verification__swift-ordered-retention-diagnostic-rust__writer.rs",
              "verification__swift-ordered-retention-diagnostic-rust__source-code-table.json"]
    paths += [authority + p for p in copied]
    for prefix in ("verification/swift-ordered-retention-analyzer-design",
                   "verification/swift-ordered-retention-analyzer-review"):
        paths += [prefix + "/seal.json", prefix + "/seal.sha256"]
    snapshots = []
    for p in paths:
        content = regular(p)
        name = p.replace("/", "__")
        (inputs / name).write_bytes(content)
        snapshots.append({"path": p, "snapshot": str((inputs / name).relative_to(ROOT)),
                          "bytes": len(content), "sha256": sha(content)})
    joins = []
    for name in copied[3:]:
        original = name.replace("__", "/")
        content = regular(original)
        if content != regular(authority + name):
            raise ValueError("upstream authority mismatch " + original)
        joins.append({"path": original, "sha256": sha(content), "bytes": len(content)})
    archive = "verification/swift-ordered-retention-diagnostic-completion/candidate-source.tar.gz"
    archive_raw = regular(archive)
    if sha(archive_raw) != "8006754e71929b81b86b645f766cdcc539a0b8a131ba8d62309f6874446265dc":
        raise ValueError("candidate archive digest")
    wanted = {p.removeprefix("candidate__").replace("__", "/"): p for p in copied[:3]}
    archive_joins = []
    with tarfile.open(ROOT / archive, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            if member.name in wanted:
                if not member.isfile():
                    raise ValueError("nonregular candidate")
                content = tar.extractfile(member).read()
                if content != regular(authority + wanted[member.name]):
                    raise ValueError("candidate source mismatch")
                archive_joins.append({"path": member.name, "bytes": len(content), "sha256": sha(content)})
    if len(archive_joins) != 3:
        raise ValueError("missing candidate matches")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    invocations = [[sys.executable, "--version"], ["git", "rev-parse", "HEAD"],
                   [sys.executable, str(OWN / "test_oracle.py")]]
    runs = []
    for i, argv in enumerate(invocations):
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=60)
        (commands / f"{i}.stdout").write_bytes(result.stdout)
        (commands / f"{i}.stderr").write_bytes(result.stderr)
        runs.append({"argv": argv, "cwd": str(ROOT), "exit": result.returncode,
                     "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr)})
        if result.returncode:
            write_json(commands / "failure.json", runs)
            raise RuntimeError(f"command failed {argv}")
    sys.path.insert(0, str(OWN))
    from test_oracle import matrix
    write_json(OWN / "preaccess-vectors.json", matrix())
    write_json(OWN / "preparation-preflight.json", {
        "schema": 1, "at": at, "completed_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "python": sys.version, "python_executable": sys.executable,
        "python_sha256": sha(Path(sys.executable).resolve().read_bytes()),
        "revision": (commands / "1.stdout").read_text().strip(),
        "accepted_closures": accepted, "snapshots": snapshots,
        "original_wire_source_matches": joins,
        "candidate_archive": {"path": archive, "sha256": sha(archive_raw),
                              "members": len(members), "selected_matches": archive_joins,
                              "restored_imported_or_executed": False},
        "commands": runs, "independent_methods": 18, "baseline_pairs": 154,
        "producer_fsm_packet_accessed": False,
        "source_tree_sha256": sha(json.dumps(snapshots, sort_keys=True, separators=(",", ":")).encode()),
        "native_capture_target_or_unrelated_processes_started_or_queried": False,
        "cleanup": "No scratch or native instances; synchronous host Python child reaped; no pycache generated",
    })
    members = []
    for p in sorted(OWN.rglob("*")):
        if p.is_file():
            content = p.read_bytes()
            members.append({"path": str(p.relative_to(ROOT)), "bytes": len(content), "sha256": sha(content)})
    write_json(OWN / "preparation-seal.json", {"schema": 1, "at": datetime.datetime.now(datetime.UTC).isoformat(), "members": members})
    seal = (OWN / "preparation-seal.json").read_bytes()
    (OWN / "preparation-seal.sha256").write_text(sha(seal) + "\n")
    print(json.dumps({"preparation_seal_sha256": sha(seal), "members": len(members),
                      "methods": 18, "pairs": 154, "producer_access": False}, sort_keys=True))


if __name__ == "__main__":
    main()
