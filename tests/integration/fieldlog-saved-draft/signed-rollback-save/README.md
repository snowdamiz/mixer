# Replay an ordinary FieldLog draft save during signed rollback

Use an arm64 Mac with Xcode 27.2, Rust 1.99.0, and Embedded Swift 6.3.3.
Have the VM's locked Cargo dependencies available in the local cache.
Supply local Git checkouts containing the pinned commits.

| Checkout | Commit |
| --- | --- |
| FieldLog | `552559d2d3278abb9b1aa7dcf0288102c09a202b` |
| Swift Crypto | `c2cbadd7263439d8015189668f96ff5b5be565ce` |
| Swift ASN.1 | `3b6410f7dee09eb33cdd26260c5fd47fda19b0e2` |

Run this command from the Mixer root.

```sh
tests/integration/fieldlog-saved-draft/signed-rollback-save/run.sh \
	"$FIELDLOG_CHECKOUT" "$SWIFT_CRYPTO_CHECKOUT" "$SWIFT_ASN1_CHECKOUT"
```

Set `FIELDLOG_SWIFT_BIN` or `FIELDLOG_RUST_BIN` if your toolchains use other paths.
The runner exports Mixer `dbb9275d58e1a2824c35870767551d2d9c8588bb` and checks
each FieldLog patch step against the Apple editor recipe. It builds the candidate
tree `380e764598c31181d16ef2fbb91c95bf95693375` and removes its private
workspace on exit. In the pinned Mixer revision, the recipe is at
`tests/integration/fieldlog-entry-save/apple-editor/README.md`.

The signer creates an in-memory development key and reuses the exact signed
artifact at sequences 2 and 4. It reuses the optional artifact at sequences
3 and 5. Look for these phase results in the runner output.

1. The installed owner activates the prior compatible guest at sequence 2.
2. The signed optional guest sets follow-up to `true`, advancing the workspace
   from revision 2 to 3. The editor still has its earlier copy of the draft.
3. The owner activates the prior guest at sequence 4. The ordinary editor's
   `scheduleDraft` callback changes the note while that same guest launch stays
   healthy. The save advances the workspace to revision 4 and retains follow-up.
4. A fresh process opens the same workspace and recovers revision 4. It starts
   sequence 4 from disk without staging, stages sequence 5, and observes
   **Follow-up required**. The unrelated draft, existing outbox, and linked JPEG
   remain intact. The workspace gains one write from the optional action and one
   from the ordinary save.

The headless fixture acknowledges the owner's actual presentation ticket and
routes the optional action through the presentation handler. Both observations
use test witnesses. Device UI, installed native-binary downgrade, and unknown
schemas remain outside the replay's scope.
