"""Read-only frozen packet/member check; no subprocess or imports of runners."""
from pathlib import Path
import hashlib
import json
import sys


def main():
    if sys.argv[1:] != ["--read-only"]:
        raise SystemExit("--read-only required")
    here = Path(__file__).resolve().parent
    seal = json.loads((here / "seal.json").read_bytes())
    actual = []
    for member in seal["members"]:
        data = (here / member["path"]).read_bytes()
        found = {"path": member["path"], "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        if found != member:
            raise SystemExit("member mismatch: " + member["path"])
        actual.append(found)
    encoded = json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(encoded).hexdigest() == seal["tree_sha256"]
    assert len(actual) == seal["member_count"]
    assert sum(x["bytes"] for x in actual) == seal["member_bytes"]
    print(json.dumps({"status": "frozen-contract-members-rehashed", "members": len(actual),
                      "bytes": seal["member_bytes"], "compiler_or_native_execution": False,
                      "root_policy_or_funding_or_operational_selection": False}, sort_keys=True))


if __name__ == "__main__":
    main()
