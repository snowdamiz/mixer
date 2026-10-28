#!/usr/bin/env python3
"""Seal this review's own files under its existing offline guards."""
import datetime
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("independent_seal_guard", HERE / "review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
receipt = json.loads((HERE / "receipt.json").read_bytes())
assert receipt["allPureChecksPassed"] and receipt["totalPureMethods"] == 56
assert receipt["scratchRemoved"] and not (HERE / "scratch").exists()
assert receipt["candidateSealSHA256"] == review.EXPECTED_SEAL
assert receipt["sourceClosures"] == list(review.EXPECTED_SOURCES)
assert receipt["readsetSHA256"] == review.sha((HERE / "readset.json").read_bytes())
files = {str(path.relative_to(HERE)): review.record(path.read_bytes())
         for path in sorted(HERE.rglob("*")) if path.is_file() and path.name != "seal.json"}
review.save("seal.json", {"schema": 1, "createdAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "decision": "source-accept", "scope": "independent frozen source review only; root selection and all actual Rust/geometry/full runs pending",
    "candidateSealSHA256": review.EXPECTED_SEAL, "filesCount": len(files), "totalBytes": sum(row["bytes"] for row in files.values()),
    "files": files})
print(json.dumps({"sealSHA256": review.sha((HERE / "seal.json").read_bytes()), "files": len(files), "bytes": sum(row["bytes"] for row in files.values())}))
