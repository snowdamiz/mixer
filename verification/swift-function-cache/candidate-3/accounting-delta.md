# Candidate 3 construction-only accounting delta

This candidate is a new exact source identity. It does not reuse C2's exact-source
phase acceptance as acceptance of changed bytes. C1/C2 artifacts remain immutable;
`prior-candidate-preservation.json` records all 47 C2 artifact hashes and verifies
all 118 C2 archived source members. C2's independent and root phase receipts are
historical inputs. A separate C3 review/root acceptance must bind the new source.

Frozen cache source SHA-256:
`43d4d7af4a1959d2afd5b1da39801b0a0e4a875d5b81f05142b4befa5e120614`.
Frozen test source SHA-256:
`a734428c772f6bcced05e51a452721831e9eb9ebfa6a84c44e02efec16987c00`.
The executed Debug/Release measurements and every inventory field are bound in
`preflight-root-tail-map.json` (SHA-256
`e94138b68960d3c18e3ccc912ee7dbbf31df41ae3ffa484f07b8463af1dffeae`).
These are authored logical named-value footprints, not compiler stack, opaque
standard-library/platform internals, allocator overhead or RSS measurements.

Production still uses the same NEXT_OWNER atomic initialized to 1 and the exact
`try_update(Relaxed,Relaxed,|n|n.checked_add(1))` operation. The private
`allocate_owner(&AtomicU64)` helper contains that operation; `next_owner()` selects
the production counter. There is no new proof/adopted/control ownership wrapper.
Both helper frames run only inside construct_partial after the construction
phase enlargement has succeeded. No early preflight or final cleanup frame
calls them.

The cfg(test)-only selector can use a thread-local private atomic. A scoped RAII
guard saves/restores that private counter and clears selection during both normal
return and panic unwinding. No path seeds, swaps or stores NEXT_OWNER. No test
flag/counter is a field of a production cache/control/proof struct. Parallel test
threads have distinct private counters and selection flags.

| Complete measured role | C2 | C3 | Additive change |
|---|---:|---:|---:|
| ConstructionBorrowChainInventory |168 / align8|184 / align8|16 per inventory, count3 =48|
| Result<u64,u64> small allocator transfer shapes |3 ×16|6 ×16|48|
| Construction total |57128|57224|96|

The new borrow fields are `owner_allocator_argument` (the selected counter handle
at the `next_owner` -> `allocate_owner` call) and `owner_allocator_counter` (the
callee's distinct counter parameter), each an 8-byte shared AtomicU64 reference.
The existing ConstructionScalarInventory.owner_candidate names the checked-add
closure's u64 input; construction already has whole Option<u64> roles for its
checked-add return. The six small Result roles bound the atomic-call return,
allocator-return expression, selector's incoming result expression, selector
return, constructor's map_err receiver and source/caller outward transfer. They
are additional complete 16-byte values, not bytes borrowed inside a live result.
The map_err's changed error type remains in the separately reserved whole
Result<u64,SwiftRunFailure> roles; no 16-byte role funds that 1096-byte object.
No new large failure, budget or owner value is added to the chain.

All other layouts, all 24 phase groups and their field inventories are compared
to the immutable C2 map. Only the two construction borrow fields change size.
Cleanup remains62096, same header62424, operation80566, foundation16504.
The six early whole-slot groups remain Control2/3=1352/1664,
Proof2/3=440/352, Adopted2/3=368/632. RootLeaf remains1632, CompletionBorrow192,
remove-live fault member560 and final tuple40. Foundation counts stay3 proof,
3 control,3 adopted,4 failure,4 usage,6 ticket,6 Optional WASI shapes. C2's full
source-to-slot branch map is preserved as a historical reference; independent C3
review must confirm these unchanged paths against this new source.

The exact admission boundary named test reruns with the new construction57224:
construction and operation exact-minus1/exact combined admission; header-minus1,
header, header+512Patch-minus1 and exact fixed-arena admission. No allocator is
called on a denied boundary. No foundation/root/control/WASI contract changes
are made by this candidate.
