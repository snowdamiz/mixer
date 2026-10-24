#!/usr/bin/env python3
"""Retain exact host-only preparation checks. Native commands are not called."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time

import prepare
import run_qualification


def main():
    here, root = prepare.HERE, prepare.ROOT
    source_before = run_qualification.source_files()
    commands = [
        ("host-controls", [sys.executable, "-m", "unittest", "discover", "-s", str(here), "-p", "test_*.py", "-v"]),
        ("shell-syntax", ["/bin/sh", "-n", str(here/"native-qualify.sh")]),
        ("data-audit-final", [sys.executable, str(here/"prepare.py"), "--output", str(here/"data-audit-final.json")]),
        ("adapter-default-refusal", [sys.executable, str(here/"run_qualification.py")]),
        ("source-revision", [shutil.which("git"), "rev-parse", "HEAD"]),
    ]
    observed = []
    for label, argv in commands:
        started = time.monotonic()
        result = subprocess.run(argv, cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=30)
        outputs = {}
        for stream, data in (("stdout", result.stdout), ("stderr", result.stderr)):
            prepare.require(len(data) <= 1048576, "host output ceiling")
            path = here/(label+"."+stream)
            with path.open("xb") as file:
                file.write(data)
            outputs[stream] = {"path": str(path.relative_to(root)), "bytes": len(data), "sha256": prepare.sha(path)}
        observed.append({"argv": argv, "cwd": str(root), "exitCode": result.returncode,
                         "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         "elapsedSeconds": time.monotonic()-started, "outputs": outputs})
        prepare.require(result.returncode == 0, "host control failed: "+label)
    prepare.require(source_before == run_qualification.source_files(), "source changed during checks")
    record = {"schema": 1, "scope": "Host-only source/data preparation; no native compiler or container attempt",
              "commands": observed, "sourceFiles": source_before, "sourceDigest": prepare.digest(source_before),
              "tools": {"python": {"executable": str(Path(sys.executable).resolve()), "version": sys.version,
                                    "sha256": prepare.sha(Path(sys.executable).resolve())},
                        "shell": {"path": "/bin/sh", "sha256": prepare.sha("/bin/sh"), "operation": "-n syntax check only"},
                        "tarfile": {"path": tarfile.__file__, "sha256": prepare.sha(tarfile.__file__)}},
              "nativeAttempts": 0, "compilerExecuted": False, "packageDownloads": 0, "hostExtractionExecuted": False}
    with (here/"host-commands.json").open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": "host-preparation-controls-pass", "commands": len(observed),
                      "sourceDigest": record["sourceDigest"], "receiptSHA256": prepare.sha(here/"host-commands.json")}))


if __name__ == "__main__":
    main()
