# FieldLog entry save decision rehearsal

This macOS host replay uses public Mixer v74 at
`44aecbeb6a82a4a93321cff6a8ab86c5aa421900` and FieldLog at
`552559d2d3278abb9b1aa7dcf0288102c09a202b`. It applies the maintained Pair24
rollback floor, optional-field successor and Android application composition
before applying [the decision overlay](entry-save-decision.patch). The replay
copies [EntrySaveDecision.swift](EntrySaveDecision.swift) into the downstream
FieldLogFeatures target and passes that same source to Embedded Swift.

The native intent projects Foundation's `.whitespacesAndNewlines` trim result,
the raw UTF-8 byte counts, presence of NUL and date finiteness from the live
draft. Its shared decision returns the first failing check in scope, title
size, commit requiredness, title NUL, note size, note NUL and date order.
The native reducer and its repository transaction still own persistence.

The decision lease uses the ordinary editor's selected draft binding and
requires the repository's committed revision to match the revision the editor
is showing. The guest checks the current editor draft with a fresh read after
each activation. The versioned key carries nine bytes in big-endian order.
The first two 32-bit words carry the title and note UTF-8 byte counts,
saturated at `UInt32.max`. Bits 0 through 5 of the last byte carry project
match, commit, blank title, title NUL, note NUL and finite date respectively.
The lease exposes only the facts read. The guest drops the
action if the read is stale, denied or malformed.

Run with host Swift, Python 3, Rust and Embedded Swift 6.3.3 on arm64 macOS.
The runner fetches the pinned FieldLog source and public Swift dependencies
into fresh scratch and removes it on exit. Set
`FIELDLOG_PINNED_GIT_REPOSITORY` to read the pin from a local Git repository.
Toolchain paths can be overridden with `FIELDLOG_GUEST_BIN` and
`FIELDLOG_RUST_BIN`.

```sh
tests/integration/fieldlog-entry-save/run.sh
```

The replay checks the native reducer and staged, signed Guest UI V1 owner
through the maintained host transport. It verifies Foundation's U+200B and
U+FEFF behavior, raw UTF-8 boundaries, mixed-invalid precedence, malformed
facts, stale input and selection, explicit owner retirement, and a cold
repository reopen with exact workspace and attachment bytes. The native
positive control observes effect admission and the guest positive control
observes eligibility. Durable guest Commit and its replay/outbox and joined
retirement behavior require the next integration unit.
