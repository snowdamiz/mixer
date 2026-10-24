#!/usr/bin/env python3
"""Root evidence checks and bounded implementation-seam selection, not a release gate."""
import datetime
import hashlib
import json
import pathlib
import subprocess

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PROBE = ROOT / "verification/hosted-transaction-context-preflight"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


command = ["python3", "-B", "verification/hosted-transaction-context-preflight/check.py"]
result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
(OUT / "integrity-output.log").write_text(result.stdout)
checked = json.loads(result.stdout)
assert checked["passing_cases"] == 24 and checked["all_owned_scratch_absent"]
assert checked["artifact_tree_digest"] == "a57c2127911466c9c7a993acfe9738506e8e78eaf3bf882f78194b1e16892dfc"
sources = {}
excerpts = json.loads((PROBE / "run-3/primary-source-evidence.json").read_text())
for excerpt in excerpts:
    path = ROOT / "hosted/deps" / excerpt["package"] / excerpt["path"]
    assert digest(path) == excerpt["source_sha256"], str(path)
    lines = path.read_text().splitlines(keepends=True)
    assert "".join(lines[excerpt["first_line"] - 1:excerpt["last_line"]]) == excerpt["text"], str(path)
    sources[str(path.relative_to(ROOT))] = digest(path)

selection = {
    "schema": 1,
    "status": "root-selected-preimplementation-seam-product-acceptance-pending",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "review": {
        "command": command, "exitCode": 0,
        "producerArtifactBindingsVerified": checked["files"],
        "installedPrimarySourceFiles": sources,
        "installedPrimarySourceExcerptsVerified": len(excerpts),
        "sourceReview": "Root inspected actual context entry/validation/query/cleanup and executable transaction, timeout, lock and checkout tests. Integrity checks are fresh; 24 runtime cases are the producer's exact retained run-3, not a second root runtime run.",
        "historicalFailure": "run-2 deadline-only queued checkout failed and remains retained; run-3 supplies queue:false."
    },
    "decisions": [
        "Use a fixed Repo and owning process, checked public dynamic Repo, fresh active invocation reference, exact action/target and actual SQL backend/full xid8/database/current role/transaction-local nonce. Revalidate before every fixed repository operation; process dictionary and in_transaction? alone are insufficient.",
        "Use queue:false for protected transaction admission. A busy healthy pool rejects before callback entry and maps to storage unavailable; any retry starts fresh authorization. This is not a hard scheduling or stalled-pool-process latency guarantee.",
        "Set READ COMMITTED first, use the same absolute monotonic deadline capped at five seconds, remaining per-call timeout, decreasing transaction-local statement_timeout and 250ms lock_timeout. Read current policy in a separate statement after all canonical locks. Remove invocation marker in after and rely on transaction-local SQL cleanup.",
        "The DBConnection deadline invalidates/disconnects the checked-out connection; it does not kill a BEAM callback. Keep product callbacks fixed and bounded, with no customer code, arbitrary SQL, async work or network/signing. HTTP/request admission and cancellation require their own integration checks.",
        "A failure racing an already-sent COMMIT is uncertain. Return storage unavailable and require a fresh authorized principal-bound idempotent retry; do not claim every timeout proves rollback.",
        "Full xid is retained as text and requires the qualified primary PostgreSQL capability. No backend-only identity, 32-bit truncation, replica fallback, malicious-BEAM protection or runtime role/RLS qualification is implied."
    ],
    "scope": "Public API/actual database identity and deadline seam selected for subsequent product implementation. No live authorization, migration, repository or HTTP implementation is accepted here; Neon, providers, native, physical phones and GA gates remain pending.",
    "bindings": {
        "review.py": digest(pathlib.Path(__file__).resolve()),
        "integrity-output.log": digest(OUT / "integrity-output.log"),
        "../hosted-transaction-context-preflight/receipt.json": digest(PROBE / "receipt.json"),
        "../hosted-transaction-context-preflight/artifact-manifest.json": digest(PROBE / "artifact-manifest.json")
    }
}
(OUT / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
print(json.dumps({"status": selection["status"], "artifactBindings": checked["files"],
                  "primarySourceFiles": len(sources), "primarySourceExcerpts": len(excerpts)}))
