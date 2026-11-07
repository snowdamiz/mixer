W02/W05 generated Java validation slice, 2026-11-07

Implemented `scripts/ci/check-android-generated-java.py` and its independent,
pure-Python control tests. This is a new proposal; the older PLAN wording did
not establish an installed or reviewed generated-Java job. The existing
`Generated consumer integration` workflow step creates the default iOS host.

The runner builds the actual CLI with SwiftPM separately in Debug and Release,
using fresh scratch paths and the committed resolution. Each actual CLI creates
an Android consumer with explicit SDK and adapter paths. Its original, physically
moved (old path removed), and CLI-exported consumers each compile all 18 product
Java sources against official SDK37 with Java bytecode17, strict lint, no annotation
processing, and no implicit source lookup. D8 runs with min-api28, and official
dexdump must report every emitted class descriptor. Classes and DEX are retained.

Before compilation, it checks every canonical SDK22/adapter24 member, both generic
source digests, exact source-pair lock, full toolchain lock, exact descriptor bytes,
closed source topology, rendered-driver profile and template bytes, and the whole
consumer file inventory. All six consumer file inventories must match. Directory
inventories are retained separately because the product exporter copies files and
can omit empty directories. Each producer's exported consumer also supplies six
negative cases to the actual CLI and actual generated Python driver: changed SDK,
adapter or descriptor bytes; extra Java source; stale profile; and missing lock.
The first four recompute generic locks to prove those locks cannot authorize
changed pinned inputs. Refusals must precede `.mixer` build staging.

Official tool verification reuses the canonical `android-build.py inspect` before
and after integration. Actual create performs its own real inspection; the runner
does not replace it. Dependency provenance reuses the existing CI checkout verifier
before and after each producer's consumer checks. Receipts bind the live owning
source map/digest, Git revision/tree, installed distribution/tool identities,
commands, bounded diagnostics, consumer inventories, source locks and output hashes.
The Git revision alone does not describe a dirty worktree; the source digest does.

Pure controls use only Python fake children and independently authored dummy
inputs. They prove runner selection/refusal/cleanup behavior, not toolchain or Java
correctness. All 26 controls passed both normally and with Python `-O`.
`pure-controls.json` records the actual command, interpreter identity,
source hashes, results and cleanup. No compiler, Java, Swift, rustup, device,
simulator, UI, capture, or pre-existing process was queried or executed by this lane.

Unrun integration command (parent chooses and executes; output must not exist):

```sh
python3 -B scripts/ci/check-android-generated-java.py \
  --swift "$MIXER_SWIFT" \
  --swift-sdks "$MIXER_SWIFT_SDKS_PATH" \
  --android-artifact "$MIXER_ANDROID_ARTIFACT_PATH" \
  --jdk "$MIXER_JDK" \
  --android-sdk "$ANDROID_HOME" \
  --output "$MIXER_GENERATED_JAVA_OUTPUT" \
  --execute-toolchains
```

All five tool inputs must be explicit absolute installed paths. The required
macOS distribution is official Swift6.3.3 with the full installed Android artifact
bundle/search path, `aarch64-unknown-linux-android28`, bundled NDKr27d
`27.3.13750724` with `darwin-x86_64` tools, JDK25, Android platform `android-37.0`
(metadata API `37.0`) and build-tools `37.0.0` including D8 and dexdump. The canonical
inspection additionally requires the full runtime, metadata, clang/readelf/nm,
aapt2 and zipalign closure. Platform-only installation cannot satisfy create.
SwiftPM needs the existing pinned official Apple swift-crypto/swift-asn1 checkouts
or network access to resolve those exact existing dependencies. No new dependency
or competitor source is introduced. The runner sets the matching tool environment
and puts child temporary state under its private scratch directory.

Execution is sequential, with no retries: at most 160 commands, 600 seconds per
command, 2,400 seconds across child execution, 4 MiB per output stream per command
and 64 MiB total captured output. On failure or completion it closes/kills only
process groups it created and removes only its unique scratch subtree. Logs,
partial classes/DEX and failure receipts remain under the requested output path.
These are diagnostic ceilings, not product performance limits. A machine should
reserve space for two fresh SwiftPM builds and their dependency checkouts.

`workflow-proposal.yml` is an exact proposed job block under `jobs:`; it has not
been installed. Do not install it until a real worker supplies the documented
toolchain and configured absolute path variables. The current hosted jobs do not
demonstrate that prerequisite. The parent is evaluating an isolated local build
path following the user's runtime resumption; this sub-agent has not selected or
executed that path. A real local receipt may close generated-Java integration
before CI provisioning is ready.

Fresh independent root review, real six-consumer compilation, real refusals and
toolchain identity postflight remain pending. CLI Debug/Release names refer only
to producers. The shipped Android APK driver is Release-only; this runner never
builds an APK and makes no Debug APK, native runtime, API28 device compatibility,
linkage, simulator/device, signing, immutable published-package, FieldLog or GA
qualification claim. No workflow, product source, pair lock, status/graph/gate,
commit, push or CI dispatch was changed by this lane.
