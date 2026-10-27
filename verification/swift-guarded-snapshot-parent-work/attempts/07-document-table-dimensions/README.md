# Private P0 parent-account source work proposal

This packet proposes a bounded component for the exact frozen private account
and typed entry, using existing MIR and compiler layout diagnostics as data.
It executes only Python finite arithmetic, source data reconciliation, and
bounded control-flow models. It does not select a root policy or grant.

The candidate one-fixture surface is:

`W_P0_account_surface = 2,628,088 + 194,231 * I + 1,039 * U`

`I` is the number of inspections and `U` the number of usage observations.
Both remain unknown until an exact root route fixes their finite occurrence
bounds. Neither defaults to zero. A function name, a historical fixture, or
successful arithmetic cannot establish those bounds. No finite operational
grant is available from this expression as it stands.

The fixed term comprises 416,998 abstract source action units and a 2,211,090
native-sized occurrence-byte allowance. Its MIR portion is 2,496,754 combined
units; the additional finite primitive destruction boundary allowance is
131,334. These are conservative, reproducible arithmetic components, not
optimizer estimates or observed CPU work.

## Exact source and input custody

The source is the accepted funding144 tree plus its separately frozen
bootstrap leaf, private account include, and typed entry: 145 members, tree
`5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b`.
It is distinct from combined145. The checker reconstructs every member and
the exact manifest digest without creating a checkout or invoking Git.
The producer seal is
`6e8c8e2d8dde62e2e35fe2e8fb1a851a342d8d95f8c71facd938416ac3e153e3`
(136 members, 3,432,402 bytes). The accepted independent inventory seal is
`a41ff779d707d246997ddcbb36d5b157edc1d6fc01be27b6f80dc210e3cf2295`
(9 members, 129,818 bytes). Both member closures are rehashed.

The root selection and accepted host-account receipt are independently
hash-bound in `input-custody.json`. The selected future historical 1,947-byte
fixture is recorded only as a separate future input. This component does
not inherit its executable, session, process, or launch authority. Final
source146 composition and every changed root/constructor/quote/caller body
require source, layout, ownership, cost, tool, fixture, and identity rebinding.

## Cost rule and operation table

The inherited unit counts abstract product source operations/calls and
explicit native bytes. Every MIR operation, control transfer, and lifetime
marker gets two action units, plus a superset of projection punctuation.
Every parameter at entry, local operand or destination mention, constant,
and implicit return pays fetch/store for its concrete scalar leaves. A
struct/tuple sums fields, an enum counts one tag plus the largest inhabited
payload, and fixed arrays multiply cardinality. Opaque standard resources,
unit, and never places count as one primitive source place. Every written
variant/failure/cleanup block is also retained in the operation sum.

The separate native allowance charges twice the full compiler-measured base
extent per operand/destination occurrence. Reference uses additionally pay
the full actual pointee extent and scalar leaves, even for a projected
read. For example, inspecting the owned option pays its 13,608-byte extent,
not merely the 8-byte reference. This is a conservative logical work
allowance; it does not assert a physical byte copy or request that much
storage. The full carrier is charged again when moved into another place.
No alias, move, disjoint alternative, or optimizer discount is applied.

All 15 P0 functions, 208 roles, and 234,375 logical source-object inventory
bytes reconcile to the accepted evidence. A finite shape reader records 54
transitive concrete product data declarations. The actual payload has 2,556
scalar leaves in its largest source-visible variant and measures 13,608
bytes; the wrapper has 2,560 leaves and measures 13,624 bytes. Every measured
P0 base and pointee extent covers its concrete leaf count. Unknown types or
callees refuse rather than receive a zero cost.

| P0 body | Source actions | Native occurrence bytes | Combined units |
| --- | ---: | ---: | ---: |
| Checked six-part quote | 4,475 | 42,066 | 46,541 |
| Pending selected quote | 78 | 192 | 270 |
| Pending selected account | 138 | 640 | 778 |
| Account from pre-existing root | 391 | 2,272 | 2,663 |
| Usage, per `U` | 239 | 800 | 1,039 |
| Reserve whole quote | 2,864 | 6,850 | 9,714 |
| Dispatch carrier | 72,665 | 380,592 | 453,257 |
| Inspection, per `I` | 30,743 | 163,488 | 194,231 |
| Explicit owned destruction | 135,730 | 706,596 | 842,326 |
| Ordinary wrapper Drop | 98,303 | 516,316 | 614,619 |
| Destroyed token release | 841 | 2,362 | 3,203 |
| Typed one-fixture entry | 44,300 | 219,730 | 264,030 |
| Exact dispatch closure | 10,331 | 54,456 | 64,787 |
| Typed destroy adapter | 30,818 | 163,488 | 194,306 |
| Typed release adapter | 82 | 178 | 260 |

`summary.json` and `operation-ledger.json` are the authoritative generated
tables; each operation retains its source MIR body identity, operands,
concrete types, counts, native extents, and callee cut. Each non-symbolic body
is charged at most once in the candidate envelope. Including both pending
constructors and currently unreachable success arms is conservative; it
does not make a future selected implementation match this source.

