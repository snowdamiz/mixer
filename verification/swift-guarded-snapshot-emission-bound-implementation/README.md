# Pure snapshot emission-bound candidate

This packet adds one unused private arithmetic helper to an isolated overlay of
the accepted authority225 source144 tree575b55. No real invocation/admission
path changes: `proposed_emission_work_v1` still returns `WorkAuditPending`.
The helper is a candidate for **emission only**, pending independent review and
later explicit integration. No complete work or storage floor is selected.

Accepted component interfaces give:

```
encoder initialization                       14224
encoder nonempty call ceiling                  291214 B
writer                                        1217 +4259B+122A
native requested bytes                        32E
one transfer-buffer initialization             4096
A<=32B, and the actual writer makes no terminal None call

candidate =14224+1217+4096 +B*(291214+4259+32*122)+32E
          =19537+299377B+32E
```

The encoder ceiling independently expands as
`26+68*515+39*(9*515)+139*513+4096=291214` under its accepted per-call counters.
It covers a failed nonempty call's prefix; retries after encoder error remain
forbidden. The actual stable writer exits at the first error and after its
final block, so it attempts at most B cursor calls and32B native writes. Every
request is at most its block length, giving32E total requested bytes. Early
stops consume a prefix bounded by the planned whole E/B envelope.

Getter3 is already in writer terms; no additional getter charge is added here.
The per-block writer clear4096B, encoder output Q<=E inside its call ceiling,
native requested32E and initializer4096 remain separate obligations. This
candidate includes that initializer once; the prior future-begin7930 interface
also names the same initializer, so a consumer combining decompositions must
attribute one occurrence. The authority routing delta19 belongs to earlier
pre-admitted construction, outside emission.

At raw E=B=0 the algebraic constant is19537; this is not a valid runtime shape.
The zero-count geometry function gives E2560/B1 and work400834, without proving
an empty source is a validated Swift profile. Maximum admitted geometry caps
give E69,765,152/B17,033 and work7,331,792,842. The original ExecutionWork
ceiling1,000,000,000 and every budget literal are unchanged. The conservative
maximum may therefore be refused; this packet adds no grant or larger ceiling.

The production helper in `overlay/.../emission_bound_v1.rs` reads only the
private shape's extent and blocks, then performs two checked multiplications
and two checked additions. It returns Arithmetic on overflow. It does not
validate a shape, grant authority, mutate work, observe a stop, allocate or call
an encoder/writer. The only parent-file delta declares the unused private module.
`source-delta.patch` and `source-manifest.json` bind the exact2-file delta and
resulting145-member source. The original144 files are verified under manifest
6f835a76 and source tree575b55; the entire control/budget source is unchanged.
The unchanged retained loader build descriptor still hardcodes source_count144
and support_count11 (lines409–410). This145-member overlay does **not** claim a
genuine loader descriptor/profile binding. Correcting and requalifying that
descriptor and its support roster is a separate coordinated integration step;
metadata success and arithmetic tests do not resolve the mismatch.

The helper's logical source-action price is29:
entry/return2 + two named field fetches2 + four checked operations4 + four eager
Arithmetic variants4 + four ok_or inspect/output pairs8 + three ? operations6
+ three local bindings3. Carrier/error paths and final Result return are included;
first overflow returns sooner. There is no unexplained rounded debit constant,
large Existing failure copy, loop, callback, clock or native call in the helper.
This is source logical work, not CPU/instruction/time or stack/RSS measurement.

If later integrated at the existing evaluator position, planning must already
pay these29 before computing the emission debit. The existing future-begin
interface excludes the evaluator body and already names its caller ?/binding3;
the actual future callsite still requires exact review. Its parameter/local/
Option/Result/eager-error/return storage must be funded before evaluation, which
precedes the current phase-storage commit. A later commit cannot retroactively
fund those places. `helper-source-roles.json` records actual source occurrences
and qualified host type observations for a **separate** owner-storage delta; no
byte floor or simultaneous set is selected and the active owner recipe is untouched.

The dedicated Rust host crate includes exact source declarations for the real
error/usage/shape types and the original pure shape/checked helpers, then imports
the exact candidate helper file. It contains no VM/encoder/writer modules or
entrypoint. Nine arithmetic groups pass in debug and optimized host modes:
minimum/cap corners, cap refusals, all geometry residues, monotonic boundaries,
each checked failure edge, an independent u128 oracle, unchanged-budget boundary
and actual type layouts. Raw synthetic overflow shapes are arithmetic probes,
not owner/proof fixtures. Full145-source metadata compilation passes in debug
and optimized modes; that compile executes no product function or unit suite.

Two deliberate negative controls are preserved: a coefficient lowered by1 fails
the exact-floor test (exit101), and an invalid helper return fails full-source
metadata compilation with E0308. These demonstrate actual helper use and module
inclusion. All nine command expectations are met. Expected failures retain their
stdout/stderr, mutation and preimage descriptions; every owned scratch directory
and binary/metadata artifact was removed after its child was reaped. Positive
metadata artifact hashes/sizes remain in receipts. No global process inventory
or other project's process/data was accessed for cleanup.

`verify.py` adds5507 deterministic source/algebra/prefix/custody controls.
`prepare.py --verify` and `verify.py --verify` are read-only reproducibility
checks. `run.py` repeats only this arithmetic and metadata workflow, retaining
receipts; it never imports a predecessor runner or hosted harness. Compiler
version, exact commands, environments, source digests, outputs and cleanup are
recorded. Dedicated host inputs are additionally reconstructed from the bound
unchanged packet bytes and recorded mutation, explicitly labelled as post-run
reconstruction rather than an independent filesystem capture.

Unresolved: independent emission review, new helper/callsite storage closure,
paid planning/shell/inherited/caller/cleanup and F1 lifetime decisions, target
layout/device qualification and all canonical/native/OTA/FieldLog/store/customer/
GA gates. No canonical source, budget, credential, deployment or Git state is
changed. No product VM/writer/encoder, native app/device/simulator/emulator test,
UI/capture, process inventory, forbidden hosted/rejected-worker harness or stopped
Android experiment is executed. Only the explicitly requested pure Rust host
arithmetic tests and source metadata compiler run.

The coordinator summary label was clarified after the recorded run to say
`product_runtime_entrypoints_executed=false`: the four listed pure arithmetic
functions are actual product-source functions and did execute. The dedicated
input reconstruction records the exact one-label coordinator delta and both
runner hashes; compiled Rust bytes, command sequences and test results did not
change or require another runtime run.
