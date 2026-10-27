# Private outer parent source candidate

The candidate supplies an actual consuming Rust outer path inside the existing
private `trusted_local_host_account_entry_v1` module. It is a source proposal for
independent review. The root policy, whole quote and new immutable binding
selectors all remain Pending. No fixture, loader, VM, cache, writer, destructor,
native test, UI or capture runtime ran.

The 146-member distribution changes one file by inserting a private module
before its final closing brace. Every pre-existing declaration/body byte is
preserved; the other 145 members are exact. The original tree is
`690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185`;
the new tree is
`27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3`.
The profile file changes from 49,980 bytes, SHA256
`04c5e5895586f5270c3d2bcaeaa1cfa451872d75b5b9260dbf3a1c9beb7d5876`,
to 61,144 bytes, SHA256
`b19bca0a2f5ad193fc782061a2f345bd75b9414408643823b8f7691c89bc150f`.
`outer-parent.inc.rs`, `source-delta.patch`, the candidate overlay and complete
old source custody expose that exact inline addition. The authored snippet is
inlined, so it does not add a 147th distribution member or alter the frozen
loader's 146-member check.

`run_selected_one_fixture_outer_v1` selects a private affine request and passes
it to `consume_outer_request_v1`. The latter selects the account, captures its
original pre-entry usage, consumes one frozen fixture and retains the complete
returned wrapper. It records usage while the originals remain held, observes
one scoped typed shared view, consumes the full wrapper through
`destroy_returned_fixture_v1`, and releases exactly once on the returned
destruction token. The final usage snapshot follows token handling. A missing
token or unwind cannot reach a release. The resulting finite observation and
usage copies live in separately funded P0; they claim no healthy File
close/flush, operational cleanup or admission authority.

The actual finite ceilings are `I <= 1`, `U <= 3`. Entry refusal has `I=0,U=2`;
binding/account refusal has neither call. This substitutes 2,825,436 into the
prior conditional account-surface expression
`2628088 + 194231*I + 1039*U`. That is only the old account component with
these occurrence ceilings. The new outer work, complete P0 storage/lifetime
overlap, actual binding/path/identity backing and root policy still require
independent pricing/rebinding; no complete host quote or grant follows.

`contracts.json` gives each exact parameter obligation. `owner-roster.json`
lists the pre-existing P0 policy/account/binding, twelve immutable identity
preimages, five native path pointees, original File/cancellation/claim owners,
all original primary/retirement/error diagnostic categories, shared observation
views and late token/result places. The eventual producer must inject actual
immutable identities and paths. The selected existing 1,947-byte Wasm and
five narrowed original validator limits are retained as constraints; no fresh
build, session, executable, compiler-process or claim identity is invented.
Static lifetimes and digest fields supply neither backing bounds nor authority.
The native/dynamic whole binding remains pending actual selection and review.

Twelve Python test methods pass. They exercise 14 synthetic original-kind/token
routes and reject premature release/token production, owner destruction during
a borrow, repeated dispatch/inspection/token/release, excess snapshots and
unwind refunds. Separate data checks preserve all old bytes, private scope and
the full selected source digest. These are pure control/ownership models and
source invariants, not genuine I/O, release qualification or numeric pricing.
The two new Rust unit tests are written but were neither compiled under test
configuration nor executed.

One approved compiler-only metadata/MIR/layout context ran with the exact
installed Rust 1.99.0 compiler, whose executable was freshly rehashed. Query
instrumentation consists only of two inert size/alignment parameter-array
functions appended to copied private modules. Query tree
`11dd778041d13911e656138e75fc3fb3977808afb7e74ec2117b82e1e5709aa4`
is distinct from the candidate distribution. It injected no loader compile
identity and ran no tests or product code. The query emitted 25,621,814 bytes
of metadata and 82,162,472 bytes of MIR; stdout/stderr were empty. Seven exact
outer/query MIR bodies and 44 concrete layout observations were retained.
Whole `ReviewedFixtureBindingV1` is observed as 512 bytes/alignment 8;
`PreexistingImmutableBindingV1` is 1,168; the borrowed view/Option are 56/64;
`OuterResultV1` is 80. These inline observations do not bound pointee backing.

The original receipt writer then failed because a keyword was duplicated after
`Popen.communicate()` returned. Its exact source and failure are preserved.
The compiler exit code, elapsed time and process-group identity/absence were
not retained and remain unknown. Artifact existence is not treated as a
terminal compiler pass. Recovery invoked no compiler. The known child was
waited by `communicate`; owned source/MIR/metadata scratch was removed after
extracting exact surviving evidence. No global process discovery occurred.
`compile_once.py` was corrected, but its existing output guard prevents a
retry. Another compiler context requires root coordination.

`outer-mir-inventory.json` records five new functions, 130 typed roles, 386
written operations and 43 acyclic direct terminal paths, including cleanup and
unwind alternatives. It independently derives the occurrence ceilings and
release-after-destruction-call ordering from retained compiler MIR. The raw
operation/role inventory is unpriced; old accepted work/storage packets remain
separate. LLVM output and retained generic standard-library binary bodies were
not requested in this bounded context.

All changes are confined to this lane. No canonical metadata, frozen input,
other lane, Git state or production state was mutated. No native/product
process or instance started. Remaining gates include independent review,
terminal compiler receipt, new outer work/storage, complete actual immutable
binding geometry/backing/identity, original simultaneous error owners,
transitive destructor temporaries, native request bounds, full compiled
correspondence, actual loader/writer/destructor/healthy cleanup and final native
acceptance under the user pause. FieldLog, OTA and GA remain separate.

Read-only reproduction after freeze:

```text
python3 verification/swift-guarded-snapshot-outer-parent-source/prepare.py --check-only
python3 verification/swift-guarded-snapshot-outer-parent-source/test_model.py
python3 verification/swift-guarded-snapshot-outer-parent-source/inventory_mir.py --check-only
python3 verification/swift-guarded-snapshot-outer-parent-source/freeze.py --check-only
```
