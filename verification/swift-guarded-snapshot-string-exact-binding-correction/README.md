# Exact authored binding and typed header correction candidate

This separate implementation packet addresses S1–S5 in the binding correction
contract `e8c3364612e7e9f90b9da0456d54c1c806968474676b0efe6b5c038309976974`
and root return `9dba765988b0e464fe58245520586696945e9f4bbd87f1ca2b8bc4051cf68440`.
It is a source146 candidate for fresh independent review and root selection.
No L_str, complete source proof, P0 caller, whole-host budget, policy, account,
operational authority, OTA release or GA gate is selected here.

`mir_graph.py` now resolves an exact complete definition name first. Otherwise
it uses `authored-contracts.json`: 423 explicit complete target identities,
434 direct argument/result signatures, four named function-item signatures and
the exact closure-adapter contracts. An absent namespace, receiver, trait,
member or generic instantiation has no short-name fallback. Foreign Fault,
Policy, SharedControlV1 and MeterControl cases refuse. Multiple compiler bodies
for the two enum constructors remain distinct. Contracts identify source owner
declarations and complete headers; they contain no body-hash waiver.

`prepare_authored.py` uses the old frozen independent edge roster only for
membership. It reparses the actual source146 MIR and checks every positional
argument/result against the destination declaration using `type_contracts.py`.
All 323 nonidentical type pairs unify through explicit exact path aliases,
selected B/B::Access/P/C/D specializations, consistent T/R/N substitutions,
reviewed typed constants, and the two actual Fn callback implementations.
The complete per-signature equations and solved substitutions are retained.
These finite aliases were reviewed against the source owner declarations,
the full 423-target roster and compiler type spellings. They do not authorize
another target by a familiar basename or authorize arbitrary instantiations.
The frozen catalog is a reviewable interface contract, not a general Rust
trait solver. A new alias, type signature or instantiation needs new review.

Every authored call now checks arity, its exact reviewed signature and structural
type compatibility before expansion. Exact authored definitions precede external
classification but still receive typed checks. Named callback function-item
parameters/results are checked against their authored declarations. Closure
adapters bind the full outer identity and typed arguments/result plus each
closure's exact receiver/parameter/result declaration. Destination `_0`
compiler declarations are also bound. The existing exact external catalog
remains 1,127 targets / 1,130 signatures / 3,209 call sites.

Header parsing balances the outer parameter list and validates the full nested
type delimiters. Fn/FnMut/FnOnce arrows cannot terminate the enclosing signature.
`typed-header-inventory.json` contains params, returns and local types for all
2,009 bodies. The independent lexer in `audit.py` agrees with all current types
and full selected statements. The complete nine-header historical discrepancy
roster remains recorded: f0907, f1257, f1258, f1297, f1298, f1299, f1300, f1319,
f1405. The selected f0907 callback is `impl FnOnce() -> T` with return
`PrepaidOwnedV1<'_, T>`; f1405's callback is
`impl FnMut(&[u8]) -> io::Result<usize>` with return
`Result<diagnostic_profile::ProfileRowsObservationV1, diagnostic_profile::ProfileAdapterErrorV1>`.

The rederived graph retains all 525 selected bodies and 1,908 edges: the original
1,879 edges, 28 named edges at 22 sites and f1605→f1697. Both exact standard
Option predicates remain. All 80 primitive str assignments remain: 24 literals,
54 reference/field transfers, two authored policy returns. The complete
statement, nested aggregate, incoming port, failure/error latch, return,
retirement and Drop evidence is rederived. All nine direct ports and 257 direct
and nested carrier ports remain. `source-semantic-review.json` rebinds actual
source excerpts and critical complete MIR bodies to the corrected inventory.

The private fixture contains paths, byte claims and scalar budgets. The exact
selected loader proof is forwarded unmodified; cancellation/control start
fresh with no failure or cleanup latch. The validator constructs Policy::swift.
There is no incoming arbitrary str/Fault/failure, custom callback or intervening
mutation in this caller contract. Policy::Frozen(&Limits) contains scalar/profile
limits and is a control dependency, not a fabricated str field. Alternate
callers remain open. Path/OsStr and io::Error backing remain separate native
allowances. The 5,080-byte envelope remains a candidate from 1,958 allocation
occurrences / 1,464 IDs / zero unresolved IDs and 3,189 literal occurrences /
1,397 unique values / maximum literal extent 92 bytes. Lifetime, pointer width,
claimed length, finite catalog membership and syntax analysis supply no release
authority.

The original 14 methods, first correction's 16 methods, prior independent 17
adverse expectations and 17 new exact-binding methods run against this candidate.
The new controls include 12 full-MIR negatives covering every finding, a missing
argument, changed argument, nested result, unknown/changed named callback and
changed closure header. Other controls check every one of the 423 identities
and all 434 direct signatures, complete nested Fn/tuple/array syntax and all
2,009 corrected headers. Full-MIR groups run in separate bounded children.

All four old packets are rehashed with complete membership checks: original
producer b228f62… (114 / 6,305,257), original independent 741e104…
(108 / 6,581,268), first correction 4d2dcab… (358 / 56,817,849), second
independent 7c101623… (248 / 6,817,047). Their failures remain failed.
`history/` copies original producer 006/007, old independent adverse006, all nine
failed first-correction attempts and every failed second-independent attempt.
Current failed preparation and test-harness attempts remain under `commands/`.
Attempt 011's recorder incorrectly considered this packet's mutable catalog a
frozen input after a successful preparation child; its incomplete original
files and truthful failed-recorder supplement remain. No passing receipt was
fabricated. The corrected recorder checks external frozen inputs separately
from its own candidate catalogs. Initial reads/edits are preparation, not
qualifying receipts; the seal lists only final passes against the same scripts.

All qualifying commands go through this packet's `run.py`, which snapshots
scripts, records Python version/executable digest, exact argv/environment,
source/host identity, output and exit code, and external frozen input inventories
before/after. Children have a 55-second limit and their own process group.
Only an owned group would be killed on timeout, then waited. No timeout occurred.
No compiler, provider execution, product runtime, native simulator/emulator,
phone, UI/capture, Git action or global process inventory was used. Only this
directory was written. Other projects' processes/data were preserved; no native
instance was created. Native/device, compiler/session/executable correspondence
and actual immutable published P0 package checks remain pending. The future
outer 27deef candidate requires a separate rebind.

After sealing use read-only commands directly, with `-B`, never the recorder,
preparation writers or freeze helper:

```sh
python3 -B verification/swift-guarded-snapshot-string-exact-binding-correction/seal_check.py
python3 -B verification/swift-guarded-snapshot-string-exact-binding-correction/check.py
python3 -B verification/swift-guarded-snapshot-string-exact-binding-correction/prepare_authored.py --check
python3 -B verification/swift-guarded-snapshot-string-exact-binding-correction/prepare_contracts.py --check
python3 -B verification/swift-guarded-snapshot-string-exact-binding-correction/audit.py --check
python3 -B verification/swift-guarded-snapshot-string-exact-binding-correction/custody.py --check
python3 -B verification/swift-guarded-snapshot-string-exact-binding-correction/report.py --check
```

The test scripts are also read-only. `test_exact_binding.py` accepts `syntax`,
`identity`, `receiver`, `types`, `callbacks`; run each group separately.
