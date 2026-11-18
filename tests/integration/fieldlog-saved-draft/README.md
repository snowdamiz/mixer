# Check an existing FieldLog draft

Apply [the downstream patch](fieldlog-552559d2-check-saved-draft.patch) to FieldLog commit
`552559d2d3278abb9b1aa7dcf0288102c09a202b`. Open a saved entry draft in the
ordinary iOS editor and choose **Check saved draft**. The action reads the
selected draft from the editor's open workspace repository and applies the same
title rule as **Save entry**. It displays the result without committing an
entry. Wait for any pending draft save to finish before checking.

The patch includes the prior optional-field schema and selected-draft storage
adapter so it applies directly to the pinned FieldLog source. On a branch that
already carries those changes, reuse its repository and reconcile the overlapping
hunks. The check only needs the repository read and the shared title rule.

## Replay on macOS

Use Xcode's host Swift, Swift 6.3.3 with Embedded Wasm tools, and Rust with the
macOS host target. Supply three local Git checkouts containing the pinned
FieldLog, Swift Crypto 5.0.3 and Swift ASN.1 1.7.3 commits. The runner reads
committed files into a disposable directory and removes it on exit.

```sh
tests/integration/fieldlog-saved-draft/run.sh \
  "$FIELDLOG_CHECKOUT" "$SWIFT_CRYPTO_CHECKOUT" "$SWIFT_ASN1_CHECKOUT"
```

Set `FIELDLOG_GUEST_BIN` or `FIELDLOG_RUST_BIN` if your toolchains live outside
the defaults in the script. The replay stages releases directly into the
installed host owner. It uses no network service or account.

The replay calls the exact iOS workspace-model action against a real saved draft
with a linked JPEG and an existing outbox record. On the same open repository,
it also drives the signed guest's rendered action through the installed owner
and host transport. Each check must issue one fresh storage read and publish a
new frame. The deliberately defective signed baseline accepts a whitespace-only
title. The corrected and rollback guests reject it. The optional guest toggles
the follow-up field on, then off after rollback. A fresh process with no staging
call recovers the final field value. The replay compares the full workspace,
JPEG bytes and file identity and checks storage call counts. Only the
follow-up edits may advance the workspace revision.

## Mobile boundary

The iOS editor's check uses native FieldLog validation. The signed release
replay uses the Android Guest UI V1 host transport with synthetic display and
input witnesses on macOS. Mobile signed presentation requires binding
`selected-draft` to the opened draft and the existing workspace actor in the
installed owner for each target, then verifying the native tap and result.
Android's ordinary editor uses separate downstream model and repository targets.
