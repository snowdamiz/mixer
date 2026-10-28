# Root-bound work/storage layout diagnostic preparation

This packet prepares exactly one compiler-only diagnostic query. **The compiler
slot has not been released and no compiler, version command, strategy probe,
product/host/native runtime, UI/capture, network or physical phone run occurred.**
The packet is ready for independent source/offline review and a separate root
internal release. Intentional rustc exit 1 can supply diagnostic evidence only;
it never qualifies a successful product compile, metadata build or runtime.

The original 146-member source tree is exactly the accepted IR02 tree
`91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f`.
All original members were read and hashed. The retained diagnostic 146-member
tree is `2ec0d8555d6a18d7c8222984faaec3a1543c1a1b800f4b90381f70571215516e`.
The two named-query fragments and actual closure fragment are copied byte for
byte from the accepted proposal. There are exactly three edits in two files:
the owner named-query insertion, cache named-query insertion and original inline
dispatch-expression replacement. Reverse replay recovers every original byte.
`original-source-manifest.json`, `diagnostic-source-manifest.json`,
`exact-three-edit-delta.json` and its patch record this custody.

The producer seal is
`1b077039023f424fb72f9e32902f329e3257edb50a4ab99aa42192149271cb29`;
the independent seal is
`addd2beb80ae25174c210563bffc9122cbe655f69420170ad16305eaeef544ec`.
Their complete members, accepted root receipt and proposal were read. This lane
does not modify those packets, canonical source, central metadata, prior prices,
hosted work, Android v5 or callback Unit A work. No global process inventory ran.

## Frozen command and tool custody

`plan.json` contains the exact argv and complete replacement environment. They
match the accepted proposal without added flags, environment bindings, feature
configuration or commands. The compiler executable is
`/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc`,
SHA256 `dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0`.
The retained identity is rustc 1.99.0, commit
`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, LLVM 23.1.1,
aarch64-apple-darwin. That version text comes from the already accepted IR02
toolchain receipt; this lane starts no fresh version command. Fresh offline
hashes pin rustc, direct compiler dylibs and every file in the direct target
sysroot library directory. SDK path resolution/settings and the exact Python
executable/version are pinned separately. SDK settings are path evidence, not
SDK implementation or native qualification.

The single rustc argv is retained as JSON in `plan.json`; its final arguments
are `--error-format=json` and the one metadata destination
`build/layout-proposal.rmeta`. There is no link, executable, test runner,
full-MIR output or strategy-probe command.

## Conditional diagnostic policy

The exact expected primary diagnostic set is 56 E0308 errors for 28 named
size/alignment pairs and two E0512 errors for the actual anonymous closure.
`diagnostics.py` requires the named primary spans to bind to the exact frozen
macro expression and their expansion to exactly one concrete pair invocation.
Every displayed source line, physical byte/line/column coordinate and expansion
span must match the frozen source. Type spelling and invocation identity come
from the explicit proposal roster; rendered text never authorizes a query.

The actual closure remains
`|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)` and therefore
keeps fixture and attempt by value and expected by shared reference. Both
concrete E0512 source types must name this exact closure's physical `||` token
span: one `MaybeUninit<actual closure>`, one
`ClosureAlignmentProbeV1<MaybeUninit<same actual closure>>`. Both target types
must be `[u8; 0]` with zero bits. Source bit sizes must be concrete. For positive
closure size S and leading-byte repr(C) wrapper size P, only byte-multiple
observations with positive power-of-two A=P-S and S divisible by A are accepted.
There is no proxy capture sum or assumed numerical layout.

This diagnostic emission and formatting strategy has not been qualified. A
different compiler identity spelling/endpoint or primary-span shape, missing,
duplicate, ambiguous, dependently-sized or unexpected diagnostic refuses the
observation and requires a separately reviewed correction. Warnings are retained
and rejected; no inferred warning allowlist is supplied. Only three explicitly
frozen rustc summary messages are permitted, with no spans or children. Unexpected
child notes also reject. No automatic retry follows rejection.

The first unreleased draft permitted a closure identity endpoint inside the
complete expression. Self-review narrowed that condition to the exact physical
`||` span before final sealing. `pre-seal-draft-01/` preserves its original plan,
preparation receipt and 27-control result. The final synthetic control set adds
an adverse endpoint mutation. Source146, the exact three edits, argv and
environment did not change. No compiler was used to choose the endpoint; a real
diagnostic with different formatting must therefore fail closed.

## Runner bounds and cleanup

`run.py` requires the exact plan SHA256 and a root-written release receipt at
`verification/swift-semantic-adapter-root-review/root-bound-work-storage-layout-release.json`.
The release must name this plan SHA256, `compiler_lane_released: true` and
`compiler_invocations: 1`; its exact file SHA256 is a second required argument.
Write-once `command/` evidence prevents replay. Preparation grants no release.

The elapsed budget starts before preflight. Work is limited to 44 seconds;
cleanup has a deadline at 49 seconds, posthashes and bounded artifact handling
at 53.5 seconds, and the complete receipt is required below 55 seconds. Work
alarms and all caught failure paths enter owned cleanup. Popen is assigned before
any evidence or pipe setup. Output is streamed through nonblocking bounded
capture: stdout at most 1,048,576 bytes, stderr at most 2,097,152 bytes. Overflow,
timeout, spawn/evidence/pipe/wait/hash/parser failure all refuse acceptance.

Cleanup signals and waits only the exact owned compiler process group/PID.
An exact waitpid fallback handles a failing wait. The receipt separately records
direct-child reaping, exact PID absence and exact process-group absence. It
never enumerates other processes. Generated build artifacts are inventoried,
hashed and deleted only after all three ownership conditions hold, with at
most 64 entries and 16,777,216 bytes. Any ambiguous entry, symlink, process state
or exhausted deadline preserves scratch and records rejection. The frozen
diagnostic source146 remains available for review. Unexpected metadata is
recorded and rejects the failed query even after owned artifact cleanup.

`check.py` verifies original/diagnostic146, the exact edit replay, frozen inputs,
toolchain and environment without child processes. `controls.py` uses wholly
synthetic diagnostics and fake process operations. Its parser positives are
arbitrary fixtures, never product layouts. The controls reject missing/duplicate
errors, bad source/expansion/type/closure identity, unexpected diagnostics,
dependently-sized or invalid arithmetic; they exercise no-spawn, reaped,
wait-failure/fallback, unreaped/present and ambiguous-absence cleanup states.
`verify_and_seal.py` runs those offline checks in-process, retains command/tool/
source/output custody, and freezes packet membership. It starts no child.

## Acceptance boundary

All actual target layouts remain pending. All work/storage prices, standard
library/drop/unwind costs, original source/proof/File/io-error/cancellation/
setup/leaf backing, simultaneous lifetimes/peaks, root/child funding partitions,
durable forgotten-result/root funding, useful retirement, full ownership,
native behavior, production selector/startup/allocator/custody/healthy close,
immutable external FieldLog packages, OTA and GA remain pending. The user-paused
native/UI/capture/phone matrix remains pending. No bytes, prices or funding
conclusions are inferred from source counts, synthetic controls or this plan.
