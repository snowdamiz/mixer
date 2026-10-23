# Fixed host bridge contract

This is a verification-only native object in `CMixerUIAndroidHostBridge`. It can
produce only host-domain evidence. The transport source and its ABI are unchanged.

`mxis_host_slot_acquire(facade, entry, out_generation)` first validates the exact
active C lease. Under its fixed sixteen-slot mutex it finds the same facade or
allocates a free slot, issues a checked positive generation and allocates one
bounded tree buffer, listener record and weak-owner record. Allocation failure
fails closed; partial allocation is freed before publication. Missing state after
publication is never converted to empty. No success or scope argument exists.

`mxis_host_inspect(facade, entry, out_snapshot)` validates the exact active lease,
then copies the actual slot's scalar facade/generation, last final entry, live
allocation counts and published/cleared disposition. It does not mint evidence.

The frozen `mxis_apply`, `mxis_interaction` and `mxis_retire` validate their lease
before native lookup. Apply copies at most 65,536 bytes to the bounded tree.
Nonfinal retire clears the tree and listener state while retaining its weak-owner
record. Final retire frees the tree, listener and weak-owner allocations and
records that exact final entry. Its OK means those concrete operations returned.

`mxis_host_release_destroyed(facade, generation)` runs only from the actual Swift
resource owner's destructor after final cleanup and actual C facade reclaim. It
requires the exact already-cleared generation and no live allocations, then frees
only the scalar slot. It cannot mint cleanup or retirement evidence, reset IDs or
clear a fault. The test fixture may block this real destructor call to observe
that the outer reservation remains occupied until the call returns.

All fixture failure/hold instrumentation lives only in verification objects.
No product callback setters, injectable driver, caller success flags or JNI/native
witness conversions are supplied. Host pthread/pump execution is not Android
main-Looper or Java-stack qualification.

## Permanent uncertain-obligation retention

The standalone host final gate has sixteen separate fixed cells, each retaining
only an exact facade ID and the already-issued presentation obligation. The cell
is preclaimed immediately after paired Swift/C facade acquisition and before any
resource publication. It adds no direct resource owner reference. The same Swift
facade reservation stays occupied until the cell clears, so a new facade cannot
replace an occupied different identity.

Quarantine or abandoned prepared/binding shells leave the cell permanently held.
This matters because a quarantined outer pool count alone does not keep an ARC
reservation alive: the gate must preserve the actual reservation/resource chain.
Finalization removes weak lookup only after exact final cleanup, actual Task/native
joins and C facade reclaim, while keeping its Swift reservation tombstone. It then
calls the obligation's actual `retire()` and waits for the retained resource's
real destructor to return. Only then may it clear the exact final-gate cell and
release the Swift facade reservation. No uncertain retry, extra resource alias or
destructor-based asynchronous cleanup is added.
