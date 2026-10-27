#!/usr/bin/env python3
"""Freeze this independent review without changing the frozen pre-release packet."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
PRE = HERE.parent
VERIFICATION = PRE.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify(base, name, expected):
    seal_path = base / name
    assert sha(seal_path) == expected
    seal = json.loads(seal_path.read_text())
    for row in seal["members"]:
        path = base / row["path"]
        assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], row["path"]
    return {"seal_sha256": expected, "member_count": len(seal["members"]),
            "bytes": sum(row["bytes"] for row in seal["members"])}


def main():
    assert not (HERE / "seal.json").exists(), "review seal must not be replaced"
    pre = verify(PRE, "pre-release-seal.json", "f6770a6b8c69506f5bd70d1fd76b73ab6797e965f5c899be91878497572b3371")
    candidate = verify(VERIFICATION / "swift-guarded-snapshot-export-admission-design", "seal.json",
                       "b60d1ba0790076b35b6df30dd8df407486f89144e6914f40d2d0d55e4e20e1f5")
    receipt = json.loads((HERE / "receipt.json").read_text())
    assert receipt["all_expectations_met"]
    for command in receipt["commands"]:
        folder = HERE / "commands" / command["name"]
        record = folder / "receipt.json"
        assert sha(record) == command["receipt_sha256"]
        data = json.loads(record.read_text())
        for stream in ["stdout", "stderr"]:
            assert sha(folder / stream) == data[stream + "_sha256"]
    assert not list(HERE.glob("lifetime-only-*"))
    assert not list(PRE.rglob("__pycache__"))
    encoder_contract = VERIFICATION / "swift-semantic-adapter-root-review/guarded-snapshot-encoder-component-selection.json"
    dump(HERE / "final-verification.json", {
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pre_release_packet_unchanged": pre, "producer_packet_unchanged": candidate,
        "root_encoder_contract_only": {"path": str(encoder_contract.relative_to(VERIFICATION.parent)), "sha256": sha(encoder_contract)},
        "active_encoder_implementation_read": False,
        "new_scope_or_writer_behavior_accepted": False,
        "complete_floor_or_new_grant_selected": False,
        "findings": ["F1 post-Construction pre-scope failure cleanup", "F2 phase-to-guard shared reborrow contract"],
        "cleanup": receipt["cleanup"],
    })
    rows = [{"path": str(path.relative_to(HERE)), "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in sorted(HERE.rglob("*")) if path.is_file()]
    seal = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "scope": "independent frozen70-member admission proposal review; two design findings, no full behavior acceptance",
            "members": rows, "member_count": len(rows), "bytes": sum(row["bytes"] for row in rows),
            "tree_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    dump(HERE / "seal.json", seal)
    print(json.dumps({key: value for key, value in seal.items() if key != "members"} | {"seal_sha256": sha(HERE / "seal.json")}))


if __name__ == "__main__":
    main()
