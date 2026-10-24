"""Read-only checks for selected private contracts and the hosted CI receipt."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]


def verify(path):
    receipt = json.loads((ROOT / path).read_text())
    for name, expected in receipt["bindings"].items():
        file = ROOT / name
        assert file.is_file() and not file.is_symlink(), name
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if isinstance(expected, dict):
            assert digest == expected["sha256"] and file.stat().st_size == expected["bytes"], name
        else:
            assert digest == expected, name
    return receipt


android = verify("verification/android-authored-toggle-root-review/selection.json")
transport = verify("verification/stripe-webhook-transport-root-review/selection.json")
ci = verify("verification/github-ci-8c634c49-phoenix/receipt.json")
assert android["sourceInputsVerified"] == 44 and not android["productAccepted"]
assert not android["nativeRunAuthorized"] and not android["gaAccepted"]
assert transport["sourceInputsVerified"] == 71 and transport["producerFilesVerified"] == 150
assert not transport["productionAdmissionAccepted"] and not transport["liveChangesAuthorized"]
assert not transport["privacyQualified"] and not transport["gaAccepted"]
assert ci["testResult"] == "Result: 142 passed, 2 skipped" and ci["sourceInputs"] == 71
graph = json.loads((ROOT / "work-graph.json").read_text())
gates = json.loads((ROOT / "gates/ga.json").read_text())
assert {x["id"] for x in graph["packages"]} == {f"W{i:02d}" for i in range(1, 19)}
assert {x["id"] for x in gates["gates"]} == {f"G{i:02d}" for i in range(1, 39)}
assert all(x["status"] != "verified" for x in gates["gates"])
print(json.dumps({"status": "passed", "androidSelectionBindings": len(android["bindings"]),
                  "transportSelectionBindings": len(transport["bindings"]),
                  "phoenixCIBindings": len(ci["bindings"]), "packages": 18, "gaGates": 38,
                  "scope": "Immutable contract/CI bindings and full-scope tracker checks only; no product or native qualification."}))
