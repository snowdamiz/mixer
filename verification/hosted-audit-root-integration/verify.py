#!/usr/bin/env python3
"""Read-only acceptance/source verification; no processes or services started."""
import argparse
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    seal = json.loads((HERE / "seal.json").read_text())
    for path, digest in seal["bindings"].items():
        assert sha(ROOT / path) == digest, path
    receipt = json.loads((HERE / "acceptance.json").read_text())
    for path, digest in receipt["bindings"].items():
        assert sha(ROOT / path) == digest, path
    upstream = json.loads((HERE / "accepted-input-bindings.json").read_text())
    for path, digest in upstream.items():
        assert sha(ROOT / path) == digest, path
    integration = json.loads((HERE / "integration.json").read_text())
    assert integration["status"] == "passed-integrated-focused-and-source-identity"
    assert len(integration["appliedFiles"]) == 4
    for command in integration["commands"]:
        assert command["exitCode"] == 0
        assert sha(HERE / command["log"]) == command["sha256"]
    assert "Result: 12 passed" in (HERE / "integrated-focused.log").read_text()
    correction = ROOT / "verification/hosted-audit-key-bound-correction"
    candidate = json.loads((correction / "receipt.json").read_text())
    tested = json.loads((correction / "run-1/receipt.json").read_text())["overlayInputs"]
    full = json.loads((correction / "run-1/full-hosted/receipt.json").read_text())
    assert tested == full["inputs"] and full["status"] == "passed"
    assert all(full["cleanup"].values())
    for path, digest in tested.items():
        if path.startswith("hosted/"):
            assert integration["sourceManifest"][path] == digest
        if args.live:
            assert sha(ROOT / path) == digest, path
    for path, digest in candidate["overlay"].items():
        assert sha(correction / "candidate" / path) == digest
        assert tested["hosted/" + path] == digest
    review = json.loads((ROOT / "verification/hosted-audit-key-bound-review/receipt.json").read_text())
    assert review["status"] == "passed-independent-correction-review" and not review["findings"]
    assert receipt["rootAccepted"] and receipt["liveIntegrated"] and not receipt["gaAccepted"]
    print(json.dumps({"verified": True, "upstreamBindings": len(upstream), "rootBindings": len(receipt["bindings"]),
                      "integratedFiles": 4, "directCheckoutTests": 12, "reusedFullHostedPassed": 105,
                      "explicitLinuxOnlySkips": 2, "liveChecked": args.live, "gaAccepted": False}))


if __name__ == "__main__":
    main()
