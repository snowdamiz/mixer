# Separate FieldLog remote host test proposal

Root-selected concrete preparation now exists in the separate local app:
`.github/workflows/host.yml` and `scripts/verify-host-ci.py`. Neither has executed.
The workflow is manual only. The runner has a750-second total budget and30-second
cleanup reserve under a13-minute workflow step; child output has one aggregate
32MiB bound. A pipe-gated launcher records and fsyncs its fresh PID/PGID before
admitting each command. Every exit retains logs/errors and requires direct-child
reaping, exact owned-group absence and pipe EOF; ambiguity stops further runs.
Collector or evidence-write failures cannot skip the owned cleanup path. App and
consumed public SDK sources/pins are checked, and an originHash-only lock refresh
is retained explicitly without reset/commit. Preparation was source reviewed and
`git diff --check` passed; no local syntax/compiler/process-control execution or
remote action was performed. All executable CI validation remains pending.

The separate app has **no Git remote**, no `.github/workflows`, and no additional
delivery instructions. Its `scripts/verify.sh` runs `swift test` followed by a
generic iOS Simulator source build. That script should not be used for this
host-only experiment. The README disclaims hosted CI execution. Connected GitHub
repository searches for `fieldlog user:snowdamiz` and installed `fieldlog` returned
no result on October 28. This is absence in the accessible search, not proof that
no differently named/private repository exists.

Current standing push authorization names `snowdamiz/mixer`. No FieldLog remote
creation, app push or hosted workflow dispatch has been performed or inferred.
Root must first select the separate app remote and authorize its delivery. Do not
copy app sources into Mixer or reuse the held local compiler attempt.

The smallest concrete change is one manual `workflow_dispatch` host workflow in
the selected FieldLog repository. Use one disposable `macos-15` runner and the
already used `/Applications/Xcode_26.3.app/Contents/Developer` selection, record its
actual Swift/Xcode versions, and run only the package's 26 expected host test
functions (17 existing plus9 new). Run one candidate once, with `--jobs 2`, a
15-minute job ceiling, a3-minute SDK-fetch step, an8-minute test step, and a
32MiB captured-output ceiling. The workflow's finalized runner-bound mechanism
must handle output/error/timeout cleanup; do not reuse the defective local draft.
The runner is remote and isolated; this does not resolve or inspect the original
local cleanup/identity hold.

Prepare a CI-private source-control mirror from the **exact existing public
commit**, with a depth-one fetch. This is a hypothesis to avoid the stalled
123123-object history fetch, not an observed result:

```sh
git init --bare "$RUNNER_TEMP/mixer.git"
git -C "$RUNNER_TEMP/mixer.git" -c protocol.version=2 fetch --no-tags --depth=1 \
  https://github.com/snowdamiz/mixer.git \
  d8c6965a277ca21e685f3ef9e0f68a7d59b46156:refs/heads/public-sdk-pin
git -C "$RUNNER_TEMP/mixer.git" symbolic-ref HEAD refs/heads/public-sdk-pin
test "$(git -C "$RUNNER_TEMP/mixer.git" rev-parse refs/heads/public-sdk-pin)" = \
  d8c6965a277ca21e685f3ef9e0f68a7d59b46156
swift package config set-mirror \
  --original https://github.com/snowdamiz/mixer.git \
  --mirror "file://$RUNNER_TEMP/mixer.git"
swift test --scratch-path "$RUNNER_TEMP/fieldlog-host" --jobs 2
```

The mirror command is supported by SwiftPM's public `SetMirror` interface:
[SwiftPM Config.swift](https://github.com/swiftlang/swift-package-manager/blob/main/Sources/Commands/PackageCommands/Config.swift).
The experiment records the actual selected compiler's help/version before use;
no local compiler/help command was run to prepare this proposal.

Do not change the app manifest URL/revision or either committed lock to a local
path. Keep mirror configuration transient and uncommitted. Before execution,
save the exact `Package.resolved` bytes and expected pin tuple; after execution,
require the pin identity/kind/public location/revision to remain identical and
report any byte change. The manifest changed only to add MixerUI product
consumption, so SwiftPM may refresh its `originHash`; that requires an explicit
record and root reconciliation rather than silently restoring/resetting a lock.
If the mirror changes identity/location or the depth-one fetch is insufficient,
stop the single candidate and report the failure; do not broaden to full history
or change the immutable pin automatically.

The receipt must bind the FieldLog commit/tree and six owned app source files,
the public SDK commit/tree, exact compiler/runner, full test counts and failures,
lock comparison, command timing/output hashes and remote run URL. Upload the
bounded log and receipt as a workflow artifact even on failure.

This establishes development host verification against public revision content
through a CI-private mirror if it passes. It is **not** a new immutable published
release-package qualification, iOS/Android runtime or visual/theme parity,
D0–D8, store/customer or GA acceptance. Generic iOS and Android cross-builds
remain separately selected follow-ups after host evidence and appropriate
resource authorization.
