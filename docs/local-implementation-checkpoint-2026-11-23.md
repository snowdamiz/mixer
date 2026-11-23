# Local implementation checkpoint, November 23, 2026

Six of the eight local gates passed. L02 and L08 remain open. This checkpoint records the results available when work stopped for the plan revision. The local checklist remains the source for gate decisions. [Local gates](../gates/local.json) · [Work graph](../work-graph.json)

## L02 shared native appearance

The ordinary iOS Settings replay passed the French regional date, Larger Text, diagnostics, and cold preference checks. The corrected Android account lifecycle passed. The reference screens have matched native captures on iOS 26.5 and Android API 36. Three Android dark switch labels painted black on a dark background, and the iOS held-press run recorded glass outside the switch cover. Both defects still need installed evidence for a correction. The source checkpoint includes the exact Pair28 transition, the separate CLI API-floor check, the Android paint correction, and two Apple pressed-state experiments. [Settings receipt](../verification/receipts/l02-ios-settings-cold-native-20261123.json) · [Android raster failure](../verification/receipts/l02-android-dark-switch-label-raster-refusal-20261123.json) · [iOS pressed-state failure](../verification/receipts/l02-ios-held-switch-compositor-refusal-20261123.json) · [L02 source](../verification/receipts/local-checkpoint-20261123-l02-source.json)

## L08 FieldLog

- **D2 shared app.** FieldLog tree `74560abe2ef0` passed four iOS Simulator selectors and the Android shared queue replay from the admitted seed. The full Android run stopped after fifteen saves when the title readback returned `Inspec`. The focused replay saved `Inspection 16` and passed queue and cold readback. The separate input trace is ready for an emulator run. The newer Entry and project picker candidates passed their host replays and linked both products. The latest picker candidate shares 3,070 of 6,426 linked Swift lines (47.77%). Installed verification of those candidates and the 90% target remain open. [Matched native receipt](../verification/receipts/l08-d2-shared-queue-paired-native-20261123.json) · [D2 source](../verification/receipts/local-checkpoint-20261123-d2-source.json)
- **D8 F02 checklist reorder.** The ordinary signed Android reorder passed the scoped host replay. During the native attempt the launcher button reached into the system gesture area, and the center tap opened Recents. The inset correction and native replay are preserved for later verification. [Native failure receipt](../verification/receipts/l08-d8-f02-android-launch-button-insets-20261123.json) · [F02 source](../verification/receipts/local-checkpoint-20261123-d8-f02-source.json)
- **D8 F10 Pending Changes.** The ordinary iOS route passed signed prior, exact replacement, rollback, both cached reopens, and the disabled control on one Simulator installation. The public CLI and local Go origin served the live phases. Explicit offline mode made zero origin requests and retained the candidate, sequence, and workspace. Full health checkpoint hashes refreshed on reopen. The earlier Android direct-file opt-in did not display the target frame. The separate ordinary Android live candidate reached host frame health for all three live releases, then hit the 50 ms turn deadline during the exact offline reopen in the final host run. Installed Android live delivery remains open. [Native and Android boundary receipt](../verification/receipts/l08-d8-f10-ordinary-ios-live-native-20261123.json) · [F10 source](../verification/receipts/local-checkpoint-20261123-d8-f10-source.json)
- **D8 F11 restored Note.** The private Android development fixture passed focused native editing by Android shell key input, Save, Commit, and stopped-app readback. It preserved all 50 UTF-8 bytes and four line feeds and appended one linked `entrySaved`. The retained iOS witness separately passed stock live delivery. Android live delivery and soft-keyboard composition remain open. The F10 and F11 runs add zero qualifying paired public OTA changes. [Android native receipt](../verification/receipts/l08-d8-f11-android-action-bound-native-20261123.json) · [iOS live receipt](../verification/receipts/l08-d8-f11-ios-live-delivery-20261123.json) · [Independent review](../verification/receipts/fieldlog-l08-f10-f11-native-review-24e4aca4.json) · [F11 source](../verification/receipts/local-checkpoint-20261123-d8-f11-source.json)

## Source recovery

Each source checkpoint stores the exact UTF-8 file bytes, SHA-256, and executable flag. Patch paths and their original handoffs identify the pinned Mixer and FieldLog bases. Some replay scripts use paths from their original worktree. Map those paths to the extracted files and the pinned inputs before running the replay. Release material that has expired needs fresh local development trust. The checkpoints contain source, test drivers, and compact receipts. Local builds and raw native captures remain in their retained paths. The production tree contains the previously adopted changes, including the Go origin enrollment. The source checkpoints preserve the pending candidates for later review.

From the Mixer checkout, this example extracts the D2 checkpoint into a new directory. Substitute the linked source checkpoint for another lane.

```sh
python3 - verification/receipts/local-checkpoint-20261123-d2-source.json ./d2-checkpoint <<'PY'
import hashlib
import json
from pathlib import Path
import sys

bundle = json.loads(Path(sys.argv[1]).read_bytes())
destination = Path(sys.argv[2])
destination.mkdir()
for name, record in bundle["files"].items():
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(name)
    data = record["text"].encode("utf-8")
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ValueError(name)
    path = destination / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(data)
    if record["executable"]:
        path.chmod(0o755)
PY
```
