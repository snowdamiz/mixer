# Proposed narrow amendment: optional canonical-only source controls

This proposal supplements the root's frozen integration-source-inventory
amendment. It is not selected policy until root records a decision.

The compiled source-pair.5 product policy defines exactly eighteen Java subjects
and twenty-four adapter entries. Canonical source input requires every product
subject with its exact selected identity. In the containing canonical Java source
tree, allow only these additional explicitly named canonical-only files, each
independently optional:

- AppearanceDescriptorV1.java: 15,759 bytes, SHA256 `0b3afc54df5a8943d873c5ea3941d3843f233bf48ac9354b0ff1250d6017d009`.
- AppearanceResolutionV1.java: 16,316 bytes, SHA256 `c3737cbd05d71fb13cd4e105a212b67c946c4ebc9fbf020ba2e9bf5ceccf2934`.
- AdapterInstrumentation.java: 4,209 bytes, SHA256 `40e0d4643870aeee1c8ad5575aca89c1a026d7f243fe455c7920edde8fa1868c`.

The first two are retained legacy appearance control sources; the third remains
the separately labeled instrumentation probe. Pin these identities in a separate
compiled canonical-input-only policy. Do not add them to adapter_files, the
profile.5 serialized schema, product projection, product export, or generated
consumer compilation. A product-only copied source input remains valid. No
presence of an optional file can substitute for a missing product subject.

Before required-source content reads or lock/content hashing, enumerate and admit
the complete relevant source topology, including exact ASCII spelling, ordinary
directories/regular files, absence of symlinks and each present file's pinned
size. Reject every unknown sibling, case alias, redirected ancestor or wrong
file type before content access, tool discovery, staging or output. After all
layouts pass, bounded-read/hash every present optional file against the compiled
identity before export, tool discovery, staging or output, along with required
product sources. Hash failure is a source-compatibility refusal; a recomputed
local lock cannot authorize changed optional bytes. This phase ordering applies
equally to both legacy appearance sources and the excluded probe.

The generated/copied product tree remains closed to exactly the eighteen product
Java subjects. All three canonical-only extras are forbidden there, even when
their bytes are pinned and a generic lock is recomputed. Keep the driver build-only
and its exact product profile count/schema. The separate instrumentation
cross-build may consume the explicitly named probe in its recorded source closure;
that is not generated product qualification.

Preserve the five separately classified NativeRenderer V1 compiled positive
baselines, complete selected product host A/B, real callbacks, sixteen-family
case split, direct-editor descriptor/BCI audit, SDK/D8/generated consumers, both
SDK36 guards and direct-adapter descriptor review. The two legacy appearance
sources do not replace or satisfy those five renderer baseline obligations.
Fresh source/class/BCI bindings and independent review remain mandatory; this
inventory clarification grants no native, public V2, release, OTA or GA authority.
