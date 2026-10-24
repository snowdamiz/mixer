"""Record root's private implementation direction after frozen packet checks."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PACKET = ROOT / "verification/stripe-webhook-transport-contract"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = HERE / "selection.json"
    assert not target.exists(), "immutable selection already recorded"
    seal_path = PACKET / "seal.json"
    assert digest(seal_path) == "2ade7904589112ca5329856952eb1653620e996b4f780c30f42ffbfa95ed9847"
    seal = json.loads(seal_path.read_text())
    actual = {str(p.relative_to(ROOT)) for p in PACKET.rglob("*")
              if p.is_file() and p != seal_path}
    actual.add("docs/stripe-webhook-transport-contract.md")
    assert actual == set(seal["files"])
    bindings = {}
    for name, item in seal["files"].items():
        path = ROOT / name
        assert digest(path) == item["sha256"] and path.stat().st_size == item["bytes"]
        bindings[name] = item["sha256"]
    commands = []
    for argv, log in [
        ([sys.executable, "-B", str(PACKET / "verify.py")], "producer-replay.log"),
        ([sys.executable, "-B", "verification/stripe-raw-body-integration/verify.py", "--live"], "integrated-capture-replay.log"),
        ([sys.executable, "--version"], "python-version.log"),
    ]:
        completed = subprocess.run(argv, cwd=ROOT, capture_output=True)
        output = HERE / log
        output.write_bytes(completed.stdout + completed.stderr)
        commands.append({"argv": argv, "exitCode": completed.returncode,
                         "output": str(output.relative_to(ROOT)), "sha256": digest(output)})
        assert completed.returncode == 0, log
    accepted_path = ROOT / "verification/stripe-raw-body-integration/acceptance.json"
    accepted = json.loads(accepted_path.read_text())
    for name, expected in accepted["sourceInputs"].items():
        assert digest(ROOT / name) == expected, name
        bindings[name] = expected
    for path in [seal_path, accepted_path, Path(__file__),
                 ROOT / "docs/stripe-webhook-transport-direction.md"]:
        bindings[str(path.relative_to(ROOT))] = digest(path)
    for command in commands:
        bindings[command["output"]] = command["sha256"]
    receipt = {
        "schema": 1,
        "status": "root-selected-private-transport-implementation",
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "sourceDigest": accepted["sourceDigest"],
        "sourceInputsVerified": len(accepted["sourceInputs"]),
        "producerFilesVerified": len(seal["files"]),
        "pythonVersion": sys.version,
        "command": [sys.executable, "-B", str(Path(__file__))],
        "commands": commands,
        "bindings": dict(sorted(bindings.items())),
        "selectedDirection": "docs/stripe-webhook-transport-direction.md",
        "selectedContract": "docs/stripe-webhook-transport-contract.md",
        "rootDecisions": [
            "Dedicated BEAM role/listener with complete owned sink inventory; private isolated implementation first.",
            "Select all proposed fixed connection/header/frame/stage/outer-lifetime constants and normal H1/H2 framing.",
            "Independent whole-connection cancellation, original-owner reads, monotonic one-use permit and observed disposal.",
            "New allowlisted events and per-handler filtering cover every configured sink, including the private process default handler.",
            "Trusted bootstrap and controlled sink changes only; drift detection cannot undo events delivered to privileged raw subscribers.",
            "Private adapter trailer discard semantics retained; public trailer policy and OS/container limits remain unselected."
        ],
        "implementationOwnership": ["docs/stripe-webhook-transport-implementation.md", "verification/stripe-webhook-transport/**", "explicitly owned temporary source/build directories"],
        "liveChangesAuthorized": False,
        "publicListenerAuthorized": False,
        "productionAdmissionAccepted": False,
        "privacyQualified": False,
        "resourceCeilingQualified": False,
        "gaAccepted": False,
        "scope": "Implementation direction after offline API/probe evidence review; no fresh runtime or native run in root selection.",
    }
    target.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "bindings": len(bindings), "producerFiles": len(seal["files"]), "sourceInputs": len(accepted["sourceInputs"])}))


if __name__ == "__main__":
    main()
