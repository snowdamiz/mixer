# R01: physical alignment is independent of numerical rebasing

The original v1 packet and its independent review remain unchanged. This version
changes only the two selected source files and their preparation/evidence packet.
No selected module, syntax checker, test, compiler/capture or actual-input parser
has executed. The sixteen method families remain P01-P16.

The old offset+rebase alignment check proved only a property of an arbitrary
coordinate origin. The frozen witness joins A_R/A_C with a one-byte signed base
delta while their local normalized starts are both zero. Their physical start
separation is -15 bytes, contradicting two claimed eight-byte alignments.

Each arena now requires physical_alignment explicitly: either null, or a closed
record with modulus, residue, reviewed and evidence. Modulus is a positive power
of two within u64; residue lies in [0,modulus). A reviewed record states that the
actual symbolic entry-base address is congruent to residue modulo modulus. Its
artifact anchors and semantic meaning still require independent whole-slice
review and the external root approval. An EntrySP name supplies no implicit ABI
alignment. Unreviewed records and null records supply no known congruence.

For every reviewed same-base component, checked signed origin deltas express
arena_base = component_base + origin. Known congruences are translated to the
component base and merged. Two power-of-two congruences are compatible exactly
when their residues agree modulo the smaller modulus. A disagreement refuses.
The strongest compatible known congruence is retained.

Separately, each region requires component_base + origin + signed_offset to be
zero modulo its declared alignment. These requirements are checked against one
another and the known facts. They are not inserted into the known-evidence set.
Thus a compatible eight-byte base fact cannot grow into a sixteen-byte fact by
merging a region requirement. Contradictory claims refuse; missing or too-weak
support adds a local missing fact and suppresses all numeric local unions.

entry_min/rebase still bounds coordinate/end arithmetic and requires its own
review. It no longer supplies or tests physical alignment. A coordinate origin
may move by one while the separately evidenced physical address stays aligned.
Native SP/frame containment and lifetime checks are otherwise unchanged.

The added P09/P10 source subcases cover both witness deltas +/-1 with known base
facts and with only contradictory region requirements, positive deltas0/8, a
neighbor's congruence supplying missing local support, both facts absent, absent/
unreviewed/modulo1 facts, malformed congruences, stronger alignment unsupported by
modulo8, a contradicting modulo16 residue, a consistent modulo16 residue, and a
coordinate-only rebase change. No fixture claims actual physical evidence.

All trust/capture/source pins, phase coverage, byte bounds, signed arithmetic,
backing identities, pending retained partitions and external approval remain.
Every output stays local_geometry_only=true and complete_capacity_accepted=false.
No price, grant, refund, root durability, backing bound or product integration is
accepted. Source review and a separately released bounded synthetic run are next.
