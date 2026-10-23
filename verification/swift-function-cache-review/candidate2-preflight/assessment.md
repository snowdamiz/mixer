# Provisional candidate 2 preflight assessment

This is a source/type audit of an evolving candidate, not implementation acceptance or a new foundation numeric allowance. Candidate 1's report, receipt and all 85 bound artifacts remain unchanged.

The originally proposed 552-byte chain was not complete. It omitted the called WASI owner-check parameters, root reservation/fault/time helpers and their associated values. The independent snapshot captured the expanded chain at 1,056 bytes/align16, GroupA at 2,432/align16, GroupB at 1,696/align8 and the existing control at 1,720/align8 in both Debug and Release. The snapshot's precise VM Rust sources, test-only includes, commands and output hashes are bound by `measurement-receipt.json`; it must not be mistaken for a final candidate 2 freeze.

The measured actual anonymous closures are pairing16/align8, layout-failure24/align8 and bound-add8/align8. The capture storage therefore consists of references for the non-move closures, rather than copied 112-byte observations or 32-byte cursors. The expanded source corrects those fields. All measured preflight Result/Option<Result> variants carrying a possible SwiftRunFailure are 1,096/align8; violation Option<(Invariant,&str)> is24/align8, Instant/Duration16/align8, u12816/align16 and Result<u64,TryFromIntError>16/align8. Source, return and argument/pattern transfers still need distinct whole-slot roles when simultaneously active.

The required early phases include:

1. Caller prepare parameters and bounded helper parameters.
2. Optional pairing/map/checked_usage/then/context.usage, including missing or foreign WASI headers. A foreign context's envelope cannot pay the local control's temporaries.
3. Both adopted ticket checks or the intact cache-header check, including reservation category lookup, violation Option/tuple/pattern values, fault construction and the first immutable failure snapshot.
4. The normal usage snapshot and previous-bound extraction, runtime checked previous+extra addition and failure closure/Result transfer.
5. The helper's actual return and end.
6. After the helper has ended, the prepare caller's new observation, checkpoint and **enlarge_construction_with_wasi before it commits**: check/cancellation/deadline, construction-ticket/old bound, category/combined preflight, Fault::new/limit, failure/usage transfers, and successful commit/category_mut. The extra construction/operation allowance cannot fund this phase before commit.

Pure checked size sums may be evaluated exclusively in const initializers. Runtime getters still return an Option and the runtime previous-bound addition still has its Option/Result path, but runtime calculator arrays/folds/products cease to exist by language semantics. This is a valid narrow repair, without relying on optimization or last use.

Whole local proof/adopted transfer slots2/3 are disjoint from the selected prepare/preflight call graph: inputs are borrowed intact, and whole owner construct/Partial/drop_proof transfers begin after helper and prepare return. Operation prepare likewise only borrows the existing cache. A foreign supplied owner remains in its original caller/control, with no local whole-owner transfer. Thus complete measured groups may be assigned to these entire local slots, alongside the control-transfer alternatives, if the final field/branch table proves each fit. No remainder or padding inside a live owner is available. This direction does not apply to construct's owned recheck, final cleanup's currently unreused proof/adopted classes, or an enclosing executor phase. Those require their own disjoint accounting.

A possible additional whole-slot alternative is a root standalone Usage slot during early preflight. The normal helper usage return occurs after pairing/owner success, and its temporary ends at the previous-bound let statement. Pairing/owner faults instead call fail->usage, while record_cleanup is absent. The final map must count every usage source/return/at_failure transfer and separately funded outer caller outcome before using such an alternative; no numeric reduction is accepted here on that suggestion alone.

Root approved the proof/adopted transfer-slot design direction subject to the final frozen measured branch map. No root numeric amendment has been accepted by this review. No target guest, device, publication or GA qualification occurred.
