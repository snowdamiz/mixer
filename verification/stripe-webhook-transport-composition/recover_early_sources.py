"""Recover failed harness source closures without rewriting their sealed attempts.

Attempts 2/3 failed before the first collector wrote a source archive. Their
preserved actual formatter diff plus immutable raw source fully identify the
normalized module. This recovery is explicit and separate from original output.
"""
import difflib
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()
raw = (HERE / "attempt-1/reviewed-webhook-transport.ex").read_bytes()
normalized = (HERE / "attempt-4/source/hosted/lib/mixer_hosted/billing/webhook_transport.ex").read_bytes()
expected_diff = "".join(difflib.unified_diff(raw.decode().splitlines(keepends=True), normalized.decode().splitlines(keepends=True), fromfile="reviewed/webhook_transport.ex", tofile="normalized/webhook_transport.ex"))
assert sha(raw) == "62cd64f8711ff5296270b38a1c679336e075705bf5845c88d82d7e4bbd28aec0"
assert sha(normalized) == "56a26cf3a56f3e5a5b2d8f5104fc7c3371b0e44918b007197be5871cf94ef1a5"
with tarfile.open(HERE / "attempt-1/source-closure.tar.gz") as archive:
    source = {member.name: archive.extractfile(member).read() for member in archive.getmembers()}
source["hosted/lib/mixer_hosted/billing/webhook_transport.ex"] = normalized
assert len(source) == 72
inputs = {name: sha(data) for name, data in source.items()}

for attempt in ["attempt-2", "attempt-3"]:
    original = HERE / attempt
    assert (original / "formatter-only.patch").read_text() == expected_diff
    out = HERE / "source-recovery" / attempt
    out.mkdir(parents=True)
    (out / "source-inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    archive_path = out / "reconstructed-source-closure.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, data in sorted(source.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    receipt = {
        "status": "explicit-source-reconstruction-not-original-run-archive",
        "reason": "Original failed harness attempts stopped before source archival. No original failed receipt, output, or seal was rewritten.",
        "originalAttempt": attempt,
        "originalSealSHA256": sha((original / "seal.json").read_bytes()),
        "observedActualDiffSHA256": sha((original / "formatter-only.patch").read_bytes()),
        "baseArchive": "attempt-1/source-closure.tar.gz",
        "baseArchiveSHA256": sha((HERE / "attempt-1/source-closure.tar.gz").read_bytes()),
        "exactDiffMatchesAcceptedNormalizedSource": True,
        "sourceFiles": 72,
        "sourceDigest": sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()),
        "archiveSHA256": sha(archive_path.read_bytes()),
        "failedAttemptPromoted": False,
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"recoveredEarlyFailedSourceClosures": 2, "originalAttemptsRewritten": False}))
