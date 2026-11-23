# Private signed F11 note replay

The replay uses the restored Pair25 F11 workspace and the real signed
capability owner, Rust Wasm VM, macOS input router, and reconciled
`MixerUIHost`. The replay observes the initial host display ticket
headlessly. The guest copies the bytes from the accepted edit event
into the revision 2 frame. Both revisions preserve the original four
line feeds, combining mark, emoji sequence, and Japanese text.

Pass the read-only Stage checkout at `1ca46eb93e`, the local FieldLog
Git checkout containing the three F11 source anchors, and the F04 and
F11 recipe directories. The worker reconstructs the pinned F04 source
from the retained overlay, checks the exact tree and writes scratch
under `/private/tmp` so the input checkout stays read-only. It verifies
the Pair25 tree and all three corpus anchors. The offline replay uses arm64 macOS, Swift, Rust
1.99.0, the local SwiftPM and Cargo caches, and the Embedded Swift 6.3.3
Clang and Wasm linker.

```sh
python3 -B tests/integration/fieldlog-d8-f11-vertical-private/replay.py \
  "$stage" "$fieldlog" "$f04_recipe" "$f11_recipe"
```

The receipt records signed wrong-field and wrong-action refusals and
one accepted and delivered edit from the current attachment. The guest
attempts to mutate the real note key during that edit. The pinned
repository observes zero write calls and byte-identical workspace
contents. All three owners must retire. The worker checks all 11 stock
CBOR and fingerprint vectors and the existing V1 and F04 codec
boundaries. Earlier stock offline deadline and retirement failures
remain separate historical observations.

The next F11 integration is action-bound Save draft and Commit entry.
It needs one-shot host authority for the exact displayed note and
workspace revision, followed by cold readback of the saved draft and
the linked commit outbox event. This replay covers the headless macOS
host and uses in-memory fixture signing keys.
