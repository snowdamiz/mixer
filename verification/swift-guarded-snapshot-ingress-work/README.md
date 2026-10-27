# Frozen selected ingress and optional WASI source work

This candidate exports three finite logical-source-action ceilings for the
144-member source tree `575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896`
in `swift-guarded-snapshot-scope-authority-correction/source/vm`. Its source packet
seal is `351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c`.

| Export | Actions | Exact invocation scope |
| --- | ---: | --- |
| `W_ingress` | 33,613 | Once: consuming selected carrier, authentic selected tuple, adoption wrapper/core, all selected callbacks, and possible pre-scope failure retirement/finalizer |
| `W_setup` | 68,781 | Optional once: attachment wrappers, prepare, one construct attempt, any selected partial cleanup, and complete |
| `W_wasi_finish` | 7,155 | Optional once: final `AccountedWasi::cleanup`, context usage getter and up to five drop/refund calls |

For `z` in `{0,1}`, these missing scopes contribute
`33613 + z*(68781+7155)`; the maximum is **109,549**. This is an additional
source-work term, not a runtime debit. Attachment permits cached repeated API
calls in general; this interface assumes the selected caller invokes attachment
at most once. Each additional cached call, if later permitted, needs the existing
16-action outer row separately.

The sibling complete-work-plan lane owns caller/construct/outer/final-run wrappers
and the original constructor/row/cache-cleanup envelope. Ingress failure includes
its own `finish_owned_cleanup` invocation because it returns before a final run
exists. Final-run cleanup remains the sibling's invocation. `W_setup` includes
at most one of the two partial-cleanup branches; final WASI cleanup is separately
priced even after setup failure because charging that harmless upper sum closes
both result paths. Historical `521088` names constructor and cache cleanup;
there is no justified automatic adoption/WASI charge or subtraction from its
broad fixed-path row. Historical `451173376` is evidence, not selected funding.

`ledger.json` contains 64 complete-body source fingerprints and 11 loop or repeat
expression fingerprints. Every body has named local parts and explicit callee
multiplicities, with an acyclic expanded total. Key fixed maxima are 17 budget
comparisons, five adoption admissions, two failure refunds, three final-control
tickets, 13 WASI layout terms, four WASI buffer iterations, four capacity-fold
iterations, 64 inline Span outputs and five WASI final drops/refunds.

The writer correction's exact small helper and wrapper rows are reused and
rebound, including adoption wrapper27, selected callback bookkeeping35,
attachment bookkeeping61 and the context/WASI getter pair28/31. Remaining helpers
are newly priced. The inherited unit charges entry+return2, fetch/store/scalar or
decision1, primitive logical invocation1, and aggregate Copy fetch+store per leaf.
Bound operands remain free. Deliberate conservative allowances additionally
retain explicit Copy parameter transfers, aggregate output slots and alternative
branch stores even where the convention would permit a cheaper owned move.
Terminal callbacks use a stated branch maximum; other written branch work may
be upper-summed. These are explained overcounts, not arbitrary multipliers.

Atomic owner allocation is one logical primitive invocation and one evaluation
of its closed pure `checked_add` callback. Standard-library retry reevaluations,
private std code, allocation/kernel implementations, machine instructions,
CPU/wall time and syscall interruptibility are outside this selected unit.
No contention semantics change is required or made. Buffer allocation calls are
logical events; there is no claim of source-level per-byte initialization when
the code reserves capacity without filling it.

The frozen original foundation getter already copies a const Option for3.
The separate, unapplied replacement interface prices a new const-copy body at3:
snapshot helper17→3 reduces `W_ingress` by14. If separately changed and rebound,
WASI construction-layout176→3 and header-layout22→3 reduce `W_setup` by173 and19.
No active funding source was read, and no such replacement is accepted here.

`python3 verification/swift-guarded-snapshot-ingress-work/check.py` verifies the
entire frozen source manifest/seal, all arithmetic, 31 positive/negative controls
and the preserved `WorkAuditPending` source. Mutation controls remove real loop,
Copy or callee terms and reject the changed expanded export. These finite
controls support review of the manual ledger; they are not independent source
review or OTA authority. No compiler, writer, runtime, native/device, simulator,
emulator, UI or capture was run. Operational work/storage and all GA gates remain
unqualified.
