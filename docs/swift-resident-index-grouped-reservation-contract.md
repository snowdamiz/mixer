# Resident index reservation ownership

The integrated private Swift cache retains a 192-byte resident index in a fourth
vector allocation. Its separate reservation ticket leaves no spare ticket after
Initialize in the last full reactor attempt. That run fails when a later owner
requests ticket 87 against the unchanged limit of 86. The exact requesting owner
was not observed. This contract defines the narrow storage correction to evaluate;
it does not accept a candidate or select another full reactor run.

Keep the existing index vector, its 128 bucket heads and 64 links, allocation
request and byte-by-byte metered initialization. Include its 192-byte payload
exactly once in the cache header reservation, using checked arithmetic. Admit
that reservation before any index allocation. Remove only the separate fourth
buffer ticket, leaving the three other buffer reservations independent. The
reported fixed reservation must include the payload through the header without
adding it a second time. Recompute all affected owner, return-slot, construction,
operation, cleanup and foundation inventories from their actual types.

On partial construction failure, explicitly destroy the index vector while the
header is still charged, before destroying the partial owner and releasing that
header. On consuming cleanup, explicitly destroy the index vector before moving
the header into the existing cleanup tail. The header must remain charged until
the caller's existing completion boundary has consumed the owner and return
storage. No release-before-drop, hidden copy, uncharged array initialization or
new fallback allocation is permitted. Failure before header admission leaves
only the existing empty vector value and existing construction accounting.

Lookup, hashing, full-chain validation, mutation admission, LRU selection, pins,
nonces, corruption rejection and the shared Frozen cache trace remain unchanged.
The constructor retains its 832 charged work steps for the selected finite
fixture and four actual buffer allocation requests. A removed reservation
admission may remove its corresponding cancellation checkpoint; every remaining
prefix and checkpoint must still clean up correctly. All production limits,
including 86 tickets and 64 cache residents, remain unchanged.

Acceptance needs source-bound tests of the actual cache and runtime owner:
allocation failure, header refusal, each shorter work/cancellation prefix,
partial and successful consuming cleanup, exact payload accounting, full cache
population, a real additional admission at ticket 86 and refusal at ticket 87.
Retain the initial accounting-expectation failures; update only expectations
that follow from the changed ownership. Run existing private cache, execution,
lifecycle and shared-cache regression controls and independent review before
live integration. Keep diagnosis-only instrumentation out of the product delta.

Finite headroom evidence does not predict complete FieldLog execution. A later
full reactor attempt requires a fresh source and binary binding with the original
harness, workload and limits. Native, public/signed, immutable published FieldLog,
physical-device, operational and GA acceptance remain separate and pending.
