# Apple reference-first runtime preparation v4

V4 repairs the ambient-Decimal-context precision defect found by the frozen V3
independent review. This is **host-only preparation**. All 111 retained producer
controls, all 25 focused repair controls, and all 37 exact V3 reviewer controls
pass. The latter include **25 actual composed inventory probes**, not 25 additional
independent tests. All 19 new exact-time controls and all eight frozen
actual-adapter precision cases pass. The exact historical reviewer remains
**32/33**: its malformed direct-TransactionStore journal fixture is correctly
rejected, and its unchanged acceptance assertion is still a recorded failure.
Independent V4 review, fresh root selection and native execution remain pending.

## Frozen rejection and derivative boundary

Before copying, V4 verified the V3 producer handoff
`f50006ea6fbe274eac4a78c214a33da4b77c4249b0ef2e8a19f1e0c4200e18f1`,
the V3 packet
`89e4b9b819bacc7ba69aee1fa2344245bf2eb26a3b8ed72a33a169f574f3fd60`,
and the rejected independent-review handoff
`70f56f2e9495cf6ca18c0298fdf83300849b484298b62830a4facf744c6eebe1`.
Its 621-member frozen closure had digest
`30e511b5622426f8288595da7613e829e50eba34046d8351186a7d415067cca4`.
Every member, including the original three failed reviewer controls and three
failed actual-adapter reproductions, remains unchanged. Historical V1/V2 failures,
the V3 producer and V3 review are preserved; no past failure is relabeled.

V3 multiplied the untouched Decimal token by one billion under the caller's
ambient precision. With precision 28, the raw JSON timestamp
`1792893615.999999999999999999999999999` became the integer
`1792893616000000000` ns. A baseline with that mtime was later than the actual
premise endpoint, yet V3 accepted the strict diagnostic result with count 1.
The independent review rejected dispatch. The source snapshots and raw hostile
inputs remain available in the frozen V3 review, without alteration.

The only V4 product-path changes are the packet-local importer and fresh namespace.
The auxiliary validator, actual Bridge, Session, TransactionStore, classifier,
original oracle, action budget, timings, observer V2 and compiled app/runner
products retain their existing contracts and bytes. The exact accepted derivative
source tree remains
`696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`.
The product archive remains
`0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`,
with 55-member product tree
`e3d60e7c69dcbe6e75e7089840b62dd4dd475f4a9db4fe87465543f822b39e20`.
No compiler is invoked. The packet-local source manifest separately binds its
31-file selected closure. `namespace-adaptation.patch` records the initial
namespace-only changes, and `v3-to-v4-repair.patch` records the final derivative.

## Exact timestamp predicates and finite work

The importer uses `Decimal.as_tuple()` solely to retrieve the original sign,
digits and exponent. It performs no Decimal multiplication, quantization,
rounding or integral conversion, and never changes or consults Decimal context.
Integer digit processing removes only known trailing zeroes. A nonzero discarded
digit rejects before integer construction. Only after checking the result length
does the importer construct a bounded integer coefficient or power of ten.

A genuine sub-nanosecond endpoint is incomplete/invalid diagnostic evidence with
an unknown input count. It never becomes a diagnostic pass or a native-fault
claim. Exact nanoseconds with extra trailing decimal zeroes and equivalent
exponent notation are accepted. There is no tolerance, discretionary rounding or
arbitrarily increased Decimal precision.

The existing raw JSON bound is two million bytes, with duplicate/nonfinite/overflow
and depth validation retained. The exact decimal pass additionally caps each
numeric token and coefficient at 1024 characters/digits. Nanosecond results are
capped at 318 digits, covering the largest finite binary64 seconds permitted by
the original JSON pass. Positive huge exponents reject before computing powers;
nonzero tiny values reject before constructing enormous divisors. Finite zeroes
with extreme representable exponents return zero without exponent-sized work.
Negative nonzero, nonfinite and unrepresentable values reject. All authoritative
endpoints still must be inside the unchanged 660-second selected-run range.

Every authoritative ordering predicate uses exact integer nanoseconds: root
microsecond/calendar time, summary start/finish, generation begin, original
premise, original before-key attachment, original returned witness and verdict,
and original filesystem mtimes. Summary start must be strictly before finish;
this is now checked against untouched decimal endpoints even when the ordinary
JSON float values collide. Root freshness compares timedeltas directly.

