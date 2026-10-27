# Guarded snapshot writer/control work proposal

This compact packet derives missing source logical-action terms for the stable
composition writer, its fixed admission/control helpers and error propagation.
It runs only Python source-custody/arithmetic models. It does not import or run
Rust, the encoder, a VM, the writer, a hosted harness, UI, devices, capture tools,
process inventories, or a simulator/emulator. `WorkAuditPending` remains in the
source. All writer/control coefficients are provisional pending independent review.

`source-bindings.json` hashes121 exact function/type definitions, with source
locations and actual whole-file observations. The writer's complete definition
including trailing newline is5113 bytes, SHA256
`0de141d7c07db571a576fc343c3d43841614937c9ac07fd4cb64512761373343`.
The definition tree is a dedicated digest, **not** a claim that the whole144-file
composition tree equals an earlier tree. The composition owner confirmed that
only private measurement additions/attributes changed outside these behavior
bodies; future file drift is reported separately. Audited behavior/type drift
fails the model's custody check. No Git metadata was queried or changed; the
external encoder acceptance reports source revision
`79b948a7b361e537cfdd03285f68ea8c50d1a382`.

For E encoded bytes, B=ceil(E/4096), and A attempted writes:

| Quantity | Bound | Source reason |
| --- | --- | --- |
| Native write attempts | A<=32B | one native call per fixed range iteration; first error exits |
| Native requested bytes | <=32E | each block requested at most32 times, each request at most that block's size |
| Native file-call events | <=A+3 | writes, two metadata calls and one stream-position call |
| Writer transfer clear | <=4096B | one whole-buffer fill per attempted block |
| Transfer initialization | 4096 once | admitted storage array construction, before writer |
| Stop observations | <=12+5B+2A | seven fixed explicit stops, five fixed post-call checks; block4 explicit+1 encoder post; attempt pre+post |
| Opaque encoder getters | <=2+3B+2A | fixed extent2; block offset/bytes/final; attempted request/completion bytes |
| Terminal next_block(None) | 0 | break on returned final flag; no extra cursor call |

The transparent row proposal is
`W_local <=1214+4259B+122A <=1214+8163B`.
It includes local control/Result work, checked writer counter updates, metadata
decisions, logical native call events, all stop/getter calls, per-block4096
clear, and one global628 terminal diagnostic tail. It excludes the encoder
bodies and native implementation time. `ledger.json` gives the named row sums;
`cost-convention.md` explains copies and cooperative operations.

The **partial** future emission consumption contract, before missing caller and
formula-evaluation/cleanup terms, is:

```
accepted encoder: F14224 +26B+68I+39D+139W+Q
writer proposal:             1214+4259B+122A
required requested bytes:    32E
transfer initializer:        4096
```

With A<=32B and Q<=E this is
`F14224+1214+8189B+68I+39D+139W+33E+4096`, still **incomplete**.
The writer already includes the `3*(2+3B+2A)` opaque getter term; adding the
encoder interface's optional getter charge again would double count it. F is an
external accepted encoder-only parameter. The original frozen encoder proposal
still has F14221; root's separate additive correction accepts14224 and its
block26+68I+39D+139W+Q interface. This audit does not mutate that packet.

The fixed pre-debit shell is an explicit separate obligation. With WASI, cache
pairing has12 actual ticket checks, WASI pairing10, totals foundation3, and
storage preflight3:28 ticket checks plus one standalone cache owner check29.
These are fixed arrays of3 cache tickets,4 WASI tickets,6 category terms and2
storage-limit pairs. Vec capacities are scalar queries; none scans source,
records, cache slots, pins, metadata payloads or signature parameters.
This is compatible with the original design's constant-size pre-admitted shell
direction, subject to explicit shell/foundation acceptance; it is not work paid
retroactively by a later debit.

Proposed expanded helper amounts are cache/WASI pair1928, preflight260,
debit44, count/proof getter55, shape501 and commit293 (including its repeated
preflight). Admission has a separate once-only608 large-copy error tail.
The current source debits the original unselected16384, reads all9 lengths,
performs9 conversions/shape arithmetic, then returns `WorkAuditPending` before
second debit, commit or transfer initialization. The original prose says8
count conversions; the actual source converts source length as well as8 metadata
counts. Future policy selection must name the actual9-conversion source.

The future paid planning decision must cover the actual post-first-debit shape
work559, exact checked emission-bound evaluator, second debit44, and applicable
phase/return/transfer work. The existing checked debit helper itself costs44;
the work of reading/checking/storing work is not assumed free. There are a fixed
two intended debits, so no unbounded accounting recursion is needed. The actual
bound evaluator is absent and cannot be priced from an imagined implementation.
The original16384 planning value is not independently selected by this packet.

Every checked add/multiply/cast/Option/Result and helper branch is covered in the
source rows or explicitly named exclusion. Arithmetic failure terminates; no
wrapping/saturation is assumed. The one small failure stops further writer calls.
New wrapper bookkeeping is now separately priced below. Inherited original
construction/primary header/row, adoption, end_construction_phase_with_wasi,
retirement and cleanup/finalizer bodies remain explicit dependencies, alongside
foundation/F1 simultaneous-place acceptance. Native syscall implementation time and final device,
package/OTA, FieldLog, store, customer and GA gates are not covered.

Run `python3 verification/swift-guarded-snapshot-writer-work-audit/audit.py` from
the repository root. `results.json` records finite models and source custody.
Controls include all1,179,648 (block length, attempt index, failure-kind) traces,
8,193 small block geometries, first-error/acknowledgement/attempt32 limits,
32/64-bit checked-arithmetic boundaries, cap arithmetic, observer/getter site
counts, nested copy slots and helper-substitution consistency. These are finite
adverse models; they are not runtime proof of the writer. Provisional arithmetic
substitution mistakes and their correction remain in `attempt-history/`.

Root requested a final bounded wrapper extension before freeze. Added retirement
bookkeeping is132 once. Added finish bookkeeping is812 plus retire132 and a
possible302 Existing copy in its one direct WASI pairing:1246 once. This includes
optional WASI pair666 and usage31, and two reused OptionWasi observation copies
28 each. It does not include the original drop_proof, cache cleanup/tail.complete,
WASI cleanup or finish_owned_cleanup bodies. Their exact entry bodies are bound
as inherited dependencies; existing attribution remains a prerequisite. No
whole-engine cleanup proof is claimed.

Other new wrapper terms are scope adoption27 plus new adoption callbacks35,
scope construct16, forwarding5, new common guard15, branch begin2, branch
export13 plus refused Copy<=306 OR writer, branch finish/access-complete14, and
early branch return7. Attachment outer16 is **per call**, with inner45 at most
once plus original prepare/construct/complete/fail bodies. Borrowed outer getter3
is also per call. Repeated attachment/getter observations require actual caller
counts; only consuming construct/finish/retire are structurally one-shot. The
bounded future route must select those counts after source inspection.

The complete `begin_snapshot_access_v1` source orchestration is also explicit:
66 own actions across both arms, in addition to named helpers, transfer4096 and
once-only large copies608. The current fail-closed path has upper3431 including
its WorkAuditPending helper. The conditional all-branch future begin obligations
sum7926 **plus the actual emission-formula evaluator body**, with no selected
debit. A separate candidate fixed shell grouping is2867, including pairing,
preflight, the first debit's own44, and common refusal/error return work. This is
a proposed accounting partition for policy review; it does not authorize
retrospective funding or establish the missing foundation lifetime closure.
