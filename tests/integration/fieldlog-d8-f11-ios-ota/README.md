# F11 signed iOS release witness

This fixture extends the reviewed F11 Simulator witness at Stage
`e00a90daf2`. In one installation, the XCTest opens a stock signed
read-only prior, requests the exact historical successor, runs the
reviewed UIKit Paste, Save draft and Commit assertions, checks the commit
in a fresh process, then opens the signed rollback and reopens it offline.
Only the successor can acquire the reviewed paste and action authority.
The prior uses ordinary Guest UI, spends no capability calls, and is
selected by the digest of its verified VM input. The existing execution
preflight and installed storage grant still apply to each artifact.

The app bundle contains public trust and identity material, the seed and
expected wire hashes. Every online phase fetches the actual signed
assignment and artifact from the stock loopback origin. The offline phase
uses the retained rollback candidate. Signed releases live outside the
app in the kit. The controller closes the origin and observes connection
refusal before the offline launch.

## Rebuild the kit

Use the pinned Stage, the FieldLog object store with the Pair25 base and
three F11 corpus blobs, the retained F09 stock tools, and a fresh ignored
work directory. Run the preparation and arm64 iOS Simulator VM build from
the [reviewed fixture instructions](../fieldlog-d8-f11-ios-simulator/README.md).
Then run these commands from this directory, with absolute paths.

```sh
native="$stage/tests/integration/fieldlog-d8-f11-ios-simulator"
sealed="$work/export/source/capability-activation/verification/f11-native/Witness/SealedInput"
python3 -B issue.py "$stage" "$work" "$sealed" "$work/final-releases" "$openssl"
python3 -B delivery.py probe "$tools" "$work/final-releases" "$work/final-probe" "$sealed/delivery.json"
python3 -B compose.py "$stage" "$work"
PYTHONPATH="$native" python3 -B - "$native" "$work" <<'PY'
from pathlib import Path
import runpy
import sys
native, work = map(Path, sys.argv[1:])
build = runpy.run_path(str(native / "build.py"))["build"]
build.__globals__["setup"] = lambda work: work / "export/source/capability-activation/verification/f11-native/Witness"
raise SystemExit(build(work, 95))
PY
python3 -B package.py "$stage" "$work" "$tools" "$kit"
python3 -B check-kit.py "$kit" "$work/kit-check"
```

## Root-owned dispatch inputs

Verify `MEMBERS.sha256` after copying the kit. The development roots
expire two hours after issuance. A fresh controller run takes a new
scratch path. It writes `control.json` when ready.
`configure.py` produces a private plan beside the original one. The
relative paths still resolve after moving the kit.

```sh
python3 -B "$kit/delivery.py" serve "$kit/tools" "$kit/releases" "$controller" "$kit/delivery.json"
# After the controller reports readiness, from a separate command:
python3 -B "$kit/configure.py" "$kit" "$controller/control.json" "$kit/private.xctestrun"
```

The selector is
`F11NativeWitnessUITests/F11WitnessUITests/testPasteSaveAndCommitRestoredNote`.
The host-only check verifies controller order, authorization, exact
served bytes and closure. Native execution requires separate owner
admission, Accessibility preflight, signing and an owned Simulator.
