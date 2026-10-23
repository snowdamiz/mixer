# Guest capability transport development contract

[`../../contracts/guest-capability-transport-v1.json`](../../contracts/guest-capability-transport-v1.json)
publishes the proposed six import signatures and value transport for guest ABI 2,
wrapper ABI 1. It is a **development contract**, not import admission or implemented
runtime transport. It changes no existing profile, SDK, VM, C header, identity,
release protocol or activation behavior. Identity/release version migrations are
still proposals. Native exit observation and the standalone Rust mailbox have
separate implementation/review evidence; this receipt does not qualify either.

The contract fixes all four operation/result/schema-hash bindings, argument objects,
closed completion variants, strict JSON bounds, Unicode/numeric/base64 rules and
the proposed reusable public codec API. An enum chooses exactly four operations;
there is no arbitrary capability/hash/operation string API. Existing envelopes and
their hashes are preserved. The bridge must first validate a real native completion
with `CapabilityCodec.decodeCompletion(expected: actualCall)` before converting it.

`cases.json` indexes 90 original plain fixture files, with exact source bytes,
SHA-256, fixed operation context, expected acceptance and expected meaning. Keep
the raw files: parsing and reserializing a negative fixture can erase its defect.
Well-formed Unicode carried as base64 remains opaque application data. Escaped
duplicate keys, lone surrogates, non-ASCII identifiers, invalid numeric spellings,
base64 padding/pad-bit errors and decoded-size boundaries are distinct cases.

The codec and native policy remain distinct. The positive
`get-missing-nonempty-type-valid` fixture preserves the existing codec's acceptance
of `found=false` with nonempty canonical value bytes. `http-302-type-valid` preserves
the HTTPResponse type's 100...599 range, while the actual host separately rejects
3xx/redirects. `committed=false` is a valid mutation result. These fixtures prevent
the future transport codec from inventing new cross-field restrictions.

Run the offline oracle from the repository root:

```sh
python3 verification/guest-capability-contract/verify.py
```

The runner checks pinned source/fixture hashes, records tools/revision/tree/input
digests, and builds the **existing** `capability-probe` public consumer in a local
ignored `.build/`. It inserts raw argument/outcome bytes into existing capability
call/completion envelopes and invokes `CapabilityCodec` through that public probe.
It does not implement a mirrored wrapper validator. Public input validation and
strict roundtrip behavior therefore come from existing independently authored SDK
code, including its original JSON preflight, rather than a new regex-only test.

The observed scope in [`run/receipt.json`](run/receipt.json) is:

- 67 existing-codec projections executed and matched their expected acceptance.
- 23 new-contract cases remain pending and **were not executed**: 21 wrapper
  fixtures and two standalone argument-message byte-boundary fixtures.
- The old envelope adds metadata, bytes and depth. Passing a projection does not
  prove the proposed standalone argument API, wrapper decoder, import routing,
  mailbox ownership, native I/O, grant binding or activation works.

The two standalone payload fixtures contain exactly 524,288 and 524,289 UTF-8
bytes, including internal JSON whitespace. The former is contract-valid and the
latter exceeds the transport limit. An old full-envelope decoder cannot qualify
these new API boundaries because adding its required metadata changes byte size.
They remain pending until the actual new codec API exists. Wrong wrapper ABI,
hash/operation, unknown/session fields and rejected-outcome cases likewise have
expected meanings without any claim that a wrapper implementation ran.

The receipt preserves exact commands, source manifest and output hashes. Its
`existing-envelope-expected-calls/` files are trusted oracle scaffolding containing
legacy host identity; they are **not** new guest payload fixtures. No session UUID,
slot/generation or guest token is present in valid new argument/wrapper payloads.
Failed commands/mismatches must remain visible; never relabel pending fixtures as
passes. Before rerunning after source changes, review and re-anchor the contract
rather than bypassing the source digest check.

No devices were used. This is not full Swift async, physical iOS/Android, immutable
published-package consumer, store, production publication or GA evidence.
