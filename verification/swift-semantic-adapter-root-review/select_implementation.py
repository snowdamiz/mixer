"""Verify sealed independent preparation, then select bounded fixture-only Rust work."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    require(path.is_file() and not path.is_symlink(), "Nonregular file")
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


seal = ROOT / "verification/swift-cache-state-independent-review/preaccess/seal.json"
expected_sha = "1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c"
require(identity(seal)["sha256"] == expected_sha, "Seal differs")
data = json.loads(seal.read_bytes())
seen = set()
total = 0
for row in data["members"]:
    relative = Path(row["path"])
    require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe path")
    require(identity(ROOT / relative) == {key: row[key] for key in ("bytes", "sha256")}, "Member differs: " + row["path"])
    require(row["path"] not in seen, "Duplicate member")
    seen.add(row["path"])
    total += row["bytes"]
require(len(seen) == data["member_count"] == 173 and total == data["member_bytes"] == 27268876, "Totals differ")
prefix = seal.parent.relative_to(ROOT).as_posix() + "/"
actual = {p.relative_to(ROOT).as_posix() for p in seal.parent.rglob("*") if p.is_file()}
expected = {name for name in seen | set(data["excluded"]) if name.startswith(prefix)}
require(actual == expected, "Packet closure differs")
for name in data["excluded"]:
    require((ROOT / name).is_file(), "Missing excluded metadata")
ready = json.loads((ROOT / "verification/swift-cache-state-independent-review/preaccess-ready.json").read_bytes())
require(ready["seal_sha256"] == expected_sha and ready["members"] == 173, "Readiness differs")
receipt = json.loads(seal.with_name("final-receipt.json").read_bytes())
require(not receipt["new_producer_source_accessed"] and receipt["actual_public_File_semantic_executions"] == 0, "Scope differs")
for mode in ("normal", "optimized"):
    result = receipt["control_evidence"][mode]
    require(result["methods"] == 14 and result["checks"] == 29006 and result["failures"] == result["errors"] == 0, "Controls differ")
require(identity(ROOT / "verification/swift-semantic-adapter-root-review/combined-contract-acceptance.json")["sha256"] ==
        "aac275052af88c802b0594c2d47318898d383b90f20d99a3914a4080c1a76dcc", "Accepted source contract differs")
require(not (ROOT / "verification/swift-cache-state-implementation").exists(), "Producer source already exists")
for name, digest in [("analyzer.rs", "1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b"),
                     ("envelope.rs", "2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef")]:
    require(identity(ROOT / "verification/swift-envelope-ci-pack/source/library" / name)["sha256"] == digest, "Accepted child source differs")

selection = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
    "script_sha256": identity(Path(__file__))["sha256"],
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "independent-preaccess-verified-fixture-cache-state-Rust-implementation-selected",
    "source_contract_acceptance_sha256": "aac275052af88c802b0594c2d47318898d383b90f20d99a3914a4080c1a76dcc",
    "preaccess_seal": seal.relative_to(ROOT).as_posix(), "preaccess_sha256": expected_sha,
    "members": 173, "bytes": total, "review_plan": "docs/swift-cache-state-implementation-review-plan.md",
    "review_plan_sha256": "7bc49b011445d080a2f3d4ba0a493f02a11d905ccdd3edca7cb27492d52afebd",
    "reviewer_methods_per_mode": 14, "reviewer_checks_per_mode": 29006,
    "public_fixture_designs": 39, "word_mutations": 3461, "stage_transitions": 220,
    "terminal_cases": 2670, "actual_source_obligations": 35,
    "actual_public_File_semantic_executions": 0, "new_Rust_product_tests": 0,
    "three_paid_domain_exclusions_runtime_passes": 0,
    "owned_paths": ["verification/swift-cache-state-implementation/**", "docs/swift-cache-state-implementation.md"],
    "selected_work": "Additive standalone fixture-only safe File cache-state implementation and owned host tests; complete source/debit/caller/move/lifetime/cleanup proof within the accepted unchanged bounds; freeze an immutable candidate before independent access.",
    "immutable_inputs": ["verification/swift-envelope-ci-pack/**", "verification/swift-cache-state-independent-review/preaccess/**", "all six accepted source-contract packets"],
    "provisional_bounds": {"semantic_record": 7680, "inherited_record": 471, "combined_record": 8151,
        "preflight": 8192, "setup": 512, "finish": 256, "terminal_guard": 128,
        "role_union": 29344, "reserved_transients": 41984, "global_named_transient_cap": 65536,
        "candidate": 2048, "predicted_aggregate": 488, "complete_Result": 512},
    "predicate_overlap": "Named single-defect reasons fixed; legitimate overlapping reason sets require deterministic actual-source order explanation and independent review. T00-T15 precedence unchanged.",
    "forbidden": ["Cap increases, spare-credit transfers or optimizer-only bounds", "Old API/ABI/report behavior changes",
        "Public raw records/state seeds/authority booleans/FD adoption", "Current live VM or target integration",
        "Frozen hosted inspector/authority-driver/rejected WorkerV2/broad hosted harness/callback access",
        "Native/capture/UI/simulator/emulator/phone execution or process discovery", "Root metadata/CI/git edits or unrelated lanes"],
    "prior_preparation_error": "Initial inline custody check included excluded readiness metadata outside the sealed subdirectory in its subdirectory closure set; all member hashes passed, but no admission was written. This verifier scopes exclusions to the actual subdirectory.",
    "implementation_selected": True, "implementation_accepted": False,
    "fullReplayAccepted": False, "storedPrefixValidated": False, "semanticMetricsValid": False,
    "realBindingVerified": False, "native_runtime_or_capture_started": False, "GA_qualified": False,
}
destination = OUT / "implementation-selection.json"
destination.write_text(json.dumps(selection, indent=2) + "\n")
print(json.dumps({"path": destination.relative_to(ROOT).as_posix(), **identity(destination)}))
