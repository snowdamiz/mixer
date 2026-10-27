# Independent scoped immutable binding review

The frozen lifetime-only candidate passes this independent offline source,
ownership-boundary, compiler-evidence, full MIR and concrete-inline-layout review.
The reviewed source is `69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7`;
the producer seal is `84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2`.
No compiler, product executable, native test, UI, capture or global process
inventory ran in this independent lane. All writes are in this packet.

`report.json` is the complete independently derived result. `audit.py` imports
only the Python standard library, executes no other program, and does not import
the producer's parser, normalizer, source transformation or derive helpers.
The producer's permitted read-only verifier also passed under a separate bounded
Python command. Every host command retains its plan, source/tool identity,
stdout/stderr, terminal status and exact-owned-group cleanup receipt.

The accepted 146 source members and the candidate/query trees were reconstructed
through explicit frozen custody, including the accepted overlay profile.
Exactly 145 members remain byte-identical; the profile changes only the six
reviewed types' shared lifetime annotations, affected function signatures and
comments. A separate source projection and exact field grammar validate that
delta. All binding/account/whole-quote selectors remain their Pending refusals.
The type fields remain covariant shared borrows; neither a mutable,
interior-mutable nor contravariant lifetime-bearing field is introduced.
The owned result carries no fixture lifetime.

The retained rustc 1.99.0 executable bytes, its frozen version preimage, actual
production cfg, argv/environment and both query manifests were verified against
the accepted compiler query. The positive probe's actual MIR contains the local
owned binding borrow through the consuming call and has no caller. Its retained
compile exited 0 in 3.32 seconds. The combined negative compile exited 1 in 3.03
seconds with exactly E0515 twice, E0506, E0505 and E0382. Each diagnostic is
bound to the reconstructed source line. Both producer compiler children/groups
were reaped/absent and owned scratch removed. This review did not recompile.

The complete raw MIR parser accounts for all UTF-8 bytes, accepting only actual
constructs, whitespace and compiler comment lines. Both inputs compare across
6,006 production constructs: 2,020 functions, 248 braced const/static/anonymous
bodies, 1,785 standalone constants and 1,953 emitted allocation blocks. Only
four precisely named inert probe functions and their explicit anonymous layout
constants are excluded; their complete header inventory is retained. No
production body is excluded. Every operand, place, move/copy, call, literal,
constant, CFG and drop route is preserved after narrow display normalization.

The allocation mapping has 1,459 distinct IDs across the 1,953 emitted blocks;
494 declarations repeat. Six mapping pairs follow production reference roles,
36 follow relocation roles, and 1,417 follow unique complete-payload plus complete
production-context sets. Every repeated declaration must agree. All extents,
alignment, raw bytes, ASCII displays, static identity and relocation targets
compare, and every occurrence position is checked against that independently
derived bijection. Mapping does not depend on declaration order or the observed
+4 ID offset. The arbitrary-offset positive control and incorrect-target
negative control exercise this distinction.

**Mandatory completeness amendment:** the producer's 4,221-block parser omits
1,785 top-level single-line constants. That claim covers braced constructs only.
`standalone-constants.json` inventories every omitted line with exact accepted
and candidate text, one-based MIR line, zero-based UTF-8 byte offset, raw SHA and
normalized SHA. Of these lines, 1,746 are raw-byte identical and 39 differ only
in exact scratch/impl display coordinates. All 1,785 normalized lines are exact.
Any full-MIR preservation claim must include this independent amendment.

All 44 old concrete inline layout observations remain identical. The two
additional Result size/alignment observations are 8/8. These observations price
no dynamic/native backing. Thirty-eight host controls exercise semantic and
standalone constant changes, moves, places, calls/drop/CFG, strings and character
literal comment masking, raw allocations, extents, alignment, static headers,
relocation identities, parser coverage, inactive/misnamed probes, unrelated or
unsafe lifetime changes, mutable/interior-mutable/contravariant owners, borrowed
result escape, unsafe transmute, Clone/Copy, constructor and selector changes.
They are host comparator/source-boundary controls, not new rustc or runtime tests.

Producer preliminary preparation and both failed offline comparators remain in
the frozen candidate. This lane also retains its first failed full audit and
exact source preimage: a character literal containing a double quote exposed a
reviewer lexer error. The corrected lexer distinguishes character/string/comment
regions and has a specific adverse control. Interim successful audit preimages
and outputs remain retained; the final recorded command uses current `audit.py`.
The preliminary distinct-allocation count was corrected before finalization.

The old conditional source-work/storage acceptance names source tree
`27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3` only.
This review proves preservation of that source's production MIR and inline
layout observations and recommends retaining the conditional logical-source
counts in an explicitly source-bound root decision for the new tree. It does
not itself accept or operationally rebind whole pricing. Actual immutable
provider/identity/native path correspondence, future provider/launcher work and
backing, whole pricing, P0 funding, selected root policy/account/quote,
executable closure, healthy cleanup, native tests, separate immutable FieldLog
packages, OTA and GA remain pending. Native/device/UI/capture remain paused.

Verify without writing, recompiling, process inventory or product execution:

```sh
python3 -B verification/swift-guarded-snapshot-scoped-binding-independent/check.py --read-only
```

The check rehashes both seals and every independent member, rederives the entire
source/MIR/layout/negative/control result, verifies the standalone amendment and
host command custody, and checks read-only modes. This packet is sealed once.
