"""Owned host-only review runner; never executes producer orchestration."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
UPSTREAM = (
    ("swift-ordered-retention-analyzer-design", "c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8", 67),
    ("swift-ordered-retention-analyzer-review", "da87dd37e0983e212bbaf9658bc3177cb47c146bb13d82ddd2fea948c1966ebc", 212),
    ("swift-ordered-retention-diagnostic-rust", "c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf", 186),
    ("swift-ordered-retention-diagnostic-completion", "2e427447a34357ab4ff70eb220f56754f685a930edf4a89ebc29096fff3b73ba", 222),
    ("swift-ordered-retention-diagnostic-completion-review", "87a6fe21fd5c8f6590992aae8cc826e2502454686cf0d7a8c550acb7965827cc", 158),
)


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        while raw := f.read(65536):
            h.update(raw)
    return h.hexdigest()


def verify(root, name, expected, count):
    seal = root / "verification" / name / "seal.json"
    assert sha(seal) == expected
    rows = json.loads(seal.read_bytes())["members"]
    assert len(rows) == count
    for row in rows:
        p = root / row["path"]
        assert stat.S_ISREG(p.lstat().st_mode)
        assert p.stat().st_size == row["bytes"] and sha(p) == row["sha256"], row["path"]
    return {"seal": str(seal.relative_to(root)), "sha256": expected,
            "members": len(rows), "bytes": sum(row["bytes"] for row in rows)}


def main():
    assert sys.dont_write_bytecode
    run = OWN / "commands" / sys.argv[1]
    run.mkdir(parents=True, exist_ok=False)
    freeze = os.environ.get("FSM_REVIEW_FREEZE", "producer-freeze-1")
    frozen_root = OWN / freeze / "repository"
    producer = frozen_root / "verification/swift-ordered-retention-analyzer-fsm-contract"
    expected = (producer / "seal.sha256").read_text().strip()
    count = len(json.loads((producer / "seal.json").read_bytes())["members"])
    before = [verify(ROOT, *item) for item in UPSTREAM]
    frozen_before = verify(frozen_root, "swift-ordered-retention-analyzer-fsm-contract", expected, count)
    original_before = verify(ROOT, "swift-ordered-retention-analyzer-fsm-contract", expected, count)
    sources = [OWN / p for p in ("oracle.py", "test_oracle.py", "test_frozen_contract.py", "run_review.py")]
    if freeze == "producer-freeze-1":
        sources.append(OWN / "reproduce_freeze1.py")
    source_rows = []
    for source in sources:
        shutil.copyfile(source, run / ("executed-" + source.name))
        source_rows.append({"path": str(source.relative_to(ROOT)), "bytes": source.stat().st_size, "sha256": sha(source)})
    shutil.copyfile(producer / "layout.rs", run / "executed-layout.rs")
    rustc = Path("/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc")
    commands = [
        ("python-version", [sys.executable, "--version"], 0),
        ("git-version", ["git", "--version"], 0),
        ("revision", ["git", "rev-parse", "HEAD"], 0),
        ("independent-oracle", [sys.executable, "-B", str(OWN / "test_oracle.py")], 0),
        ("frozen-producer", [sys.executable, "-B", str(producer / "test_model.py")], 0),
        ("independent-cross-checks", [sys.executable, "-B", str(OWN / "test_frozen_contract.py")], 0),
        ("rustc-version", [str(rustc), "-vV"], 0),
        ("layout-compile", [str(rustc), "--edition=2021", str(run / "executed-layout.rs"), "-o", str(run / "layout-probe")], 0),
        ("layout-execute", [str(run / "layout-probe")], 0),
    ]
    if freeze == "producer-freeze-1":
        commands.append(("contract-findings-reproduction", [sys.executable, "-B", str(OWN / "reproduce_freeze1.py")], 1))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    runs = []
    for name, argv, expected_exit in commands:
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=60)
        out, err = run / (name + ".stdout"), run / (name + ".stderr")
        out.write_bytes(result.stdout); err.write_bytes(result.stderr)
        runs.append({"name": name, "argv": argv, "cwd": str(ROOT),
                     "exit": result.returncode, "expected_exit": expected_exit,
                     "stdout_sha256": sha(out), "stderr_sha256": sha(err)})
    after = [verify(ROOT, *item) for item in UPSTREAM]
    frozen_after = verify(frozen_root, "swift-ordered-retention-analyzer-fsm-contract", expected, count)
    original_after = verify(ROOT, "swift-ordered-retention-analyzer-fsm-contract", expected, count)
    assert before == after and frozen_before == frozen_after and original_before == original_after
    assert all(sha(ROOT / r["path"]) == r["sha256"] for r in source_rows)
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.UTC).isoformat(),
               "freeze": freeze, "upstream_before": before, "upstream_after": after,
               "frozen_before": frozen_before, "frozen_after": frozen_after,
               "original_before": original_before, "original_after": original_after,
               "source_rows": source_rows,
               "source_tree_sha256": hashlib.sha256(json.dumps(source_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
               "python": {"path": sys.executable, "sha256": sha(Path(sys.executable).resolve())},
               "rustc": {"path": str(rustc), "sha256": sha(rustc)},
               "layout_binary": {"path": str((run / "layout-probe").relative_to(ROOT)), "sha256": sha(run / "layout-probe")},
               "commands": runs,
               "expected_exits_match": all(r["exit"] == r["expected_exit"] for r in runs),
               "scope": "Finite contract model, standalone host layout and independent oracle only",
               "cleanup": {"synchronous_children_reaped": True, "scratch_created": False,
                           "bytecode_created": False, "native_capture_target_or_unrelated_processes_started_or_queried": False},
               "storedPrefixValidated": False, "fullReplayAccepted": False,
               "semantic_counters_valid": False, "Rust_implementation_executed": False}
    (run / "result.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"run": run.name, "expected_exits_match": receipt["expected_exits_match"],
                      "upstream_members_unchanged": sum(r["members"] for r in before),
                      "frozen_members": count,
                      "source_tree_sha256": receipt["source_tree_sha256"],
                      "commands": [{"name": r["name"], "exit": r["exit"]} for r in runs]}, sort_keys=True))
    return 0 if receipt["expected_exits_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
