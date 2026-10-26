"""One-shot custody/disposition record; no product imports or execution."""
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("g6-review-admission.json")
assert not OUT.exists(), "preserve the existing admission"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(relative, expected):
    path = ROOT / relative
    assert digest(path) == expected, relative
    data = json.loads(path.read_text())
    seen = set()
    size = 0
    for member in data["members"]:
        rel = member["path"]
        assert rel not in seen and not Path(rel).is_absolute()
        seen.add(rel)
        source = ROOT / rel
        assert source.is_file() and not source.is_symlink(), rel
        assert source.stat().st_size == member["bytes"], rel
        assert digest(source) == member["sha256"], rel
        size += member["bytes"]
    assert len(seen) == data["member_count"]
    assert size == data["member_bytes"]
    return {"path": relative, "sha256": expected, "members": len(seen), "bytes": size}


audit = verify(
    "verification/swift-cache-state-g6-accounting/seal.json",
    "56531ea3ebaf7e4fcd3eb8df2afddc7b2aa17dda2121156c4238659c6bdd1cbf",
)
proposal = verify(
    "verification/swift-cache-state-g6-accounting/proposal-clear128/seal.json",
    "021f726ae15a9a3046e149ccde61294be045956f43b1ddd431e5b9d98f7c8733",
)
boundaries = {
    "G128": "Retain one-shot absorbing zero-debit guard reply, received and caller terminal installation ownership; no reassignment to G7 selected.",
    "G7": "Paid ordinary semantic reply transfers and applicable paid-record terminal work remain G7; exact source mapping still required.",
    "G6": "Actual post-loan cleanup remains G6 under combined prepayment; pre-loan guard paths leave scratch untouched. Staged prior-pin ld and its checked staging calculation belong to G6.",
    "unresolved": "Independent review must distinguish cleanup-fault poison effects and remove every cross-group overlap exactly once; no complete ledger is accepted.",
}
record = {
    "schema": 1,
    "at": datetime.now(timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())],
    "python": sys.version,
    "platform": platform.platform(),
    "head_context_only": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "audit": audit,
    "proposal": proposal,
    "status": "custody verified; independent source-only review active; producer guard-reply ownership disputed",
    "conditional_core": {"payload_copy_groups": 329, "clear_scalar_operations": 5376, "globally_pooled_blocks": 336, "sum": 665},
    "core_qualification": "Depends on explicit component grammar; not a complete upper bound, unconditional cap overrun, or runtime measurement.",
    "boundary_disposition": boundaries,
    "proposal_effect": {"clear_bytes": 2048, "literal_stores": 16, "bytes_per_store": 128, "additional_initializer_and_binding_peak_bytes": 240, "additional_steady_local_bytes": 120},
    "caps_changed": False,
    "proposal_implementation_selected": False,
    "full_G6_bound_accepted": False,
    "whole_role_union_accepted": False,
    "product_or_compiler_execution": False,
    "native_UI_capture_or_process_inventory": False,
    "GA_qualified": False,
}
OUT.write_text(json.dumps(record, indent=2) + "\n")
followup = {
    "status": record["status"],
    "root_admission": str(OUT.relative_to(ROOT)),
    "root_admission_sha256": digest(OUT),
    "audit": audit,
    "proposal": proposal,
    "conditional_core": record["conditional_core"],
    "core_qualification": record["core_qualification"],
    "boundary_disposition": boundaries,
    "proposal_implementation_selected": False,
    "full_G6_bound_accepted": False,
    "whole_role_union_accepted": False,
}
for name, key in (("work-graph.json", "packages"), ("gates/ga.json", "gates")):
    path = ROOT / name
    data = json.loads(path.read_text())
    hits = 0
    for item in data[key]:
        if "fixtureCacheStateContractCandidate" in item:
            item["fixtureCacheStateContractCandidate"]["source_accounting_supplement"]["G6_followup"] = followup
            hits += 1
    assert hits == 1
    path.write_text(json.dumps(data, indent=2) + "\n")
print(json.dumps({"record": str(OUT.relative_to(ROOT)), "sha256": digest(OUT), "audit": audit, "proposal": proposal}))
