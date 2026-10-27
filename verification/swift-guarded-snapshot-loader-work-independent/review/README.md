Independent review of released descriptor145 loader-work proposal

Decision: the released candidate is **not accepted**. Two Type-slice callback edges are incomplete. A direct isolated correction to the pricing tool and renewed independent review are required. This is a defect in named operation attribution; a whole-quote numerical shortfall has not been demonstrated.

The producer seal is `0550b44baf9f576d8379e1dd93f89ea9bd5b48ff7367762ae008181d29d2c30c`. All46 frozen members and all145 reconstructed compiler-source members are rehashed. The complete219 selected MIR definitions are each found verbatim exactly once in the existing whole-source MIR. Source tree `450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a` and host11 remain the scope. The preaccess packet is unchanged. No fresh compiler was used.

Concrete callback defect

`WasiFunction::resolve` at descriptor.rs167–184 compares `function.parameters() != parameters` and `function.results() != results`. Both actual MIR `<&[Type] as PartialEq>::ne` callsites are recorded in `blocking-callback-witness.json`. Their producer edges each target authored Type::eq with multiplicity1. That complete equality body costs104 logical actions.

The producer's broad `resolve(target)` tests whether an authored equality receiver's name occurs anywhere in the target. Finding `Type` inside `&[Type]` therefore returns the scalar Type equality immediately. The later branch that would add128 Type-slice callbacks runs only when `resolve(target) is None`; it never runs here. Contrary to the README, no128 edge exists in the sealed ledger.

A source-only PathOpen model has nine matching parameters and one matching result. Under the accepted closed-callback contract those two slice comparisons can invoke ten authored equality callbacks, while the named edges pay two. Eight callbacks,832 logical actions, are unassigned for that concrete shape. The advertised128-per-slice bound would require254 additional callbacks,26,416 actions. The model executes no product resolver or validator.

The broad match also occurs for actual Option<Type> comparisons and metadata's Type-slice versus `[Type;1]` comparison. Their maximum authored callback multiplicity is1, so the actual multiplicity1 covers those frozen sites. Direct Type::ne likewise delegates once. No additional multiplicity defect was found in those sites.

The native name-comparison term happens to exceed a source-specific requested-input upper bound by134,364 actions per resolver body. This explains why an overall numerical underbound is not proved. It does not fix the incorrect edge ledger and is not used to accept it. No unrelated native slack was reassigned.

Actual value/projection coverage

The README's claim that paying a base local always overcovers a projection is false through references. For this particular frozen source, an exhaustive independent value audit closes the actual sites using their other charges. `source-shapes.json` derives product shapes from actual frozen Rust field type strings rather than copying numeric FIELDS. It validates every selected local type, captured closure shape, generic C/D binding, and the admitted ten Copy element types; Control is the actual maximum at six source leaves. Empty arrays are known zero-size source shapes, not unknown types assigned zero.

`projected-value-ledger.json` retains every one of1456 dereference statements:

* 1128 borrow/address operations traverse pointers and form references without transferring the pointed aggregate value.
* 24 discriminant reads consume scalar tags.
* 204 typed Copy reads and30 no_retag reference copies materialize into complete typed destinations. For Buffer::reserve `_98 = copy (*_81)`, T's destination alone pays12 fetch/store units for its maximum six-leaf read+write transfer; the reference occurrence adds2.
* 8 overflow rvalues and24 nonassignment assert/switch reads use scalar values.
* 37 projected stores use fully typed source values, except scalar constant booleans. `observe` stores Option<[u8;32]> through a reference from its complete33-leaf temporary. No projected store requires an unpriced aggregate literal.
* One dereferenced Option<File> drop has at most two opaque source leaves, paid by its reference surcharge plus primitive/projection events. It has no product destructor, proves no close success, and grants no storage refund.

All by-value call operands in the selected definitions are materialized locals. No aggregate is copied directly from a projected/dereferenced argument into a call without a complete value surcharge. Each copied place and projected destination is independently typed, and its total applicable charges cover the actual transfer. This is a fixed-source proof, not correctness of a generic MIR verifier. New or unknown types, values or call shapes require renewed analysis and binding.

Loops, native requests and closure limits

The preaccess positive-credit audit remains applicable. Reader.take(0) is not used as a positive cut. Byte/uint, Buffer push/copy, empty-name comparison's trailing debit, heap-build's initial sift debit, body count/control initialization, and nonempty source-copy chunks cover dynamic repeats. Failed debit attempts propagate terminally. Nested loops use the same monotone original meter, so they share B; fixed2 segment-family setup/exit survives empty inner scans. The original five validation ceilings remain separate from the host logical-action conversion.

Loader zero-credit work is separately bounded. Read requests have32 calls and33 visits, including Interrupted failures and a zero-length file's EOF request. C-string scanning has4096 byte checks and4097 visits. Environment observation can read65 pointer slots and has a66 visit multiplier. The sort makes at most2016 comparisons and2079 while-condition visits, covered by2080. Hex has32 iterations and two digit-call sites; resolver find has34 candidate callbacks; array map has five. All complete statements and alternative failure/cleanup blocks are retained.

`native-audit.json` records independent source-specific request and visit calculations. Buffer native requested-byte bounds follow checked `capacity * size_of(T)` and the original category limits; they do not infer ABI size from six logical leaves. Source reserve/copy, retained reserve/resize, read buffers, hash input/output, fixed encodings, names/keys/process comparisons and equality have explicit bounds. Observe's control-key short-circuit paths give a536,512 total comparison/output-buffer upper bound below its540,672 native allocation. No missing native family or additional repeat defect was found in this pass. Native amounts never replace missing authored callback actions.

Pure controls and remaining scope

The owned run captures exact commands, tool versions, tool-source hashes, stdout/stderr, exit codes, elapsed time and waited child state. Independent controls cover972 nested-credit partitions, all actual value sites/shapes, the complete call/primitive roster, checked arithmetic, unknown/cyclic callees, and native/fixed-term omissions. The callback defect is an explicit counterexample, not hidden by a passing arithmetic rerun.

The historical token candidate was not used. P0 account/custody and quote evaluation, caller setup before P1, P2 argument/carrier production, P3 ingress/pre-store shell, P4 VM/cache/scope/constructor/writer/shared path, P5 reporting/custody/teardown, final source146, genuine fixture/session/build binding and complete host enforcement remain pending. The quote supplies no host budget or grant. Trusted quiescent process pointers and closed standard callbacks remain assumptions; private std retries/implementation work, allocator/kernel/CPU/RSS/time remain excluded. Physical devices, native simulator/emulator runtime, UI and capture remain paused.

No loader, validator, guest, VM, cache, scope, constructor, writer, compiler or native runtime was executed. No process inventory, publication, customer message, Git operation or outside-lane edit occurred. Only owned pure children were started and waited; owned duplicate scratch was removed. No GA gate is qualified.
