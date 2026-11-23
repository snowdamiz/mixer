# S3 SwiftUI state and handler spike

The same screen source exercises declaration-keyed `@State`, captured `@Binding`,
keyed `ForEach` rows, structural branches, and closure actions. The test screen
builds against Apple SwiftUI with `APPLE_SWIFTUI`. The other builds resolve the
same names to the experimental views and wrappers in this directory.

## Host results and replay

From the repository root, run:

```sh
python3 -B compiler/experiments/swiftui-state-handlers/replay.py
python3 -B compiler/experiments/swiftui-state-handlers/replay.py --apple-typecheck
```

- **S3n host** passes 14 checkpoints on arm64 macOS with Apple Swift 6.4.2.
  The trace covers conditional reads, changed read order, different state
  values following their rows through a move, branch state reset on
  reinsertion, and captured binding writes after re-render.
- **S3g host** passes the same checkpoints in a full-Swift 6.3.3
  `wasm32-unknown-wasip1` reactor on Node 26.13.1 with WASI Preview 1.
  Plain `@State` declaration discovery works with `-Osize` and linker
  symbol stripping. There is no registration transform in this build.
- Both runs also check that pending handlers are gated, canceled or invalid
  frames leave accepted actions routable, an accepted action invalidates an
  older candidate snapshot, and rollback refuses stale owner callbacks at
  a reused frame and handler ID. The 15-line traces match byte for byte.
  The invalid-render checks include a custom mirror that hides `@State`.
  Staging refuses that view before calling its mirror or evaluating its body.
- The Apple app and UI test sources typecheck for arm64 with iOS deployment
  target 17.0 using the Xcode 27.2 Simulator SDK. The project plist lints.
  The Simulator differential and a run in Mixer's installed guest VM remain
  pending.

The host replay requires the standard Xcode Swift compiler, the Swift 6.3.3
release toolchain and WASI SDK installed at the paths in `replay.py`, and Node.
Each invocation prints its fresh `verification/local/swiftui-s3-*` directory.
The receipt contains the source hashes, commands and custody outcomes.
Successful runs remove executables, module caches, and temporary files. The
logs and receipt stay available for review.

## Runtime decisions

- Register state by the view path and the reflected backing field's label before
  evaluating the view body. A path incorporates child position and branch for
  structural children, and an integer key in place of position for a keyed
  row. Swift type identities are in-memory only. Renaming a declaration changes
  its slot.
- The subset refuses view types conforming to `CustomReflectable` during
  state discovery because a custom mirror can omit or rename backing fields.
  The key-path enumeration SPI is unavailable through the tested public Apple
  SDK and reported incomplete enumeration for a struct with a closure field
  on the pinned WASI toolchain.
- Give each candidate a private state snapshot. Registration keeps the slots
  present in the candidate, so accepting a frame that removes a branch also
  removes its state. Canceling that candidate keeps the accepted slots and
  handlers. Scope the captured binding's writes to the accepted callback turn.
- Publish the value-only document and closure table together on a matching
  feature epoch and frame acknowledgment. The presentation owner supplies a
  nonrepeating epoch across replacement and rollback, including when it
  recreates the runtime. Handler indices and frame numbers can repeat under a
  new epoch.
- The spike supports fresh struct view values, scalar `Int` and `Bool` state,
  synchronous serial turns, and the view forms in the shared screen. The packet
  is local to the experiment. Matching the UI wire schema, persistence across
  code releases, asynchronous effects, and the integrated presentation
  acknowledgment belong to subsequent work. Reflection depends on field
  metadata in the compiled profile.

## Root-owned Apple differential

Run the host replay first. Record the successful run directory as
`S3_HOST_RUN`. After the repository's public Accessibility preflight and
external-device baseline check, root selects a single owned iPhone Simulator
UUID and exports it as `S3_DEVICE`. Use a fresh directory and run this one
test with root's bounded command runner:

```sh
S3_EXPERIMENT="$PWD/compiler/experiments/swiftui-state-handlers"
S3_APPLE_RUN="$(mktemp -d "$PWD/verification/local/swiftui-s3-apple.XXXXXX")"
mkdir "$S3_APPLE_RUN/tmp"
TMPDIR="$S3_APPLE_RUN/tmp" xcodebuild test \
  -project "$S3_EXPERIMENT/AppleDifferential.xcodeproj" \
  -scheme AppleDifferential \
  -destination "platform=iOS Simulator,id=$S3_DEVICE" \
  -derivedDataPath "$S3_APPLE_RUN/derived" \
  -resultBundlePath "$S3_APPLE_RUN/differential.xcresult" \
  -parallel-testing-enabled NO \
  -only-testing:AppleDifferentialUITests/AppleUITests/testStateJourney \
  CODE_SIGNING_ALLOWED=NO COMPILER_INDEX_STORE_ENABLE=NO \
  >"$S3_APPLE_RUN/xcodebuild.log" 2>&1
```

Verify one passed test on the exact owned UUID in the summary and compare the
observed Apple attachment with the host trace:

```sh
xcrun xcresulttool get test-results summary \
  --path "$S3_APPLE_RUN/differential.xcresult" > "$S3_APPLE_RUN/summary.json"
xcrun xcresulttool export attachments \
  --path "$S3_APPLE_RUN/differential.xcresult" --output-path "$S3_APPLE_RUN/attachments"
python3 -B - "$S3_HOST_RUN" "$S3_APPLE_RUN" "$S3_DEVICE" <<'PY'
import json
from pathlib import Path
import sys

host, apple = map(Path, sys.argv[1:3])
summary = json.loads((apple / "summary.json").read_text())
assert summary["totalTestCount"] == summary["passedTests"] == 1
assert summary["failedTests"] == 0
assert {item["device"]["deviceId"].upper() for item in summary["devicesAndConfigurations"]} == {sys.argv[3].upper()}
attachment_directory = apple / "attachments"
manifest = json.loads((attachment_directory / "manifest.json").read_text())
traces = [
    attachment_directory / item["exportedFileName"]
    for test in manifest
    for item in test["attachments"]
    if item["suggestedHumanReadableName"].startswith("S3 Apple SwiftUI trace")
]
assert len(traces) == 1
expected = [line for line in (host / "s3n-run.log").read_text().splitlines()
            if line.startswith("s3 checkpoint ")]
assert len(expected) == 14
assert traces[0].read_text().splitlines() == expected
print("Apple SwiftUI matched all 14 host checkpoints.")
PY
```

The test taps the actual SwiftUI buttons and verifies rendered label order.
Mixer's presentation and rollback rules are covered by the host and WASI
controls. Record the OS, exact device, source revision, test result, and
cleanup. Retire only the owned Simulator and its settled disposable outputs
following repository rules.
