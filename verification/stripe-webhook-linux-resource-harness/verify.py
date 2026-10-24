#!/usr/bin/env python3
"""Read-only packet verification. Does not launch a role, compiler, or stress."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("resource_controller", HERE / "run.py")
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--seal", action="store_true", help="seal owned packet files after authoring")
    args = parser.parse_args()
    doc = ROOT / "docs/stripe-webhook-linux-resource-harness.md"
    if args.seal:
        controller.require(not any(HERE.glob(".owned-scratch-*")), "cleanup")
        files = {str(p.relative_to(ROOT)): controller.sha(p) for p in HERE.rglob("*")
                 if p.is_file() and p != HERE / "seal.json"}
        files[str(doc.relative_to(ROOT))] = controller.sha(doc)
        for path in ("selection.json", "mutable-execution-index-amendment.json"):
            p = ROOT / "verification/stripe-webhook-resource-ingress-root-review" / path
            files[str(p.relative_to(ROOT))] = controller.sha(p)
        (HERE / "seal.json").write_text(json.dumps({"schema": 1, "scope": "private incomplete implementation and host controls only",
                                                   "files": files, "treeDigest": controller.digest(files)},
                                                  indent=2, sort_keys=True) + "\n")
    seal = controller.load(HERE / "seal.json")
    controller.require(seal["schema"] == 1 and seal["treeDigest"] == controller.digest(seal["files"]), "source_mismatch")
    actual = {str(p.relative_to(ROOT)) for p in HERE.rglob("*") if p.is_file() and p != HERE / "seal.json"}
    expected = {p for p in seal["files"] if p.startswith(str(HERE.relative_to(ROOT)) + "/")}
    controller.require(actual == expected and not any(HERE.glob(".owned-scratch-*")), "source_mismatch")
    for name, expected_sha in seal["files"].items():
        path = ROOT / name
        controller.require(not path.is_symlink() and path.resolve().is_relative_to(ROOT)
                           and controller.sha(path) == expected_sha, "source_mismatch")
    receipt = controller.load(HERE / "authoring-receipt.json")
    controller.require(receipt["status"] == "passed-host-controls-linux-unavailable-implementation-incomplete"
                       and receipt["hostTests"] == {"run": 17, "passed": 15, "skipped": 2}, "runtime_error")
    controller.require(receipt["runtimeCasesExecuted"] == 0 and receipt["LinuxCOrNIFOrBEAMCompiled"] is False
                       and receipt["gaAccepted"] is False and receipt["independentReview"] == "pending", "runtime_error")
    controller.require(receipt["harnessDigest"] == controller.harness_digest(), "source_mismatch")
    for name, expected_sha in receipt["sourceInputs"].items():
        controller.require(controller.sha(ROOT / name) == expected_sha, "source_mismatch")
    matrix = controller.load(HERE / "matrix.json")
    selected = controller.load(controller.CONTRACT / "matrix.json")
    controller.require(len(matrix["rows"]) == 30 and {r["id"] for r in matrix["rows"]} == {
        r["id"] for r in selected["rows"]}, "runtime_error")
    controller.require(all(r["status"] == "pending-runtime" and r["runtimeExecuted"] is False for r in matrix["rows"]),
                       "runtime_error")
    controller.require(not any(HERE.glob("mixer-resource-host-control-*")), "cleanup")
    if args.live:
        controller.profile(controller.CONTRACT / "profile.json")
        controller.source_inputs()
    print(json.dumps({"status": "passed-packet-host-controls-only", "live": args.live,
                      "sealedFiles": len(seal["files"]), "hostTestsPassed": 15, "hostTestsSkipped": 2,
                      "pendingRuntimeRows": 30, "runtimeCasesExecuted": 0,
                      "implementationComplete": False, "independentReview": "pending", "gaAccepted": False}))


if __name__ == "__main__":
    main()
