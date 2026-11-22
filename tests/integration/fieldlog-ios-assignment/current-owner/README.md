# Replay current FieldLog iOS assignment routing

The host test covers recovery after a real workspace-open failure and report
presentation after an assignment sheet closes. Use a Mixer checkout containing
the pinned revisions and local Git stores for FieldLog, Swift Crypto, and Swift
ASN.1. The replay checks the source trees, dependency pins, and exact patch
digests.

From the Mixer checkout, set `FIELDLOG_GIT_STORE`, `SWIFT_CRYPTO_GIT_STORE`,
and `SWIFT_ASN1_GIT_STORE` to the respective store paths. Run the host replay.

```bash
python3 -B - <<'PYTHON'
from pathlib import Path
import base64
import os
import shutil
import subprocess
import tempfile

mixer = Path.cwd()
inputs = mixer / "tests/integration/fieldlog-ios-assignment/current-owner"
scratch = mixer / "verification/local"
scratch.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="ios-assignment-inputs.", dir=scratch) as folder:
    delivery = Path(folder)
    for name in ("replay.sh", "AssignmentHost.swift", "HostPackage.swift"):
        shutil.copy2(inputs / name, delivery / name)
    for name in ("fieldlog-ios-assignment-41eaf5b4", "fieldlog-ios-assignment-review-fixes"):
        packed = inputs / f"{name}.patch.b64"
        (delivery / f"{name}.patch").write_bytes(base64.b64decode(packed.read_bytes()))
    subprocess.run([
        delivery / "replay.sh", mixer, os.environ["FIELDLOG_GIT_STORE"],
        os.environ["SWIFT_CRYPTO_GIT_STORE"], os.environ["SWIFT_ASN1_GIT_STORE"],
        delivery / "fieldlog-ios-assignment-41eaf5b4.patch", "host",
    ], check=True)
PYTHON
```

Use `all` for the host replay and unsigned generic arm64 iPhoneOS Debug and
Release builds.
