Independent generated Java runner review, round 2, November 7, 2026.

Verdict: ACCEPT for the parent-owned real six-consumer integration. No blocking
defect remains from this review. No further preparation round is requested.
This acceptance concerns the reviewed runner and its Python controls. Actual
Swift, javac, javap, D8, dexdump, native, runtime, and device execution did not
occur in this review. Concurrent parent execution is outside this receipt.

The runner SHA256 is
`5c854f3888a1fb63d1aee02172cd5adae73b181436bf4d266ba356bedc5b968e`.
The supplied test SHA256 is
`22ac0a13c395b428c4ebec0095f21195a3e57b632a15ff379ca8a2fe2fa39baf`.
Both match the correction receipt. All 51 reviewed input identities remained
unchanged, including the source-pair.7 policy and its SDK22/adapter24 projections.
The Git revision/tree identifies the committed baseline; these explicit file
identities describe the reviewed shared sources. Exact inclusive line-range
hashes are retained in `verification.json` and `receipt.json`.

The prior findings are resolved:

- GJ-R1, prior P1. `scripts/ci/check-android-generated-java.py:177-332` retains
  PID, created PGID, child reap, separate stream EOF observations, signal result,
  bounded group absence, and each cleanup error. Signal, wait, drain, stream
  close, selector close, and persistence errors cannot make a command pass.
  Stream and selector closure are attempted independently after nested errors.
  Denied command-receipt writes retain in-memory records for the outer receipt.
  Lines 174-180 prevent another command after unknown custody. Lines 607-630
  preserve scratch and fail on unknown custody or cleanup error. Ordinary
  compiler failure can remove owned scratch after positive terminal evidence.
  The normal and optimized suites exercise all these branches. Independent
  controls additionally observed closed pipes and selector after injected nested
  failures, bounded return from a live-child signal denial, retained diagnostics,
  and rejection of a follow-up spawn. Only newly created Python child groups
  were observed or signalled. The denial control's harness killed and reaped its
  own child after injection ended, closed its streams, and observed group absence.

- GJ-R2, prior P2. Lines 549-559 share the explicit `-j 2` flags for both producer
  builds and their bin-path queries, and record the job selection. Independent
  fake-boundary execution reached both Debug and Release builds, checked each
  actual selected argv, and reached the original, relocated, and exported forms
  in order for each. Relocation removed the original path before that form ran.
  The existing 160-command, 600-second command, and 2,400-second execution
  budgets remain selected. Cleanup retains its separate five-second cap per
  command. No real compiler resource calibration is claimed.

- GJ-R3, prior P2. Lines 335-402 select official `javap -v -p -c -s` for every
  emitted classfile, parse actual-output class scopes and member entries, and
  bind raw output, exact command, class input identities, member inventory,
  output hashes, and scope. The parser rejects missing, duplicate, or unexpected
  class scopes and unscoped or unresolved member entries. Executed controls
  cover missing, duplicate, unscoped, and unresolved input. Lines 470-475, 534-537,
  and 601-603 require javap and retain/check its identity and version before and
  after execution. An independent fake compile boundary copied all 18 real
  product Java inputs and supplied 19 explicitly fake emitted classfiles,
  including an extra nested class. The actual runner selected every class for
  javap and D8 and retained all 57 fake member entries and matching output hashes.
  This proves Python selection and receipt behavior, not real tool compatibility.

Member-reference scope is honest. The extracted inventory covers pre-D8 classfile
constant-pool Fieldref, Methodref, and InterfaceMethodref entries, including unused
entries. Raw verbose disassembly is retained. Dynamic/reflection resolution,
post-D8 rewrites, and API28 linkage qualification remain outside that observation.
The real run must establish that the installed official javap output is accepted.

No prior source-admission control was removed. All 26 earlier test names remain
in the 40-test suite. The actual integration path still calls the SwiftPM-built
CLI for create and export, validates the complete generated inventory, compares
all six consumers, and invokes canonical inspection before and after integration.
All 18 product Java sources are selected unchanged for strict Java17 compilation
against SDK37 and D8 min-api28. The exact pair lock, SDK/adapter digests, descriptor,
closed topology, rendered driver, toolchain lock, and source-stability checks remain.
The six tamper cases per producer still use its exported consumer. CLI and copied
driver refusals require their named diagnostics and no `.mixer` staging. The first
four cases recompute generic tree locks. Wrong refusals, missing Java, extra Java,
descriptor drift, source drift, symlinks, and changed driver/profile/toolchain inputs
remain rejected by the executed Python controls.

Verification passed 40 supplied tests normally and 40 with Python `-O`, plus seven
independent controls in each mode. Exact interpreter identity, argv, timeout,
stdout/stderr logs, hashes, and observed cleanup are retained. Each control process
had a 55-second bound. One initial independent run failed because this review's
mock validator returned a placeholder inventory instead of the fake fixture's
actual inventory. The corrected harness passed. The initial normal and optimized
logs, command receipts, facts, and correction explanation remain preserved.

All review temporary directories were removed. The original 14 sealed evidence
files and all seven correction evidence files retained their inventories and byte
hashes. No source, production input, tracker, gate, workflow, commit, push, merge,
child agent, physical device, old process, held v5 startup, or hosted lane changed
through this review. An initial read-only Git status command exceeded its
15-second timeout and its newly created child was killed/reaped by subprocess.run.
The baseline records that setup diagnostic and a corrected descriptor lookup.

The parent can proceed directly with its existing bounded actual integration,
using the full installed official toolchain, these frozen source identities,
and a fresh output path. The executable command and prerequisites are already in
`../generated-java-fix-r2/IMPLEMENTATION.md`. Actual generation, all six real
compiler/D8 closures, real member observation, real tamper refusals, and toolchain
postflight require that run's evidence. This review grants no APK, API28 floor,
runtime, signing, immutable published-package, separate-repository FieldLog,
physical-device, release, or GA qualification.
