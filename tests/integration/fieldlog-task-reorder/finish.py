"""Seal the packet after checking the observed command and offline readbacks."""
from pathlib import Path
import shutil
import sys

from package import CALC, calculation, digest, read, require, write

work, output = map(Path, sys.argv[1:])
build = read(output / "build-receipt.json")
host = read(output / "host-receipt.json")
require(host["status"] == "passed" and host["runtime"] == build["androidRuntime"],
        "Expected a closed host replay for the exact Android runtime")
require(digest(output / build["apk"]) == build["apkSHA256"]
        and calculation.inventory(output, output / "delivery-android") == read(output / "materials.sha256.json"),
        "APK or delivery changed after assembly")
runs = {path.stem: read(path) for path in (work / "logs").glob("*.json")}
expected = {"preflight", "source-fetch", "source-checkout", "source-check", "mixer-export", "trace-overlay",
            "row-overlay", "appearance-export", "vm-android", "vm-host", "guests", "java", "android",
            "host", "package", "host-replay"}
require(set(runs) == expected and all(run["exit"] == 0 and run["custody"] == "closed" and "interrupted" not in run
                                     for run in runs.values()), "Incomplete or interrupted build stage")
for target in ("android", "host"):
    engine = read(work / f"{target}-engine/receipt.json")
    require(engine["source_revision"] == build["mixerRevision"] and engine["commands"]
            and all(c["exit_code"] == 0 and c["problem"] is None for c in engine["commands"]),
            f"Incomplete {target} VM build")

write(output / "rebuild-receipt.json", {
    "scope": "Source-built APK and macOS host presentation. Android device run is root-owned.",
    "preflight": read(work / "preflight.json"),
    "commands": runs,
    "buildReceiptSHA256": digest(output / "build-receipt.json"),
    "hostReceiptSHA256": digest(output / "host-receipt.json"),
})
for name in ("README.md", "verify-workspace.py"):
    shutil.copyfile(Path(__file__).with_name(name), output / name)
shutil.copyfile(CALC.parent / "android-readback.py", output / "android-readback.py")
with (output / "SHA256SUMS").open("x") as checksums:
    for name, sha in sorted(calculation.inventory(output, output).items()):
        if name != "SHA256SUMS":
            checksums.write(f"{sha}  {name}\n")
