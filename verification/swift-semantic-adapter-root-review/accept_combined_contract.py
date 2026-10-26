"""Verify the six immutable packets before accepting their combined source contract."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKETS = [
    ("verification/swift-semantic-adapter-prerequisite/seal.json", "d145cda8cdde0915493f5c75102ae0dc11adb577891b1b773322b5c4d0f32cba", ".", "member_bytes"),
    ("verification/swift-semantic-adapter-contract-review/preaccess/seal.json", "7ae911b982f2bf96f596969c2c282bd5bbdd7302033a6d1404278f1df23d9ae9", "verification/swift-semantic-adapter-contract-review/preaccess", "total_bytes"),
    ("verification/swift-semantic-adapter-contract-review/review-1/seal.json", "d44b2edd19961ebeda7e197f549433e7a0d7f0630ce7d501e5465044340c6c02", "verification/swift-semantic-adapter-contract-review/review-1", "member_bytes"),
    ("verification/swift-semantic-adapter-terminal-correction/seal.json", "efa9288096a692780e195ac519ffb7ed0be1280a974e830d80fc9932d194aef7", ".", "member_bytes"),
    ("verification/swift-semantic-adapter-terminal-review/preaccess/seal.json", "b71097292535a76631d787121c60e315f91343ed6da8c71fec9303cf9328e681", "verification/swift-semantic-adapter-terminal-review/preaccess", "member_bytes"),
    ("verification/swift-semantic-adapter-terminal-review/review-1/seal.json", "87428e8a867993a32b72579a7c8b5c19df5ae2e5da365707ab22e4cd2b4167d4", "verification/swift-semantic-adapter-terminal-review/review-1", "member_bytes"),
]


def require(value, message):
    if not value:
        raise ValueError(message)


seen = {}
packets = []
for path, want, base, count_key in PACKETS:
    seal = ROOT / path
    require(hashlib.sha256(seal.read_bytes()).hexdigest() == want, "Seal differs: " + path)
    data = json.loads(seal.read_bytes())
    total = 0
    local_paths = set()
    for row in data["members"]:
        relative = Path(row["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe member")
        member = ROOT / base / relative
        require(member.is_file() and not member.is_symlink(), "Nonregular member")
        content = member.read_bytes()
        require(len(content) == row["bytes"] and hashlib.sha256(content).hexdigest() == row["sha256"],
                "Member differs: " + row["path"])
        require(row["path"] not in local_paths, "Duplicate member")
        local_paths.add(row["path"])
        key = member.relative_to(ROOT).as_posix()
        require(key not in seen or seen[key] == row["bytes"], "Overlapping member differs")
        seen[key] = row["bytes"]
        total += len(content)
    require(len(local_paths) == data["member_count"] and total == data[count_key], "Incorrect member totals")
    if base != ".":
        actual = {p.relative_to(seal.parent).as_posix() for p in seal.parent.rglob("*") if p.is_file()}
        require(actual == local_paths | set(data["excluded"]), "Unexpected packet paths")
    packets.append({"seal": path, "sha256": want, "members": len(local_paths), "bytes": total})

document = ROOT / "docs/swift-semantic-adapter-terminal-review.md"
document_sha = hashlib.sha256(document.read_bytes()).hexdigest()
require(document_sha == "3ce15cb0c5a9c3d077207589462ff3f8cc9eb866a5adc1776c1174d0e31b727c", "Review document differs")
receipt = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "status": "accepted-combined-fixture-cache-state-source-contract", "packets": packets,
    "unique_members": len(seen), "unique_bytes": sum(seen.values()),
    "review_document": document.relative_to(ROOT).as_posix(), "review_document_sha256": document_sha,
    "R1_closed": True, "independent_methods_per_mode": 8, "independent_checks_per_mode": 29944,
    "terminal_rows": 16, "observation_fields": 32, "stages": 11, "accepted_child_branches": 13,
    "source_model_cases": 19635, "terminal_combinations": 3360, "preaccess_scenarios": 114,
    "finite_preaccess_cases": 111, "private_paid_domain_exclusions_requiring_implementation_proof": 3,
    "original_constraints_retained": True,
    "provisional_bounds": {"semantic_record": 7680, "combined_record": 8151, "setup": 512,
        "finish": 256, "terminal_guard": 128, "role_union_bytes": 29344, "predicted_aggregate_bytes": 488},
    "Rust_product_tests_run": 0, "source_contract_accepted": True, "implementation_selected": False,
    "next_selected_work": "Seal independent raw-record/profile/context actual-File fixtures, sorted-victim oracle and complete source/work/move/lifetime obligations before producer Rust source access.",
    "pending": ["Actual Rust implementation within unchanged bounds", "Complete source/debit/move/caller/lifetime and arena/candidate cleanup proof",
        "Fresh layout/API/framing/envelope regression and independent actual-File execution", "Real adapters/custody/target/live VM and full product gates"],
    "prior_root_receipt_preparation_error": "Initial inline verification assumed member_bytes for original preaccess, whose declared total key is total_bytes; no acceptance receipt was written.",
    "fullReplayAccepted": False, "storedPrefixValidated": False, "semanticMetricsValid": False,
    "native_runtime_or_capture_started": False, "GA_qualified": False,
}
destination = Path(__file__).with_name("combined-contract-acceptance.json")
destination.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"receipt": destination.relative_to(ROOT).as_posix(),
    "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "members": len(seen), "bytes": sum(seen.values())}))
