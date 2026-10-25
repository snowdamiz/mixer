# Independent fixed4992 Settings diagnostic review

The isolated fixed4992 derivative is accepted for its reviewed source and host
consistency scope. No actionable defect was found in the two endpoint changes.
The exact four current UIKit/XCTest sources also pass a fresh complete
simulator-target typecheck. A generic runner build and native execution still
require a separate source-bound root selection.

The producer handoff SHA-256 is
`2d01866f3fa0f88b283ba8f2774f03092eb93d9616daeaa7d5d2875618cf6748`.
All 176 handoff members match. The reviewed source archive SHA-256 is
`585f44532cb67ca626ae7c2c95bfa7030408bf2b4dc57f5bac0fdbd84cea66af`;
it contains 97 regular members. Independent comparison against both pinned
original archives confirms 72 source members, exactly two changed endpoints,
and 70 byte-identical sources. The original application, library, importer,
oracle, transport, failure diagnostic, public capture/action code, witnesses,
termination/completion and attachment paths remain byte-identical.

`verification/apple-settings-fixed-chunk-review/independent-endpoint-diff.patch`
is independently generated from the frozen originals. The receiver changes
only CHUNK, the closed exact-integer start shape/echo, index bound and encoded
chunk bound. The Swift change adds the fixed chunk size and CoreFoundation
integer/Boolean discrimination, start request/echo validation, slash-preserving
serialization and chunk packing. The actual original body guard was already
8,192 bytes and remains 8,192. Request/response/file/aggregate/event/upload/poll
limits, 29-second session rules, two-second request ceiling, anchored
three-second observation rule and sticky first failure remain unchanged.

The review executes seven newly written receiver test methods with 99 detailed
controls. It uses the actual reviewed Session, TransactionStore and replay code.
The producer's synthetic Flow data constructor is copied byte-for-byte and
explicitly shared; the expected results, mutations and fault injections are
independently written. No producer test suite or 758-field mutation loop is
rerun. Receiver controls cover:

- Exact JSON integer agreement; missing, Boolean, floating/exponent, string,
  null and wrong formats; duplicate start and old/new endpoint mixtures;
  rejection without accepted state, journal or payload advancement.
- Actual descriptor admission, ordered fragments, exact decoded lengths and
  padding, publication and durable replay for AX sizes 1, 4,991, 4,992, 4,993,
  multiples and 200,000, and valid synthetic PNGs at full/partial boundaries,
  multiples and 2,000,000. Every published byte and digest matches.
- Old/mixed fragment lengths; reordered/duplicate/wrong-slot fragments;
  descriptor/generation mismatches; per-chunk format fields; malformed,
  padded/noncanonical base64; partial payloads, digest mismatch and malformed
  PNG/UTF-8/NUL AX. Rejection preserves the accepted cursor and a valid final
  fragment can subsequently commit at the same cursor.
- Complete strict synthetic proof for tap and no-tap, seven-route-AX proof
  with an allowed retry, route search/tap/opened binding, fresh parent/leaf/action
  binding, capture/terminal files, termination and all completion markers.
  Independent semantic mutations and omitted phases cannot satisfy the full
  strict proof. An enabled sample exactly at the anchored three-second boundary
  qualifies; the next binary64 value beyond it does not. A changed durable
  AX file rejects replay.
- Host and runner deadlines, request/event/upload/aggregate/poll caps, unchanged
  before-app-begin preconditions, and finite uptime extrema without narrowing
  admission.
- Real filesystem payload/journal/publication-directory failures roll back
  without cursor advancement and permit an exact retry. Postcommit retirement
  failure preserves the committed ACK and exact published bytes while a guard
  blocks replay; explicit retirement resolves it. Failed rollback directory
  durability leaves terminal uncertainty and refuses replay.

The direct base adapter supplies only in-process dispatch and synthetic identity;
its status values are not HTTP observations or native provenance. The original
importer remains unchanged and is not used to accept synthetic host proof.

The independently generated Foundation probe retains the exact changed
`start`, `send`, `observe` and serialization expression, replacing only `post`
with an explicitly named in-process stub. The unchanged actual transport and
first-failure diagnostic are host compiled. Twenty-six detailed client controls
cover raw JSON echo rejection (including `4992.0`, `4992e0` and `4.992e3`),
unaccepted generation/no fallback, and client packing through both maximum file
sizes. Ninety-six finite-extrema/slash-heavy/all-byte full and partial envelope
rows round-trip exact bytes. The maximum observed body is 6,995 bytes; the closed
metadata count excluding uptime/data is independently checked as 316 bytes.
The retained actual guard accepts 8,192 bytes and rejects 8,193. These finite
rows do not prove exhaustive Foundation binary64 formatting. The 1,076-character
representation accounting remains a calculation, with the actual guard
authoritative. Actual transport state controls check response cap, deadline
clipping, request ceiling and sticky first failure. The asynchronous URLSession
network path is preserved but not executed or qualified by this stub.

The complete, unchanged four-source UIKit/XCTest compilation unit is checked
with Apple Swift 6.3.3 from Xcode 26.6 (17F113), iOS Simulator SDK 26.5,
`arm64-apple-ios26.0-simulator`, and the framework/library search flags from the
previous accepted typecheck. Compiler SHA-256 is
`2ed38571e92c0283091838c1649e27650ad9c99950288e883c7b2dc6c4ce89fb`.
The reviewed ToggleUITests.swift SHA-256 is
`0e43bd202946711ff6f1c89c8ebeb7d26f692f7ab4d5ec862e67e674f3765fb3`.
This is a typecheck, without native product compilation, a runner build or launch.

Exact argv, tool versions, outputs, compiler/source bindings, process ownership,
EOF and exit status are retained under the review verification directory. The
first independent Foundation harness compile failed because two throwing calls
were passed into a nonthrowing assertion autoclosure. That failed source and
command/output are retained under `attempt-1-foundation/`; only the review
probe was repaired. A passing second probe is retained separately before the
final additional exact-body-boundary controls. Product sources were never edited.
The first review seal rejected the review's own TAR hardlinks because its
verifier initially classified only regular TAR headers as regular filesystem
files; the dependent verify found no handoff. Those failures are retained under
`attempt-1-seal/`. The final verifier resolves only lexically confined archive
hardlinks to regular archive members and verifies exact bytes. Exploratory
read/JSON-output-inspection errors are separately documented.

The producer's 25,394-entry synthetic archive is independently checked with
type-aware path handling: 19,219 regular files, 6,174 directories and one dangling
symlink. The link target is recorded lexically; it is never followed or extracted.
Fresh review stores are archived with an independent type-aware manifest and
then removed. Owned compiler/module caches are removed after each invocation;
all owned subprocess groups reach exit and EOF. Producer inputs are rehashed
after testing and remain unchanged. No listener, outbound network, device query,
simulator/emulator/phone/UI/screenshot or Git operation is performed, and no
other project process or store is changed.

The original V6 result remains Settings failed, dependent Tab skipped, Xcode exit
65, strict importer rejection. This review does not predict elapsed time or
claim a Settings/Tab pass, native keyboard/carrier completion, external immutable
FieldLog qualification, signing, store, operational or GA acceptance. Physical
phones remain disconnected and deferred. Frozen hosted-inspector, authority and
rejected transport lanes are outside this review.
