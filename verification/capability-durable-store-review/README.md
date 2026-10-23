# Independent durable-store foundation review

Final target: owner candidate 2, source manifest
`8e75b805bb82b0c31174a2ffee992b24be207fd6c60c4ee316b9af5c46198376`.
The five new production/test files use dependencies exported from Git
`3bdf5cd4dc32842f3a9b876d473320c54f36731f`. This review qualifies the private
store/pool foundation; it does not qualify its future composition with the owned
adapter lifecycle SPI, a coordinator, selection, effects or health authority.

Two actionable lifetime defects were reported before the final freeze and fixed
by the owner:

1. Concurrent store and adapter retirement could release the outer slot while
   the first retained owner's destructor was blocked. The original direct-library
   probe records `occupied=15 released=true extra_admitted=true`, exiting 1.
   Per-kind retiring flags now join both destructions and prevent replacement
   adapter admission during a previous adapter's destruction.
2. An owned append snapshot could remain in its async ingress frame after the
   actor operation returned, while close retired the outer slot. A clearly
   labelled derived-only gate reproduced `occupied=15 released=true
   ordinary_busy=true extra_admitted=true`, exiting 1. Owned inputs now live in
   inner helpers; actual I/O close joins all ordinary/cancellation ingress tails
   before retiring the store obligation.

The exact original negative probe source, captured production source, derivation,
commands and outputs are preserved in `negative-concurrent-retirement` and
`negative-ingress-tail`. `development-functional` preserves the first successful
harness compile. Candidate 1's 24 positive probe executions remain preliminary
historical evidence. Candidate 2 repeats the same 24 executions after the owner
also clears closed in-memory raw state following diagnostic publication.

`review.py` uses retained products and direct `swiftc` links. It creates no
SwiftPM graph. In each of debug, optimized release and TSan, it runs eight original
cases: both destructor-retirement orders, adapter replacement, uncertain stage
commits before/after state rename, exact signed raw bytes with monotonic high-water
preservation after cancel/reopen, cancellation plus close with a retained actual
native-validation result, embedded-host mismatch without reset, and the derived
owned-ingress-tail regression. The functional probe uses independently authored
Wasm, signing context and envelopes. Only the inert installed descriptor and
bridge material templates are reused as pinned inputs. File operations and
validate-only calls are real; callbacks/barriers inject scheduling or explicit
durability errors around those operations.

```sh
python3 -B verification/capability-durable-store-review/review.py --name FRESH-NAME --owner verification/capability-durable-store/2026-10-23-candidate-2/receipt.json
```

The source review also checked admission before owned copies/actor hops,
generation no-wrap and object-identity operation retirement, cancellation before
commit entry, actual/uncertain outcomes after commit entry, closed state decoding,
identity/channel/installation matching, signed pending reauthorization, downward
native limits including zero memory pages, and lack of selection/health/execution
ingress. Persisted structural health fields do not become health evidence here.
The final audit binds prior independently reviewed private I/O and sealed v3 SPI
evidence only where supporting source hashes match.

An obligation's `retire` remains a trusted internal assertion of actual resource
retirement; the API does not prove reference uniqueness. The review checks logical
owned frames and reservation-retained owner release, not Task object destruction,
allocator reclamation or a process RSS/OOM bound. TSan excludes Rust/framework
internals. Cross modules are owner evidence, not device execution. There are no
device, app linkage, activation, release, publication, signing or GA claims.