The quote iterator has at most six yielded components and seven `next`
calls. Each body iteration is charged at most six times. Remaining normal,
refusal, drop, and cleanup blocks are charged once per invocation. The
checker proves all other body graphs acyclic and enumerates 273 bounded
terminal paths, including written unwind exits. The source has no arbitrary
policy callback or retry loop in this component.

## Destruction and phase ownership

`drop-surface.json` closes the source-visible wrapper, optional ticket,
token, fixture/closure, and Cost-array destruction bookkeeping. It lists
ten additional per-operation field/control allowances at exact measured
carrier extents. Private standard-library and compiler-lowering instruction
sequences are outside the inherited logical unit, as are kernel and
allocator implementation work and retries. They are not unidentified
in-unit costs silently assigned zero.

The only authored production P0 destructor is `PrepaidOwnedV1::drop`, whose
complete body is charged once. Explicit wrapper destruction, cleanup, and
ordinary Drop are alternative ways to reach that hook. Its `owned.take()`
sets the owned option to None before invoking a payload destructor. Thus
normal or payload-unwind field finalization cannot invoke that payload a
second time. Remaining ticket fields are an account reference and `u64`;
they have no authored destructor or refund behavior. Token discard also
retains the account charge. The six Cost elements contain Copy scalar
fields, so iterator destruction invokes no authored product destructor.
Historical accepted debug/optimized Drop/unwind tests are rebound as input
data and were not rerun here.

The actual payload destructor body, transitive File/error/cancellation
owners, and diagnostic backing remain a separately required, nonzero P5
term. Its maximum is one actual payload destruction per one-fixture route;
the written call-site union conservatively retains both explicit and
ordinary Drop sites. P0 field/carrier bookkeeping charges do not price that
P5 body. File destruction is not successful close, flush, or durability.

All quote construction, root/account fields, reservation calls, dispatch
carrier, inspection, return adapters, destruction frames, token places,
and release bookkeeping belong to pre-existing P0. They must be funded
before any child grant. Returning a token does not retroactively fund their
work or storage. Work is never refunded. Ordinary Drop, callback/payload
unwind, unused reservations, discarded tokens, and inconsistent storage
subtraction retain conservative storage charges. Only successful explicit
destruction followed by token release may reduce that child's storage;
work and peak storage are preserved.

## Required cut interface

`cost-interface.json` lists the remaining terms. A complete expression must
add the newly selected trusted root/quote/constructor/caller route, bounded
`I`/`U`, immutable fixture binding/backing, and all eventual P0 dynamic/native
backing work. The exact P0 storage allocation remains unknown: the
234,375-byte source-object sum is not a storage, stack, RSS, allocator, or
simultaneous-lifetime bound.

The six child components remain explicit: P1 setup; P1 loader including
original validation; P2 arguments; P3 pre-store shell; P4 selected route;
P5 returned owners and destruction. The last composes separately explicit
returned-carrier and actual payload-destruction terms with checked addition.
The callback body is outside this P0 surface. No child component, destructor,
root, or backing omission can become zero. Every addition and multiplication
must fit `u64`; unknown terms or occurrence counts and overflow fail closed.
Arithmetically summing six arbitrary positive numbers establishes no
evidence, authority, or runtime permission.

The two selected production constructors still return `WholeQuotePending`
and `RootPolicyPending`. This packet is not complete P0 work/allocation,
complete host quote, fixture qualification, operational authority, canonical
integration, native runtime, OTA, FieldLog, customer, or GA acceptance.

## Reproduction and preserved attempts

The command receipt records Python 3.14.8, the command, driver hash, exact
source tree, stdout/stderr hashes, and scope. The model passes 4,549 finite
checks, including independent state/ownership and CFG controls, six-part
quote failures, arithmetic overflow, missing/zero/unknown costs and counts,
source-rebinding refusal, and concrete underpricing countermodels.

Before sealing, the recorded commands are:

```text
python3 verification/swift-guarded-snapshot-parent-work/run.py
python3 verification/swift-guarded-snapshot-parent-work/run.py check-only
python3 verification/swift-guarded-snapshot-parent-work/freeze.py
```

After sealing, use read-only checks:

```text
python3 verification/swift-guarded-snapshot-parent-work/derive.py --check-only
python3 verification/swift-guarded-snapshot-parent-work/freeze.py --check-only
```

The `attempts/` directory preserves exploration errors, failed parser
revisions and exact logged failures, and the superseded broad unresolved
glue assumption. No source compiler output was repaired or regenerated.
No compiler, product loader/VM/cache/scope/writer, broad harness, Android-v5
route, hosted authority driver, native/device/simulator/emulator/UI/capture,
or global process inventory was started. No instance or process cleanup was
needed; no scratch checkout or native executable was created. All writes
are confined to this assigned packet. Independent review remains pending.
