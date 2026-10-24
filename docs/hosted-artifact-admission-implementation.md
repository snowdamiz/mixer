# Hosted v3 artifact admission implementation

Producer evidence is complete for the bounded overlay. Independent semantic
review and root acceptance are pending. No live hosted source is changed by
this packet. The frozen boundary is
[the root contract](hosted-artifact-admission-contract.md); the product plan
remains binding.

The proposed internal API is `MixerHosted.Protocol.ArtifactAdmission.admit/4`:
exact envelope bytes, a trusted string-keyed host map, trusted root maps with
raw 32-byte public keys, and an integer uint64 verification time. Success returns
`%ArtifactAdmission.Checked{}` with original bounded envelope bytes, the exact
embedded signed JSON value bytes, checked manifest values, canonical CBOR,
signature, payload, both hashes and the signed scope/runtime/digest target.
Failure returns fixed closed atoms without input or key values.

`admit_signed/5` separately accepts a complete standalone signed document and
raw payload. It retains all standalone whitespace and returns checked data,
without an upload `Checked` record or a fabricated original envelope.
`recheck/4` takes a `Checked`, current host/roots/time and reconstructs it from
its retained actual envelope bytes. Every field must equal the fresh result.
A caller-edited struct, a success flag, an old root authorization or old host
policy cannot substitute for this check. This is API discipline within trusted
BEAM code; independently constructing the exact equivalent of a valid artifact
can still pass because its actual bytes are valid. No object authenticity or
in-process adversary boundary is claimed.

Three new production modules are included: `ArtifactJSON`, `ArtifactV3Policy`
and `ArtifactAdmission`, plus one test module. The accepted `ArtifactCBOR`
source is byte-identical. No dependency is added and no identity helper,
Application, router, configuration, migration, key owner, signer or provider is
changed. The root-approved overlay is retained under
`verification/hosted-artifact-admission-implementation/overlay/`; `source.patch`
adds exactly those four files.

The owned lexical walk precedes Jason. It enforces depth 16, 256 entries per
container, 4,096 structural items including map keys/containers, exact uint64
numeric tokens, and bounded original envelope/signed spans. It scans long
strings without constructing a character list; Jason subsequently checks full
JSON/Unicode syntax. Ordered decoded object members remain ordered until
escaped-equivalent duplicate checks finish. No untrusted atom creation occurs.
Only integer tokens are accepted; fractions, exponents, negatives and overflow
reject. Schema and full host/root/grant semantics then apply independently.
Canonical padded base64 alphabet, byte arithmetic and zero unused tail bits
are checked before decoded-byte allocation; the exact round trip is also
checked. The complete root collection is validated before key selection.
Standard OTP Ed25519 verifies the existing v3 domain and accepted CBOR; payload
length/SHA-256 are independently checked. Creation time stays an audit value.

The authoritative producer replay is `run-2/receipt.json`. Its source archive
contains the exact accepted revision
`4586bb901b980e9beeca5f7bb826f8b62140a3b4` hosted/protocol sources plus the four
new overlay files; `sourceInputs` identifies every compiled/tested source in
that closure. `collectorInputs` binds the Go comparison tool, Elixir observation
tool, replay collector and root freeze. Twenty existing dependency archives
were verified against accepted `mix.lock` hashes and installed offline. The
unfinished key-owner/dependency changes in the active checkout are excluded.
The earlier focused attempt and `run-1` remain retained.

Executable results:

- 154 original raw signed-manifest cases, 39 original origin cases, 14 original
  namespace cases and the original valid signed fixture have identical input
  hashes and verdicts in Go and Elixir: 208 comparisons. No original fixture
  is rewritten. The 36 assignment cases are explicitly outside this component.
- Synthetic tests exercise exact/one-over 64 KiB signed documents, 4 MiB
  decoded payloads, and 6 MiB envelopes including whitespace; structural work
  limits; closed fields/types/case/null; duplicate/escaped names; invalid
  Unicode/numeric/base64 forms; current host/root validity and revocation;
  wrong key/domain/signature; payload mutation; and changed retained fields.
  Generated signatures use ephemeral process-local test keys. Existing public
  deterministic fixture keys remain test-only and no private key is retained.
- The accepted hosted suite passes 44 tests, including the nine new test
  groups. Its unchanged collector builds a production release, exercises the
  accepted foundation's disposable loopback PostgreSQL/Phoenix/Bandit tests,
  and cleans its fixture. This does not add artifact HTTP or storage tests.
  The owned Go protocol regression suite also passes.

`parser-observations.json` records seven separate process observations, exact
input hashes, elapsed time, reductions, before/after process memory, sampled
process memory and referenced binary sizes. The large string is linear work;
excess depth, oversized integers and one-over whole-body size reject early.
The 4,096-item boundary accepts and 4,097 rejects. These are observations on
this macOS/OTP environment. Input already exists before measurement. Process
heap/stack samples exclude native allocator costs, shared/off-heap binaries
and unsampled transients. No hard total allocation, RSS, concurrent-request or
deployment capacity limit follows. HTTP must still bound streaming bytes and
concurrent requests before body assembly.

Run `python3 verification/hosted-artifact-admission-implementation/verify.py`
to verify the sealed packet; `run.py` creates a new append-only offline replay.
The seal verifies exact source closure, unchanged accepted files and fixtures,
new-file-only patch, replay output hashes, Go/Elixir case equivalence, full
hosted/production outcomes and cleanup. It is a producer integrity seal, not
independent acceptance.

Tenant authorization, repository transactions/current-policy lookup, private
artifact HTTP routes, PostgreSQL artifact/audit/idempotency persistence, blob
storage, hosted providers, Linux CI, native signed activation and all GA gates
remain pending their own implementation/receipts. Physical phones are deferred;
this lane is host-only and starts no simulator/emulator. The membership/storage
writer must wait for root acceptance before consuming this component.
