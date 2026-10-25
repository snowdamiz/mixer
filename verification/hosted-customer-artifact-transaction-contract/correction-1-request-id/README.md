# Request ID and facade API correction

Root review corrected two proposal errors: the frozen facade uses
`MixerHosted.Authorization.with_authorized_transaction/4,5`, and its server request
ID is exactly 32 lowercase hexadecimal characters encoding 16 cryptographically
random bytes. It does not use a UUID request ID. The proposed v2 event field is
therefore `server_request_id`.

The live contract contains only these narrow API/metadata/schema corrections.
Its storage, policy, audit semantics and 35 pending implementation cases are
unchanged. No product implementation is authorized or accepted by this packet.

`prior/` preserves all five artifacts named by the original receipt plus the
original receipt itself, byte for byte. `prior/document.md` preserves the original
sealed proposal. The original top-level `receipt.json` also remains unchanged;
its document digest describes this archived original, not the corrected live
document. This correction's separate receipt binds the corrected document and
the exact reviewable diff without replacing or falsifying the original seal.

Validate both seals and the narrow correction:

```sh
python3 -B verification/hosted-customer-artifact-transaction-contract/correction-1-request-id/verify_correction.py
```

Product case results remain zero passed and 35 pending. The original packet
runner validates the live proposal structure only; it does not establish the
old document seal. Use this correction checker to verify the historical seal and
the corrected document together.
