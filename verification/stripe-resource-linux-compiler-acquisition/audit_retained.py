"""Rehash opaque local archives and provenance; never parse/extract/execute them."""
import json
from pathlib import Path
import stat

import acquire


def main():
    here, root = acquire.HERE, acquire.ROOT
    require = acquire.require
    require(acquire.sha(acquire.SELECTION) == acquire.SELECTION_SHA, "selection changed")
    require(acquire.sha(acquire.METADATA_SEAL) == acquire.METADATA_SEAL_SHA, "metadata seal changed")
    for name, expected in json.loads(acquire.METADATA_SEAL.read_text())["files"].items():
        require(acquire.sha(root/name) == expected, "sealed metadata source changed")
    require(acquire.sha(acquire.LOCK) == acquire.LOCK_SHA, "exact lock changed")
    lock = json.loads(acquire.LOCK.read_text())
    allowed = acquire.checked_lock(lock)
    receipt = json.loads((here/"attempt/receipt.json").read_text())
    require(receipt["status"] == "all-36-locked-package-archives-verified-not-extracted", "acquisition failed")
    require(receipt["sourceSha256"] == acquire.sha(here/"acquire.py"), "executed acquisition source changed")
    require(receipt["packageRequests"] == 36 and len(receipt["records"]) == 36,
            "exact request count changed")
    require(receipt["requestRetries"] == receipt["redirectsFollowed"] == 0, "retry/redirect scope changed")
    require(receipt["elapsedSeconds"] <= 180, "cumulative deadline exceeded")
    require(receipt["error"] is None and receipt["cleanup"] ==
            {"allKnownPartialsRemoved": True, "partialFilesRemaining": []}, "cleanup or acquisition error")
    output = here/"attempt/packages"
    require(stat.S_ISDIR(output.lstat().st_mode) and stat.S_ISDIR(output.parent.lstat().st_mode)
            and stat.S_IMODE(output.stat().st_mode) == 0o700 and stat.S_IMODE(output.parent.stat().st_mode) == 0o700,
            "private output directory mode changed")
    expected_files = {Path(item["filename"]).name for item in lock["packages"]}
    require({path.name for path in output.iterdir()} == expected_files, "unexpected or missing cache file")
    records = {record["url"]: record for record in receipt["records"]}
    require(set(records) == set(allowed), "request set changed")
    total = 0
    for url, item in allowed.items():
        path = output/Path(item["filename"]).name
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600,
                "cache file is not an exclusive regular0600 file")
        require(info.st_size == item["bytes"] and acquire.sha(path) == item["sha256"], "signed cached size/hash mismatch")
        record = records[url]
        require(record["status"] == "signed-size-and-SHA256-verified" and record["bytes"] == item["bytes"]
                and record["observedBytes"] == item["bytes"] and record["sha256"] == item["sha256"]
                and record["responseUrl"] == url and record["httpStatus"] == 200
                and record["elapsedSeconds"] <= 30 and record["partialCleanup"], "request provenance mismatch")
        total += info.st_size
    require(total == receipt["verifiedRetainedPackageBytes"] == receipt["observedTransferBytes"] == 50997408,
            "exact transfer sum mismatch")
    for phase in ("controls", "acquire"):
        command = json.loads((here/(phase+"-command.json")).read_text())
        require(command["exitCode"] == 0 and command["refusal"] is None, "observed command failed")
        require(command["observerSourceSha256"] == acquire.sha(here/"run_observed.py"), "observer source changed")
        for record in command["outputs"].values():
            path = root/record["path"]
            require(path.stat().st_size == record["bytes"] <= 524288 and acquire.sha(path) == record["sha256"],
                    "bounded command output changed")
    print(json.dumps({"status": "opaque-archive-and-provenance-audit-pass", "packages": 36,
        "verifiedBytes": total, "partialFiles": 0, "metadataSealUnchanged": True,
        "packageLockUnchanged": True, "packageParsingOrExtraction": False,
        "packageExecution": False}, sort_keys=True))


if __name__ == "__main__":
    main()
