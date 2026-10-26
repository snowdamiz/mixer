# Failed cached-head source proposal

This finite candidate is rejected under the selected detailed component grammar.
It changes no product file and grants no implementation, compiler, runtime,
layout, lifetime, release, or GA acceptance.

The proposed source retains two cached heads and loads each index/timestamp only
when that cursor advances. Six explicitly written 64-element array constructors
replace 384 destination `IndexMut` writes. Each constructor is moved as a complete
64-byte source into its received output place and copied once into the existing
destination region. There is no macro, unsafe block, raw reinterpretation,
additional Candidate owner, or optimizer-elision assumption.

The finite all-eligible witness uses six-bit-reversal timestamps. It reaches
32+48+56+60+62+63=321 comparisons, 384 head loads and 384 outputs. The necessary G3
subtrace alone is 36,297 scalar events plus 384 complete 8-byte timestamp argument
copies: ceil(36,297/16)+384=2,653 groups, exceeding 2,568 by 85. This omits head-loader
call/return work, exhausted-head stores, one-time views and callee merge return.
Even dropping both actual slice-length receiver edges from every head load,
and retaining only the selected Index20 minimum, gives 2,605 groups. The complete
named finite helper kernel on the witness reaches 2,708 G3 groups.

The G4 necessary floor is 12,252 scalar events plus 12 actual 64-byte copies, or
778 groups against 768. It includes emit arguments/entry, output source/return/
array-element transfers, cursor advances/bounds, 57 inline run resets, source
range views, destination range/copy receivers and the explicit 64-byte source/
received output places. It omits state constructors and callee merge return.

`finite-kernel-ledger.json.gz` names every operation in the executed load-heads/
emit kernel, all run resets, and the G4 outer source/destination range and actual
output64-copy subtrace. Each scalar belongs to exactly one group of at
most16; every copy has a separate group. It is complete for its stated kernel,
not a complete whole-merge or new-path upper ledger. Test-only counters are
retained in source; the ledger covers the non-test body. The packet deliberately
stops at this failed initial necessary-bound gate. One-time split/chunk setup
and a full G2/G5 component recount were not built for a candidate already over
cap. Their source seams remain disclosed in `source-assembly.json` and the diff;
the prior byte proposal's numeric grammar and bounds are not reused.

`source/cache_state.rs.txt` is the full rejected source assembled from immutable
correction3 plus this merge and the prior proposal's G2/G5 source ideas.
`proposed.diff` binds all changed seams. Cleanup, the G6 suffix after the prefix,
G6 event staging before merge, and the actual `merge(c)` caller/headroom guard
bytes remain identical. The four selected caller-only G6 operations stay G6.
Group ownership and complete pending qualifications are in `group-amendment.md`.

Python mathematical checks passed 2,066 finite cases against an independent
sorted eligible oracle. They cover stable slot ties, timestamp u64::MAX,
ineligible255 tails and private exhausted256 never being emitted. They do not
execute Rust or qualify the proposed source. No compiler, runtime, native test,
UI, screen capture, process inventory, commit, push or publication was run.

This establishes an obstacle for this exact cached-index source and explicit
ownership. It does not establish that every possible private sorting design is
impossible. A direct timestamp+slot tuple buffer is a distinct future proposal;
it is not included here.
