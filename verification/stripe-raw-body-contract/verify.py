"""Verify this proposal's nested evidence seal without mutating the workspace."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    seal = json.loads((HERE / "seal.json").read_text())
    actual_files = {str(p.relative_to(REPO)) for p in HERE.rglob("*") if p.is_file() and p.name != "seal.json"}
    actual_files.add("docs/stripe-raw-body-contract.md")
    assert set(seal) == actual_files, "unsealed or missing files"
    for name, expected in seal.items():
        path = REPO / name
        assert path.stat().st_size == expected["bytes"] and sha(path) == expected["sha256"], name
    receipt = json.loads((HERE / "receipt.json").read_text())
    assert receipt["status"] == "contract-proposal-root-selection-pending"
    assert receipt["validation"]["realHTTPTests"] == 0
    assert all(row["status"] == "pending" for row in json.loads((HERE / "test-matrix.json").read_text())["rows"])
    for name, expected in json.loads((HERE / "source-inputs.json").read_text()).items():
        assert sha(HERE / "inputs" / name) == expected, name
    accepted = json.loads((HERE / "accepted-hosted-inputs.json").read_text())
    assert hashlib.sha256(json.dumps(accepted["sourceInputs"], sort_keys=True, separators=(",", ":")).encode()).hexdigest() == accepted["sourceDigest"]
    print(f"PASS: {len(seal)} exact evidence bindings; API observations only; root selection and all real HTTP rows pending")


if __name__ == "__main__":
    main()
