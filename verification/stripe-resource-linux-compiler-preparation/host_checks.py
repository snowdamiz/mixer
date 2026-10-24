#!/usr/bin/env python3
"""Proposal consistency and preserved-evidence controls, with no acquisition."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SIGNER = "F6ECB3762474EDA9D21B7022871920D1991BC93C"


def validate(proposal):
    if (proposal["status"] != "proposal-only-no-acquisition-selected"
            or proposal["resolvedPackageLock"] is not None
            or proposal["resolvedVersionsOrHashesKnown"] is not False):
        raise ValueError("unresolved preparation cannot claim a package lock")
    if proposal["minimalProposedPackageRoots"] != ["gcc:arm64", "libc6-dev:arm64", "binutils:arm64"]:
        raise ValueError("package scope changed")
    acquisition = proposal["officialAcquisition"]
    if (acquisition["origin"] != "https://ports.ubuntu.com/ubuntu-ports/"
            or acquisition["suites"] != ["noble", "noble-updates", "noble-security"]
            or acquisition["component"] != "main" or acquisition["architecture"] != "arm64"
            or acquisition["requiredSignerFingerprint"] != SIGNER
            or acquisition["allowUnauthenticated"] is not False
            or acquisition["allowInsecureOrTrustedYes"] is not False
            or acquisition["sharedAptConfigOrState"] is not False
            or acquisition["followUnselectedRedirect"] is not False
            or acquisition["separateRootSelectionBeforeDebFetch"] is not True):
        raise ValueError("acquisition proposal scope changed")
    for key, ceiling in (("metadataTransferBytes", 33554432), ("packageTransferBytes", 134217728),
            ("packageExpandedBytes", 536870912), ("packageCount", 48), ("ownedStorageBytes", 805306368)):
        if type(proposal["proposedBounds"][key]) is not int or not 0 < proposal["proposedBounds"][key] <= ceiling:
            raise ValueError("bounded proposal changed")
    for key in ("containerStarted", "packageOrSignedMetadataPayloadDownloaded", "compilerExecuted", "imageBuilt",
            "rootfsConstructed", "runtimeResourceAuthorized", "LinuxCompilationAccepted", "LinuxArtifactAccepted",
            "LinuxResourceRuntimeAccepted", "gaAccepted"):
        if proposal[key] is not False:
            raise ValueError("preparation cannot claim execution or acceptance")
    if any(phase["selected"] is not False for phase in proposal["phases"]):
        raise ValueError("future phases remain unselected")


def main():
    proposal = json.loads((HERE / "proposal.json").read_text())
    validate(proposal)
    mutations = (("gaAccepted", True), ("resolvedPackageLock", []), ("containerStarted", True))
    changed = []
    for key, bad in mutations:
        row = copy.deepcopy(proposal)
        row[key] = bad
        changed.append(row)
    row = copy.deepcopy(proposal)
    row["officialAcquisition"]["allowUnauthenticated"] = True
    changed.append(row)
    row = copy.deepcopy(proposal)
    row["proposedBounds"]["packageTransferBytes"] += 1
    changed.append(row)
    row = copy.deepcopy(proposal)
    row["phases"][0]["selected"] = True
    changed.append(row)
    for row in changed:
        try:
            validate(row)
        except ValueError:
            continue
        raise AssertionError("mutated proposal was accepted")
    seals = {
        "verification/stripe-resource-linux-artifact-preparation/seal.json": "e72d9e750aceba69d22ec01d2e41d64897db60de37e48482aae944030fe53f9b",
        "verification/stripe-resource-linux-tool-payload/seal.json": "b63ac384fcfa6648321c4708d1b560dd2aa7d1001fc4306899a7b39d8289a340",
        "verification/stripe-resource-linux-tool-payload-v2/seal.json": "06e3a6e1306820f7fb9678687f33b4da9ed9e04915941b19bb375d55ffb14c58",
        "verification/stripe-resource-linux-tool-payload-v3/seal.json": "0286c4cf72503a913520b19bdd7f1b877da995d5d95cf62cc85744015603bf87",
    }
    checked = 0
    for name, expected in seals.items():
        path = ROOT / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        for filename, binding in json.loads(path.read_text())["files"].items():
            assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == binding, filename
            checked += 1
    print(json.dumps({"schema": 1, "status": "passed-source-proposal-and-preserved-bindings-only",
        "hostControls": {"passed": 7, "failed": 0, "scope": "one proposal acceptance and six in-memory rejection controls"},
        "preservedSeals": len(seals), "preservedFileBindingsChecked": checked,
        "packageLockResolved": False, "packageSignaturesVerified": False,
        "compilerExecuted": False, "LinuxCompilationAccepted": False, "gaAccepted": False}, indent=2))


if __name__ == "__main__":
    main()
