# Independent review of complete G6 component-source accounting

The immutable producer packet is arithmetically reproducible, but its claim of
complete exact accounting needs one finite correction. The two G6
`c.copy_within(1944..2008, 1536)` calls (selected source lines596/642) are slice
method calls. Their template receives only a thin Candidate pointer. It omits
the complete slice receiver construction/transfer that the packet itself uses
for the same Candidate-to-slice coercion in `st` and `ld`.

Replacing the two receiver operations with the six explicit component edges in
`receiver-correction.json` adds four scalar operations to every affected path.
The corrected production maximum is **6,737 scalars /422 blocks +90 copies =512
groups**. The corrected maximum including private fault controls is **6,778
scalars /424 blocks +90 copies =514 groups**, within unchanged G6 cap640. This
does not prove a cap overrun. Root must select a separate correction addendum;
this review does not rewrite or accept the producer's frozen exact511 claim.

The receiver's source/received phases are also missing from the local-place
inventory. `receiver-correction.json` supplies the required Candidate-to-slice,
Range, argument, guard/address and unit phases. The cleanup caller's actual
`arena: &mut Arena` source pointer is another omitted named live place; its Vec
field24 is a different existing owner. This makes the packet's
`complete_G6_local_category_inventory: true` too broad. No wire/control/helper
role is invented here. All whole29,344-byte and role192/256 fits remain pending.

`audit.py` was authored independently. It never imports or runs producer
`ledger.py`, `verify.py` or Mixer code. Source-derived component formulas
independently reproduce all nine published helper templates and all73 published
path counts; a second recipe set adds the required receiver correction. The
full extremal operation stream is checked for unique IDs, owner partitions,
copy widths and segment hashes. Both producer14-member/565,517-byte custody and
the selected C3/clear/proposal seals are verified directly by SHA256. See
`results.json`, `audit.stdout.json`, `custody.json` and `review-findings.json`.

The audit checked st/sq LE return and destination copies separately; the staged
prior-pins ld's full8-byte argument; checked Options and loop final None16;
Range/view/receiver fields; call, unit and return control; merge caller edges;
final staging, commits, cleanup guard, exact16x128 clear, twelve restores, private
faults and returned bool/caller negation. No further finite omission was found
under the explicit selected authored-source primitive scope. It does not count
compiler ABI, machine instructions, libstd internals or measured runtime work.

Ordinary early refusals have no G6 event staging; later refusals are bounded by
the explicitly checked staging prefixes. The success/failure cleanup suffixes
are independently bounded. Combinations of private commit and cleanup failures
are dominated by the larger full built-publication cleanup-failure path; no
unlisted combination is silently treated as success. Pre-loan refusal does not
touch Candidate; the exact admitted source has one cleanup call after the loan.
G1 admission/initial flags, G5 prefix542..561, G3/G4 merge body, paid G7 replies
and G128 zero-debit guard replies keep those owners. The looser555 number is
G1-inclusive bounding slack and is not an actual G6 partition.

To reproduce this source-only audit (writes this directory's result/custody):

```sh
python3 -B verification/swift-cache-state-g6-complete-independent/audit.py
```

No compiler, product/runtime execution, native instance, UI, screen capture,
process inventory, commit or push occurred. No producer/C3/frozen source was
mutated. Full G3/G4, total work union, complete simultaneous lifetime union,
implementation acceptance, dogfood release, OTA authority and GA qualification
remain outside this review. Native checks remain paused/pending.
