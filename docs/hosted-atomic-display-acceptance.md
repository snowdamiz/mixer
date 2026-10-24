# Retained display correction acceptance

Root accepts the isolated formatter correction for CR01. The prior valid-row
false rejection is resolved within the synthetic atomic-storage specimen.
The [independent review](hosted-atomic-display-review.md) freshly passes the
unchanged 88-case suite and its expanded 94-case suite, both without skips or
exclusions. Its separate standard-library oracle reconstructs 185 actual chain
rows and a corruption-control row. Root verified 625 review and 1,509 reviewed
input bindings and inspected the exact formatter and independent oracle.

The accepted codec SHA-256 is
`7152ab6d9c2fec56cd6e707ef09bb4f5fb3a8477edb7b0b5410a884278fe37ee`.
It formats validated source bytes directly, preserving UTF-8, literal escape
text, byte-based key ordering and PostgreSQL's exact string spelling. Stored
byte equality remains strict. SQL, CBOR, storage semantics and all original
assertions remain unchanged. This acceptance does not edit live hosted source.

All four producer and two reviewer owned environments were cleaned up. Original
failed assertions and the review checker's incorrect same-HEAD assumption remain
retained. Each successful review run records its actual Git revision and frozen
source digest; the intervening evidence commit changed no implementation input.

The separately required catalog/enforcement correction and complete current
identity/membership integration remain pending. This is not complete production
AS05, combined-schema, repository, migration, HTTP, cloud-provider, native or GA
acceptance. Actual deployment inspection must cover the authorization and domain
schema together before protected product traffic. The next approved work joins
the frozen authorization interfaces to the real transaction driver in isolation;
it does not publish this specimen as a service.

The decision and replayable verification command are in
`verification/hosted-atomic-storage-root-review/display-acceptance.json`.