The original before signature must be no older than its begin and no later than
the exact original premise. The after signature must be no older than baseline
and no later than the exact later returned witness. A changed after file may
therefore occur after the premise. An entirely unchanged after file remains
allowed. Monotonic AX/key witness ordering is separate and unchanged.

## Host evidence and retained limitations

The final host command is:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v4/verify_host.py --attempt 2
```

The [host receipt](../verification/apple-focus-reference-runtime-v4/host-attempt-2/receipt.json)
records the command, Python 3.14.8, host uname, inherited compilation revision
label, exact input/source/tool/output hashes and cleanup. The label
`ba9ad4372f94463ba4d363cdfd76dd565c96413f` is inherited; exact hashes define this
host work. No Git query or mutation is performed. Attempt 1 passed the runtime
controls; attempt 2 binds the finalized handoff implementation. Both are retained.
There are no newly failed producer, focused, V3-review, precision or actual-adapter
controls. The single expected historical malformed-fixture assertion remains in
each historical replay log and receipt.

`replay_v3_review.py` extracts the exact 37 reviewer method bodies, mutation map,
loop and composed program from frozen reviewer source
`eaeab5532ef11e0ffe7d9a73c44b64de6f60c7e180d61ed65b7d5d99dbd9624b`.
Their source hashes, unchanged assertions and results are retained. The historical
33-control source remains
`84f7d1c5dbe0cbe17d60c34675de1c3d17107c17964062ea74ebdf5982a195db`.
Its direct TransactionStore publication is not a valid Session journal; V4 does
not whitelist its marker or weaken validation. Actual Session-driven AX/PNG and
complete Settings/baseline controls continue to pass.

The 19 new controls include 35 actual adapter captures using explicit fake tool
returns. They exercise exact endpoints and +1 ns, before/after lower bounds,
summary/root/attachment ordering, ordinary-float collisions, deep positive and
negative sub-nanosecond tails, trailing zeroes, scientific notation, maximum
token/coefficient/result bounds, huge exponents, signed zeroes and invalid values.
Expected scalar results use independent rational/literal-integer facts. Adapter
probes preserve the raw timestamp tokens through the production capture boundary.
The eight frozen actual-adapter cases additionally retain complete raw inputs,
capture exports, control/result files and exact endpoint facts in the V4 attempt.

Hostile ambient Decimal contexts use precision 1, 2, 9, 18, 28 and 120, multiple
rounding modes, tiny exponent ranges and every trap enabled. Valid exact endpoints
still accept, inexact endpoints reject, and all Decimal signal flags stay clear.
An untrapped context also cannot admit unrepresentable/nonfinite timestamps.

Parent audit guards forbid native commands, process execution and sockets except
for inspected Python composition probes inside the V4 directory. Those children
install process/network prohibitions before composition import. All observations,
file payloads, Settings requests, app acknowledgments and tool returns are
synthetic host fixtures. They supply no native screenshots, input delivery,
physical-device evidence, compile receipt or runtime qualification.

## Frozen handoff and separate dispatch

The host packet and complete evidence are frozen in
[handoff.json](../verification/apple-focus-reference-runtime-v4/handoff.json).
File/hash verification is:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v4/freeze.py verify
```

Fresh independent V4 review must precede any root dispatch. V4 root selection uses
`mixer.apple-focus-reference-root-selection.4`; names begin `MixerFocusReferenceV4-`
and output directories begin `native-run-v4-` with a fresh run UUID. V3 selections
and outputs cannot be adopted. All other root fields, pinned tools, five cleanup
actions, one selected owned simulator, baseline ownership and exact product/source
bindings retain their meaning. Preparation never dispatches this branch.

Owned host scratch is absent after every test attempt, including composition,
transaction and adapter probes. All frozen inputs are rehashed before and after
controls. No simulator/emulator/device query or execution, UI/screen capture,
service, compiler, signing, shared-file write, publication, customer message or
credential action occurs. The frozen hosted catalog/authority lane and separately
interrupted hosted worker transport V2 review are not read, imported or executed.

`runPassed`, complete-case, cursor, keyboard, carrier and GA credit remain false.
Native execution, the original authored-first failure, full keyboard/comparator
coverage, immutable published FieldLog packages from a separate repository,
signing, store, operational and accountable-reviewer gates remain open. Physical
phones remain disconnected and deferred. No development or GA gate is promoted
by this host-only packet.
