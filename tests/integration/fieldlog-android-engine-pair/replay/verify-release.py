#!/usr/bin/env python3
"""Expose the pinned Mixer identity and update CLIs to the origin harness."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import NamedTemporaryFile

tools = Path(__file__).resolve().parent
mode, identity, *args = sys.argv[1:]
info = json.loads(subprocess.check_output([tools / "mixer-identity", "inspect-v2", identity]))
host = info["installedRuntime"]
if mode == "identity" and not args:
    print(json.dumps(host))
elif mode == "verify" and len(args) == 8:
    roots, manifest, payload, assignment, channel, installation, last, now = args
    options = {
        "roots": roots, "manifest": manifest, "payload": payload, "assignment": assignment,
        "channel": channel, "installation": installation, "last-sequence": last, "now": now,
    }
    with NamedTemporaryFile(dir=Path(identity).parent) as host_file:
        host_file.write(json.dumps(host).encode())
        host_file.flush()
        child = subprocess.run(
            [tools / "mixer-update", "verify-v3", "--host", host_file.name,
             *(part for key, value in options.items() for part in ("--" + key, value))],
            capture_output=True, check=False,
        )
    output = child.stdout
    report = json.loads(output)
    if child.returncode:
        print(json.dumps({"error": report["code"]}))
    else:
        print(json.dumps({"artifactSHA256": report["artifactSHA256"], "releaseID": report["releaseID"],
                          "sequence": report["assignmentSequence"], "cohortBucket": report["cohortBucket"]}))
    sys.exit(child.returncode)
else:
    sys.exit("Expected identity or verify")
