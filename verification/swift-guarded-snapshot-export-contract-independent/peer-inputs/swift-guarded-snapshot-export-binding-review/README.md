# Frozen binding and encoding contract review

Scope: bounded independent source/data review of the proposed exporter contract
released by the root at producer seal SHA256
`7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe`.
This review selects no IDs, private API, budget or executable implementation.

## Finding requiring contract correction

**B01 / P2: the actual session's first identity is Source, not Executable.**
`swift-guarded-snapshot-export-preparation/contract.md:44` says MIXLSE01's
first section is a 64-byte executable identity. The accepted loader constructs
`identities` in Source/Build/Session/Executable order at
`inputs/accepted-source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs:932`.
At line 1045 it compares the first session section with `identities[0].encode()`
and also compares `s.source_bytes` with `identities[0].bytes`. Thus that section
contains the **Source File identity**. The Executable File identity is index 3;
the session's separate fixed-header executable field holds its SHA256 bytes,
checked against the retained executable at lines 1072-1075.

Replace "64-byte executable identity" with "64-byte source File identity".
Keep the proposed MIXLPR01 four-role order unchanged. Otherwise a later custody
join implemented from the prose could require the wrong File identity or confuse
the source identity section with the executable digest. There is no implemented
exporter here, so this is a concrete proposal defect, not a current execution
authority bypass. Correct and refreeze the proposal before selecting it.

## Other observations

The statement at contract line 43 that the loader "checks 144 source and 11
support members" should be read narrowly: `parse_build` checks the two counts,
and `load_inner` hashes the complete retained manifest and compares it to the
embedded compile identity. The loader does not open and rehash those 155 source
and support files at runtime. The review separately checked all 144 copied
accepted members against their supplied source manifest. This distinction is
not a new loader defect; clearer wording would prevent a custody overclaim.

The finite model names all six retained 32-byte fields `DIGESTS` and calls them
"Six digests" in a comment, although the sixth is the nonce. Contract lines
49-54 and the actual loader correctly retain the nonce as bytes, independently
compare it with the process observation, and do not hash or sign it. A neutral
`RETAINED_VALUES` label would match that contract. No nonce-derived authority was
found.

The source audit found all six private snapshot proof fields represented, and
records the 34 explicit proposed wire IDs against the accepted `WasiFunction::ALL`
order in `audit-result.json`. Validation's five limits, the later runtime's 17
limits, seven optional WASI limits, and five grants are distinct and in the actual
source declaration order. The opaque provenance's retained field order and
Source/Build/Session/Executable identity order match MIXLPR01; negative timestamps
retain the exact u64 bit pattern. The build/compiler/version digest ordering is
intentional and consistent with the source.

Source review also confirms the original sole guard literal follows phase
completion and successful inspection; header encoding precedes row writing;
the eight outcome variants retain their original inline typed payloads. The
proposed bridge gets proof and selected provenance from that same cache, bounds
returned references by the guard borrow, accepts no callback, and explicitly
returns PreparationOnly. Its compile prototype does not implement runtime/WASI
observation production, the outer export observation, same-owner serialized joins,
or any writer. No working-exporter behavior or future cleanup correctness is
inferred from this source review. The main independent reviewer owns executable
format mutations and compiler/privacy verification; the accounting reviewer owns
storage/work ceilings and admission.

## Evidence and limits

Run `python3 verification/swift-guarded-snapshot-export-binding-review/review_binding.py`.
The bounded source/data assertions are review evidence only. No source analysis
authorizes OTA, execution, export, release or a GA gate. The Python audit writes
only its result in this new directory; it does not run the frozen producer
wrapper or any Rust/native program. The original 144-member accepted source copy
was verified unchanged. No product/canonical/Git edits, process inventories,
UI/capture or native runtime tests were performed. Paused and operational gates
remain pending. Loader process correlation and SHA256 matches remain trusted-local
evidence; returned File owners do not prove closing or immutable artifact custody.

The review's seal contains every owned review file except the seal itself. Its
hash is the handoff identity; the producer remains frozen and unmodified.
