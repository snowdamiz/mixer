"""Record a source-bound private implementation direction; no HTTP startup."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRODUCER = REPO / "verification/stripe-raw-body-contract"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (HERE / "selection.json").exists(), "selection is immutable"
    bindings = json.loads((PRODUCER / "seal.json").read_text())
    observed = set()
    for path in PRODUCER.rglob("*"):
        assert not path.is_symlink(), path
        if path.is_file() and path != PRODUCER / "seal.json":
            observed.add(str(path.relative_to(REPO)))
    observed.add("docs/stripe-raw-body-contract.md")
    assert observed == set(bindings)
    for name, expected in bindings.items():
        path = REPO / name
        assert path.is_file() and path.stat().st_size == expected["bytes"]
        assert sha(path) == expected["sha256"], name
    inputs = json.loads((PRODUCER / "source-inputs.json").read_text())
    for name, expected in inputs.items():
        assert sha(PRODUCER / "inputs" / name) == expected
        assert sha(REPO / name) == expected, name
    accepted = json.loads((PRODUCER / "accepted-hosted-inputs.json").read_text())
    current = {name: sha(REPO / name) for name in accepted["sourceInputs"]}
    assert current == accepted["sourceInputs"] and len(current) == 69
    digest = hashlib.sha256(json.dumps(current, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == accepted["sourceDigest"]
    beam_inputs = json.loads((PRODUCER / "beam-inputs.json").read_text())
    for name, expected in beam_inputs.items():
        assert sha(REPO / name) == expected, name
    commands = []
    producer_commands = json.loads((PRODUCER / "receipt.json").read_text())["commands"]
    for index, recorded in enumerate(producer_commands):
        result = subprocess.run(recorded["command"], cwd=REPO, capture_output=True, text=True, timeout=30)
        output = HERE / f"replay-{index}.log"
        output.write_text(result.stdout + result.stderr)
        commands.append({"command": recorded["command"], "cwd": str(REPO), "exitCode": result.returncode,
                         "output": str(output.relative_to(REPO)), "outputSHA256": sha(output)})
        assert result.returncode == 0, output
    assert "Result: 9 passed\n" in (HERE / "replay-2.log").read_text()
    for name, expected in beam_inputs.items():
        assert sha(REPO / name) == expected
    evidence = {name: value["sha256"] for name, value in bindings.items()}
    evidence[str((PRODUCER / "seal.json").relative_to(REPO))] = sha(PRODUCER / "seal.json")
    for path in [p for p in HERE.rglob("*") if p.is_file()] + [REPO / "docs/stripe-raw-body-direction.md"]:
        evidence[str(path.relative_to(REPO))] = sha(path)
    receipt = {"schema": 1, "observedUTC": datetime.now(timezone.utc).isoformat(),
               "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=REPO).strip(),
               "status": "selected-normal-framing-private-capture-implementation",
               "profile": 1, "producerFiles": len(bindings), "frozenInputs": len(inputs),
               "sourceDigest": digest, "sourceInputs": current, "beamInputs": beam_inputs,
               "commands": commands, "dependencyAPIProbeTests": 9, "realHTTPTests": 0,
               "liveSourceChanged": False, "servicesStarted": False, "nativeStarted": False,
               "publicAdmissionAccepted": False, "g23Accepted": False,
               "pending": ["capture implementation and independent review", "all thirteen HTTP/component/ingress evidence rows",
                           "endpoint-owned logging and transport cancellation", "endpoint/account/mode ownership",
                           "durable inbox and atomic Oban enqueue", "Stripe test-mode reconciliation", "usage ledger", "G23"],
               "bindings": evidence}
    (HERE / "selection.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"selectedProfile": 1, "bindings": len(evidence), "sourceInputs": len(current),
                      "dependencyAPIProbeTests": 9, "realHTTPTests": 0}))


if __name__ == "__main__":
    main()
