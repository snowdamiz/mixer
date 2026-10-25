#!/usr/bin/env python3
"""Read-only packet audit; no product imports, runtime or resource discovery."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
SELECTED = BASE / "attempts/20261025T204044.344416Z-pg16-ae7369"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((SELECTED / "receipt.json").read_text())
    checks = {}
    for path, expected in receipt["selected_sources"].items():
        checks["source_archive:" + path] = sha(SELECTED / "inputs" / path) == expected
        checks["current_source:" + path] = sha(ROOT / path) == expected
    for path, expected in receipt["review_sources"].items():
        checks["review_archive:" + path] = sha(SELECTED / "inputs" / path) == expected
    for path, expected in receipt["dependencies"].items():
        checks["dependency:" + path] = sha(ROOT / path) == expected
    for path, expected in receipt["outputs"].items():
        checks["output:" + path] = sha(SELECTED / path) == expected
    checks["selected_receipt"] = sha(SELECTED / "receipt.json") == "8fb5830f4bb7251e5bc255d2dc42563b99ffce91da3953c3e9286155cdc4efcf"
    checks["selected_invariants"] = len(receipt["checks"]) == 34 and all(row["invariant_passed"] for row in receipt["checks"])
    checks["strict_clean_runtime"] = receipt["clean_runtime_output"] is True and (SELECTED / "independent-controls.stderr").read_bytes() == b""
    checks["owned_cleanup"] = all(receipt["cleanup"].values()) and all(receipt["beam_cleanup"].values())
    fences = json.loads((SELECTED / "trace-fences.json").read_text())
    checks["two_precise_publication_fences"] = len(fences) == 2 and all(row == {"schedulers_online": 1, "status_returned_before_action": False, "observed_trace_barrier": True} for row in fences)
    dispositions = json.loads((BASE / "attempt-dispositions.json").read_text())["attempts"]
    checks["both_attempts_classified"] = len(dispositions) == 2
    for row in dispositions:
        checks["attempt_receipt:" + row["attempt"]] = sha(ROOT / row["attempt"] / "receipt.json") == row["receipt_sha256"]
    checks["diagnostic_not_selected"] = dispositions[0]["disposition"] == "diagnostic_only_not_accepted"
    checks["clean_selected"] = dispositions[1]["disposition"] == "selected_clean_independent_pass"
    result = {"scope": "Read-only source/archive/dependency/output/disposition audit only", "checks": checks, "all_passed": all(checks.values()), "assertions": len(checks)}
    (BASE / "audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"assertions": len(checks), "all_passed": result["all_passed"]}))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
