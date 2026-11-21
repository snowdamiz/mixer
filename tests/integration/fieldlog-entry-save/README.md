# FieldLog entry save rehearsal

This macOS host replay exports the Mixer runtime, fixture sources and signer
from the same Mixer HEAD commit. The runner checks its own bytes and executable
mode against that commit before creating scratch. The replay uses FieldLog at
`552559d2d3278abb9b1aa7dcf0288102c09a202b`. It applies the maintained Pair24
rollback floor, optional-field successor and Android application composition
before applying [the decision overlay](entry-save-decision.patch). The replay
copies [EntrySaveDecision.swift](EntrySaveDecision.swift) into the downstream
FieldLogFeatures target and passes that same source to Embedded Swift.

The native intent projects Foundation's `.whitespacesAndNewlines` trim result,
the raw UTF-8 byte counts, presence of NUL and date finiteness from the live
draft. Its shared decision returns the first failing check in scope, title
size, commit requiredness, title NUL, note size, note NUL and date order.
The native save intent and `WorkspaceRepository` own persistence.

The decision lease uses the ordinary editor's selected draft binding and
requires the repository's committed revision to match the revision the editor
is showing. The guest checks the current editor draft with a fresh read after
each activation. The versioned key carries nine bytes in big-endian order.
The first two 32-bit words carry the title and note UTF-8 byte counts,
saturated at `UInt32.max`. Bits 0 through 5 of the last byte carry project
match, commit, blank title, title NUL, note NUL and valid date respectively.
Malformed date text for the selected draft clears the date bit, even when the
editor retains a finite parsed date. The guest keeps **Check entry** available
so the same lease can read the correction. The lease exposes only the facts
read. The guest drops the action if the read is stale or denied, or if the
facts packet is malformed.

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
date correction through the same action and lease, malformed facts, stale
input and selection, explicit owner retirement, and a cold repository reopen
with exact workspace and attachment bytes.

The durable Commit replay reopens an existing draft and stages edited fields
in the host. An accepted **Commit** action reads the nine-byte facts and the
guest polls that completion. The guest then sends a fixed `put` command. The
host consumes the private permit inside `WorkspaceRepository.transact` after
checking the selected draft and captured revision. The transaction calls
`EntrySaveIntent.apply`, and the host verifies `EntrySaveIntent.result` before
reporting success.

The signed single-put replay uses the admitted minimum of two request slots and
2 MiB of reservation. It cold-reads the exact title and note bytes, date, and
draft ID, with one new durable entry and its matching `entrySaved` outbox record.
A one-slot configuration at the same byte limit is refused before dispatch.
A separate guest uses four slots and 4 MiB for the facts lease and three puts.
It checks that a duplicate command and a changed payload both return
`permissionDenied`. A fresh signed minimum-budget owner retries the action
against the cold repository, which preserves the exact saved bytes.
Blank input, stale revision, close before mutation admission, and a guest that
issues the command before polling its facts leave the workspace untouched by
Commit. The single-put guest also displays **Commit refused** for a valid
`committed: false` completion. The replay checks retirement and zero live
transport allocations.

## Replay the ordinary Android entry editor

Run the signed fixture with the same host tools.

```sh
tests/integration/fieldlog-entry-save/run.sh android-editor
```

The runner applies the downstream overlay to the public FieldLog checkout and
checks both Git trees against `android-editor/pins.json`. It exports the
ordinary fixture, runtime and host transport from the same Mixer HEAD as the
other replay inputs. It signs the fixture with two request slots and a 2 MiB reservation.
It rejects a signed one-slot fixture and a signed fixture short by one byte.
Set `FIELDLOG_EDITOR_WASM_OUTPUT` to a fresh file path to retain the tested guest
module for Android development packaging.

In the development build, use **Open signed entry commit** on a saved draft,
then use **Commit** in the installed guest. The action captures the native
`EntrySaveIntent` and the revision that supplied its editor data. The host checks
that revision before it returns facts and again inside the repository transaction.
The app refreshes the editor after the signed owner closes.

The host replay injects a precommit fault at the real repository's
`before_write` hook after opening the signed editor. It checks that the guest
displays only **Commit refused** and that the **Done** equivalent joins owner
retirement and clears the host registration. A cold reopen checks the exact
workspace bytes, original drafts, and outbox.
