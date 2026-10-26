# Scope and accounting delta for the Q9/Q10 correction

This is a producer source reconciliation for review, not independent endorsement
of the inherited coarse scalar-block ledger. The correction changes only the
`shape_q` function body; `correction-source-audit.json` binds both function hashes
and proves all product bytes before/after that body unchanged. Rebuilt source-work
and lifetime ledgers bind current file hashes/line ranges. The inherited637
admin/block proof remains pending independent reconciliation under the original
640/7680/8151 and role29344 caps.

The changed source read sets are:

| Stage | Masks10/11/12 | Feasible15 | Destination14 | Pending13 |
|---|---|---|---|---|
|0..5|not read|not read|not read|not read|
|6,9,10|validate limits/subsets|must be0/1|read only if feasible1|not read|
|7,8|validate limits/subsets|must be1|read only if feasible1|read only after feasible1; range before shift|

This preserves the existing active-stage condition for operation/function, all
initial/count/call/latch checks and T01–T15 classifier order. A guard failure
returns the existing bool false to the same T09 poison branch; the aggregate,
observation, suppression words, literal false getters and complete Result sizes
are unchanged. Inactive arbitrary fields are ignored rather than rewritten.

The original planned range expression `(6..=10).contains(&q[3])` moves from the
destination-only guard to the encompassing block. Its complete bounded range,
argument/reference and returned bool work already exists. The old destination
`planned && ...` short-circuit conjunction is removed; its bool/branch owner is
replaced by the enclosing branch. The two mask subset expressions and all mask
loads remain unchanged, but now execute only within that block. No helper,
loop, key load, LE conversion, fixed copy or row mutation is added.

The only new value predicate is `q[15] != 1` before the pending range/membership
checks. It consists of one checked fixed-array scalar access, one scalar
comparison and one short-circuit branch. Conservatively its temporary bool
source/received places are2 bytes and its value/control work is four named
scalar operations, below one16-operation block. The existing pending stage
checks remain unchanged. This delta belongs solely to the existing finish256
Q-guard/finalizer ownership. It cannot spend any unused group6 or arena credit.
The old complete finish ledger still requires independent reconciliation; these
four operations are explicitly recorded so they cannot disappear in that audit.

There is no new lexical binding or persistent owner. `q` is still a shared
borrow of the same16-word snapshot, `f` the same immutable parsed Fixture view,
and the function returns the same1-byte bool source/received value. Existing
read-set branch expression temporaries have the same type/lifetime and die
before the subsequent Q guard. The conservative additional2-byte bool transient
fits within the existing control role1280's44-byte rounding remainder (producer
union1236 becomes at most1238); the selected role capacity1280 and full union29344
remain unchanged. This is use of the same named control role, not a transfer from
another role or a claim about compiler stack layout or optimization.

Actual normal and optimized compiler/layout, old/new public API and applicable
public/legacy/private regressions run against the exact corrected source. The
focused seeded matrices are private guard tests only. Public reachability of the
independently reported defects is not established by this correction. No old
contract-model check or three excluded SS/SF flag combinations receive runtime
pass credit. Source prefix/cleanup/tail/Result layout evidence from the immutable
candidate is reused only where the exact source is verified unchanged; all
pending independent qualifications remain pending.
