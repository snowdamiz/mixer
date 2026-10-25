#!/usr/bin/env python3
"""File-only acceptance of frozen reference-source and classifier evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
IDENTITIES = {
    "apple-focus-reference-diagnostic-v1": "9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c",
    "apple-focus-reference-diagnostic-v1-independent-review": "d70da20d45323be52138a6efdbd2d53c74efbd521620584b228bf9f03e3eedbb",
    "apple-focus-reference-diagnostic-v2": "07776c2af95bcc58e126b4ceb0f0dee39dec1138ea96bc9e33bc8a4a0393a3a0",
    "apple-focus-reference-diagnostic-v2-independent-review": "6ca2e2a7d7264664f50046a506b01465287dcc6d88872be528af239d8c0d5a55",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def main():
    output = BASE / "acceptance.json"
    require(not output.exists(), "preserve root acceptance")
    packets = {}
    counts = {}
    for name, identity in IDENTITIES.items():
        path = ROOT / "verification" / name / "handoff.json"
        raw = path.read_bytes()
        require(sha(raw) == identity, "handoff identity changed")
        packet = json.loads(raw)
        require(sha(stable(packet["members"])) == packet["memberTreeSHA256"], "member tree changed")
        for relative, expected in packet["members"].items():
            member = ROOT / relative
            info = member.lstat()
            require(member.resolve() == member and stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "noncanonical member")
            actual = {"kind": "file", "bytes": info.st_size, "mode": stat.S_IMODE(info.st_mode), "sha256": sha(member.read_bytes())}
            require(actual == expected, f"frozen member changed: {relative}")
        packets[name] = packet
        counts[name] = len(packet["members"])
    v1 = packets["apple-focus-reference-diagnostic-v1"]
    require(v1["compileExitCodes"] == {"app": 0, "core": 0, "runner": 0, "ui": 0}, "compiler failure")
    require(v1["cleanup"]["scratchAbsent"] is True and not Path(v1["cleanup"]["removedPath"]).exists(), "compile scratch remains")
    review_dir = ROOT / "verification/apple-focus-reference-diagnostic-v2-independent-review"
    review = json.loads((review_dir / "receipt.json").read_bytes())
    require(review["passed"] is True and review["totalControlsPassed"] == review["totalControlsRun"] == 137, "independent review failed")
    require(review["replayedEarlierControlsPassed"] == 74 and review["additionalControlsPassed"] == 63, "review count differs")
    require(review["selectedRunProvenanceImporterPresent"] is False and review["nativeExecuted"] is False, "scope changed")
    producer = json.loads((ROOT / "verification/apple-focus-reference-diagnostic-v2/host-attempt-1/receipt.json").read_bytes())
    require(producer["passed"] is True and (producer["testsRun"], producer["failures"], producer["errors"], producer["skipped"]) == (34, 0, 0, 0), "producer controls failed")
    result = {
        "schema": 1,
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, str(Path(__file__).relative_to(ROOT))],
        "python": sys.version,
        "verifierSHA256": sha(Path(__file__).read_bytes()),
        "status": "accepted-reference-source-compile-and-classifier-consistency-only",
        "handoffs": IDENTITIES,
        "frozenMemberCountsVerified": counts,
        "producerControls": 34,
        "independentControls": 137,
        "originalReviewFailuresPreserved": 8,
        "sourceTreeSHA256": "696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a",
        "compiledProductArchiveSHA256": "0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8",
        "compilerEvidence": "Retained v1 generic simulator compilation; no root or v2 compiler rerun",
        "cleanup": v1["cleanup"],
        "scope": "File-only source, retained compilation and pure classifier evidence. No producer/reviewer code imported or executed by root.",
        "nativeExecuted": False,
        "runtimeSelected": False,
        "selectedRunProvenanceImporterAccepted": False,
        "completeCaseSet": False,
        "runPassed": False,
        "gaAccepted": False,
        "limitations": [
            "Original authored-first runtime failure remains unchanged; no native focus success is claimed.",
            "A separately reviewed importer must bind official results and unique attachments to the root-selected fresh execution before native interpretation.",
            "Compile warnings and historical failed review are preserved.",
            "Physical phones, full keyboard/cursor/carrier acceptance, FieldLog and GA remain pending."
        ]
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "frozenMemberCountsVerified", "producerControls", "independentControls")}))


if __name__ == "__main__":
    main()
