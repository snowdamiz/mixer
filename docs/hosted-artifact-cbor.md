# Hosted artifact CBOR encoding

`MixerHosted.Protocol.ArtifactCBOR.encode/2` implements the existing Mixer
artifact data model in Elixir: UTF-8 text, unsigned 64-bit integers, booleans,
proper lists and text-keyed maps. It uses shortest definite-length encodings and
bytewise ordering of encoded map keys from
[RFC 8949 section 4.2.1](https://www.rfc-editor.org/rfc/rfc8949.html#section-4.2.1).
Text bytes are preserved without Unicode normalization. Nulls, negative numbers,
floats, structs, arbitrary atoms, nontext keys and invalid UTF-8 fail closed.

The existing repository-owned Go encoder and shared signed v3 fixture define the
wire compatibility target. No new library or external implementation is used.
The Elixir tests compare the complete manifest, assignment and capability grant
descriptor bytes, both signature preimages, the artifact digest and descriptor
digest. OTP's Ed25519 verifier checks the existing public test signatures over
those exact bytes and rejects a modified preimage. This does not implement
signature admission, root policy, schema validation or any upload route.

Each call has at most 65,536 output bytes, 256 entries per container, 4,096 total
items (including containers and map keys), and depth 16 with the root at zero.
Callers can lower the output budget. These limits fit the bounded v3 artifact
shape; they do not change the shared wire format or make every encodable value
a valid manifest. The byte budget is checked before scanning text. List length
checks stop at the first excessive cons cell; map size is checked before
materializing pairs. Iodata avoids repeated concatenation of growing values.
These are work/output bounds, not a claim about total BEAM memory or the input
already allocated by a caller. HTTP body and JSON admission still need their
own limits before constructing values.

The focused tests cover integer/text boundaries, encoded-key ordering,
non-normalized Unicode, nested containers, invalid values and exact versus
excessive byte/item/depth/container limits. The hosted source collector now uses
schema 2 with repository-relative input/archive paths and includes the shared
fixture. Hosted CI also runs when that fixture changes. Historical schema-1
receipts retain their original meaning.

Local evidence lives in `verification/hosted-artifact-cbor/`. This component is a
dependency for the pending authenticated artifact service. Key ownership,
database authorization, payload/root admission, persistence, audit atomicity,
R2/Neon integration, publication and all relevant GA gates remain separate work.
