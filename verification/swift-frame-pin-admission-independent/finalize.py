#!/usr/bin/env python3
"""Seal only this independent review under its existing pure-process guard."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("independent_review_guards", HERE / "review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)

receipt = review.json.loads((HERE / "receipt.json").read_text())
receipt["model"] = "gpt-6-astra"
receipt["reasoningEffort"] = "xhigh"
receipt["freshContext"] = True
receipt["orchestrationMetadataSource"] = "root confirmed actual spawn model, reasoning effort and fork_turns:none; not reviewer model introspection"
review.save("receipt.json", receipt)
review.save("verification-attempts.json", {
    "setupFailuresPreserved": [
        {"file": "review-attempt-1.stderr", "cause": "parent compact handoff joined the following 32-file count to the 64-hex seal SHA; rejected before producer member processing", "disposition": "root confirmed actual 64-hex digest; freeze then verified"},
        {"file": "review-attempt-2.stderr", "detail": "producer-replay-attempt-1.stderr", "cause": "reviewer mutation audit resolved safe relative-dirfd tempfile cleanup against cwd and rejected it; Python 3.14 cleanup implementation did not use attempted legacy fallback", "disposition": "reviewer tracks own opened directory descriptors; all 39 producer methods then pass; scratch removed"}
    ],
    "finalSuccessfulCommand": receipt["command"],
    "sourceChecks": receipt["checks"],
    "independentControls": receipt["independentControls"],
    "replayedProducerMethods": receipt["replayedProducerMethods"],
    "candidateDefectsObserved": 0,
    "actualCompilationsOrRuntimeAttempts": 0,
})
assert review.sha((review.PRODUCER / "seal.json").read_bytes()) == review.SEAL_SHA
assert receipt["sourceTreeDigest"] == review.sha((HERE / "readset.json").read_bytes())
files = {str(path.relative_to(HERE)): review.record(path.read_bytes()) for path in sorted(HERE.rglob("*")) if path.is_file() and path.name != "seal.json"}
review.save("seal.json", {"schema": 1, "scope": "independent bounded source acceptance of paired-128-v1; compiled finite/geometry/full execution pending", "fileCount": len(files), "totalBytes": sum(row["bytes"] for row in files.values()), "files": files})
print(review.json.dumps({"sealSHA256": review.sha((HERE / "seal.json").read_bytes()), "fileCount": len(files), "totalBytes": sum(row["bytes"] for row in files.values())}, sort_keys=True))
