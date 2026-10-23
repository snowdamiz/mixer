# Independent capability authority contract review

No actionable contract contradiction was found in the frozen four JSON definitions
and companion design. This is a bounded read-only design review, with no production
or contract edits and no new runtime qualification. `receipt.json` records exact
input pins, unchanged legacy bytes, inspected implementation hashes, tool versions,
command and static consistency results. It does not authorize OTA or execution.

The execution definition is SHA256
`898ea22b93a5b0dcd94c3b54f7cc97c41a259cd2285cbacd54bf0bd52ba48c97`;
identity-v2 `d66c44d49f79325a643516f33bd19ba882ef711a5139afb54499b39931ba48b8`;
release-v3 `935c2311fb32a72d4b1e49ce55fd1c63f9f8448386a7076db48550767f6212f0`;
activation-v2 `e72c75d69e089cc3a23e09cc2f65e1902d9fc8f0bee401555507ec36d5e224d4`;
design `13b047877dd1ff842b4e8984335680805709ff7b6e5a7e2e7a9e033d46a136d9`.

| Boundary reviewed | Consistency conclusion |
| --- | --- |
| Old versus new authority | Old identity initializer remains schema1, old Go/Swift verifiers protocol1/2 + guestABI1, old activation rejects capability hashes/grants. New identity2/release3/guestABI2 is an explicitly selected route; no union/probe fallback is required. Eight old contract files match Git baseline `1ab4d4ee76a5d4ba206bd370cbeeeb73a7c6c636` byte for byte. |
| Hash and signature domains | New identity and artifact/assignment domains differ. New cross-references identify the same exact execution bytes; grant descriptor/object/hash, existing transport and both C headers remain fixed. Definitions omit mutable proposed/implemented/qualification-state fields; current status lives in the design. |
| Executable admission | Six capability import signatures/tags and two legacy imports agree with the existing guest/C route. The required same-config validation is stronger than metadata/inventory and must precede staging and concrete adapter initialization. Current bridge lacks its public standalone validator; the contract requires an additive API or equivalently checked private C use with the same single archive. |
| Resource narrowing | Native C/v3 permits an exact zero-page limit while current Swift configuration rejects it. Positive signed byte budgets can floor to zero. The normative definitions explicitly require exact same-config zero or pre-staging rejection, never rounding up; this is a prerequisite, not an existing bridge parity claim. Other fixed ceilings agree with the reviewed bounded route. |
| Installed material and grants | Immutable canonical role-bound files have closed shapes and finite bounds. The factory must consume the same hashed bytes to derive both policy and concrete adapters, intersect independent installed/signed grants and omit an empty-namespace storage adapter. Declared hashes plus arbitrary DTOs/objects cannot substitute. App-private constructor filesystem work is distinguished from guest dispatch. |
| Ownership and scheduling | One distinct native archive supplies both C families and the shared16 registry; the proposed package does not depend on the existing MixerActivation/MixerRuntime target. Separate one host-close Task and one native-close dispatch job match actual bridge ownership. Terminal/cancel/close is not exit; poison/quarantine may retain counted capacity. |
| Startup, effects and health | Startup remains defined, once and disabled; earlier unavailable requests never become dispatchable. Generation/cancel/deadline is rechecked at await/publication/enable boundaries. Provisional effects can precede earned durable health, so the permanent effects-open latch is separate from health and post-enable failure requires recovery, without automatic conflicting fallback. |
| Error classification | Existing C reports carry stable machine codes and outer statuses. The current Swift error surface does not preserve all typed classifier evidence. The required additive classifier uses checked code/status/context, treats unknown conservatively, preserves cancel/deadline/poison/resource distinctions and cannot infer deterministic traps from text or status2 alone. |
| Recovery and hosted versioning | Complete host equality and replay state remain binding. Old identity state is rejected instead of reset. Local schema3 is only a successful v3 write transition, with explicit variants and old readers rejecting3; current store supports1/2 only. PostgreSQL's opaque signed storage does not imply its application dispatch or schema review is complete. Hosted/signing changes remain separate work. |

The static script independently checks exact pins/references, eight preserved
inputs, additive field sets, closed objects, version/domain separation, exact
existing grants/imports, and consistent fixed quotas. Manual review additionally
examined implementation admission, private updater selection, actor/publication,
C report classification, one-archive dependencies, capture/embedding, local store
variants and PostgreSQL byte-storage boundaries. No broad build or duplicate
bridge/native execution was run. The separate frozen bridge review is untouched.

Complete graph capture and build consumption, final signed embedding, future
parsers/factory/coordinator, successful provisioned HTTPS, actual health and data
reconciliation, published external consumers, physical mobile and GA remain
unqualified. Phones were not queried or reconnected; no credentials, trust,
commits or pushes were changed.
