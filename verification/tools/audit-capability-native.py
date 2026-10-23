#!/usr/bin/env python3
"""Audit the exact native C implementation and independent review evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OWNER = "vm/verification/capability-native/2026-10-23-final/receipt.json"
REVIEW = "verification/capability-native-review/receipt.json"


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def require(ok, detail):
    if not ok:
        raise RuntimeError(detail)


def logs(commands):
    for command in commands:
        path = command.get("log", command.get("output"))
        digest = command.get("sha256", command.get("output_sha256"))
        require(command["exit_code"] == 0 and sha(path) == digest, path)
    return len(commands)


def main():
    owner, review = read(OWNER), read(REVIEW)
    require(owner["source_unchanged_during_checks"], "owner source drift")
    require(review["independent_public_checks_passed"], "independent C tests failed")
    require(not review["owner_matrix_audit_pending"], "independent matrix audit pending")
    require(review["independent_scoped_review_passed"] and not review["blocking_findings"], "independent review incomplete")
    audit = review["owner_matrix_audit"]
    require(audit["passed"] and sha(audit["path"]) == audit["sha256"] and sha(OWNER) == audit["owner_receipt_sha256"], "owner matrix audit changed")
    require(review["source_export_unchanged"] and review["live_source_matches_at_end"], "review source drift")
    manifest = owner["source_manifest"]
    require(sha(manifest) == owner["source_manifest_sha256"] == review["freeze_sha256"], "freeze mismatch")
    files = {}
    for line in (ROOT / manifest).read_text().splitlines():
        digest, path = line.split("  ", 1)
        require(path not in files and sha(path) == digest, path)
        files[path] = digest
    require(len(files) == owner["source_files"] == 90, "source count mismatch")
    require({item["path"]: item["sha256"] for item in review["source"]} == files, "review input mismatch")
    for item in review["source"]:
        require((ROOT / item["path"]).stat().st_size == item["bytes"], item["path"])
    for path, digest in owner["unchanged_legacy_inputs"].items():
        frozen = subprocess.check_output(["git", "show", "cc0ac37abf45c59df7c85f59ebbb038af7c0a251:" + path], cwd=ROOT)
        require(sha(path) == hashlib.sha256(frozen).hexdigest() == digest, path)
    require(sha("vm/verification/capability-native/verify.py") == owner["verification_driver_sha256"], "owner driver changed")
    for path, digest in review["review_source_sha256"].items():
        require(sha("verification/capability-native-review/" + path) == digest, path)
    for mode, expected in [("default-debug", 91), ("default-release", 91), ("all-debug", 185), ("all-release", 185), ("oracles-debug", 9), ("oracles-release", 9)]:
        require(owner["test_counts"][mode]["passed"] == expected, mode)
    for run in review["runs"]:
        require(run["result"]["passed"] and run["result"]["take_close_races"] == 48 and run["result"]["ack_close_races"] == 48, "public races failed")
    binding = owner["additional_review_archive_provenance"]
    require(sha(binding["path"]) == binding["sha256"] and sha(binding["script"]) == binding["script_sha256"], "archive provenance changed")
    provenance = read(binding["path"])
    require(provenance["source_manifest_sha256"] == review["freeze_sha256"], "archive source mismatch")
    local_archives = []
    for mode, artifact in review["archives"].items():
        require(artifact["sha256"] == provenance["archives"][mode]["sha256"], "review archive mismatch")
        path = Path(artifact["path"])
        if (ROOT / path).exists():
            require(sha(path) == artifact["sha256"], "local archive changed")
            local_archives.append(mode)
    require(review["archives"]["release"]["sha256"] == owner["artifacts"]["native"]["archive_sha256"], "native release mismatch")
    counts = {"sourceFiles": len(files), "ownerCommandLogs": logs(owner["commands"]),
              "archiveBuildLogs": logs(provenance["commands"]), "reviewCommandLogs": logs(review["commands"]),
              "unchangedLegacyInputs": len(owner["unchanged_legacy_inputs"]), "localArchivesRehashed": local_archives}
    receipt = {
        "schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sourceManifestSHA256": review["freeze_sha256"], "matched": counts,
        "receipts": {path: sha(path) for path in [OWNER, REVIEW, binding["path"]]},
        "rootSourceReview": "Shared registry, synchronized transient release, destructor retention, preflight, native ticket ledger, unwind quarantine, full validation split and status mapping reviewed; no outstanding findings.",
        "checks": owner["test_counts"], "independentPublicRuns": review["runs"],
        "result": "Frozen native C implementation and independent public-boundary review matched",
        "limitations": owner["known_limits"] + [
            "Default and experimental native C archives preserve legacy admission; there is no profile4 or activation/release migration.",
            "A repeated debug build differed in bytes; exact tested archive provenance is retained, with no bit-reproducibility claim.",
            "Expanded Linux native C CI is a subsequent check; local author/reviewer execution was macOS arm64.",
        ],
    }
    (ROOT / "verification/capability-native-integration-2026-10-23.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
