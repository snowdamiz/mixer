# Isolated fixed Settings upload format

This packet implements the root-selected 4,992 decoded byte format in an isolated
derivative. It changes exactly two endpoint files: accepted
`harness/UITests/ToggleUITests.swift` and selected
`inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py`.
The other 70 source files from the selected 32-file runtime and accepted 40-file
compile archives remain byte-identical. The strict importer, application oracle,
actual application and library sources, durability store, origin guards, action
and capture code, first-failure diagnostic and transport are unchanged.

The source-binding record is
`verification/apple-settings-fixed-chunk-implementation/source-bindings.json`.
It records the source revision label `ee390cbf56ba388a21c7d28c884dbed5fd7282fe`,
the exact two frozen archive hashes and every original/derivative member hash.
Frozen archives are copied under this packet's `inputs/`. The root selection
SHA-256 is `99edd321744935dc9c6c1c3ccebe28706759e270100b72319f58a0338fee73e7`;
the verified diagnosis handoff SHA-256 is
`019746fbd6344209c69ffde35a7a0933378943c280bbc3a69147b2afb532c40b`.
No live endpoint or root execution record is replaced.

## Endpoint behavior

Start requires the exact integer `chunkBytes: 4992` in the closed start shape.
The receiver echoes that integer only in the accepted start response. The client
validates NSNumber integer representation, excludes Boolean and floating-point
values and requires 4,992 before assigning the returned generation or accepting
the remaining session allowance. Missing or invalid fields cannot commit a
receiver start. Old/new endpoint mixtures fail closed. There is no negotiation,
fallback, retry or per-chunk discriminator.

The client serializes only its Settings diagnostic envelope with `.sortedKeys`
and `.withoutEscapingSlashes`, retaining the actual 8,192-byte body guard. The
receiver admits at most 6,656 base64 characters and requires exact canonical
encoding, ordered slot/index, matching descriptor, exact decoded fragment length,
complete byte/hash identity and PNG/UTF-8 validation. Both endpoints use
`ceil(bytes / 4992)`: maximum AX 41 chunks, PNG 401 chunks, with exact final
length `min(4992, bytes - index * 4992)`. Index 400 is the largest possible index.

All existing request, response, file, aggregate, upload, event and poll bounds
remain: 2,500 requests, 8,192-byte client body/response bounds, 200,000 AX bytes,
2,000,000 PNG bytes, 7,000,000 declared bytes, 32 uploads, 100 events and 40 polls.
The client/host 29-second checks, two-second request ceiling, anchored three-second
observation window and sticky first transport failure are unchanged. No
concurrency, new diagnostic write, deferred durability, origin caching, narrower
metadata/uptime admission or application/UI change is introduced.

## Executable evidence

`record_commands.py` runs preparation, direct host controls and the Foundation
probe. Its receipt retains exact argv, Python/tool versions, source-binding hash,
exit codes, elapsed times, stdout/stderr hashes and EOF, child PID/process group
ownership and reaping. The Foundation receipt additionally binds the compiler
and generated host source, SDK and macOS target. Python 3.14.8 and Apple Swift
6.3.3 were used; this is macOS host evidence.

The 45 host test methods pass. They exercise actual derivative Session and
unchanged TransactionStore code through a documented direct-dispatch base
adapter. That adapter does not open a listener or stand in for HTTP/framing/
capability/native-origin qualification. Retained persistence controls wrap real
filesystem writes, short/partial writes, fsync, hardlink publication, exact
publication checks, rollback, guard handling, retirement, ancillary reporting
and restart/replay refusal. Sixty-eight detailed persistence cases preserve the
irrevocable commit point, same-cursor recoverable rejection and terminal
uncertainty behavior. Their adapter status integers are not HTTP observations.

Actual descriptor admission and durable replay cover AX sizes 1, 4,991, 4,992,
4,993, exact multiples and 200,000 bytes; valid synthetic PNGs cover partial/full
boundaries, exact multiples and 2,000,000 bytes. Every reassembled published file
matches bytes and SHA-256. Malformed/old/mixed/count/index/slot/duplicate/encoding/
digest/PNG/AX controls reject without advancing accepted Session state. Request,
file, storage, event, poll and deadline boundary controls remain executable.
The unchanged RuntimeBindings guard validates the complete exact derivative
source mapping and rejects a module with spoofed selected paths but foreign
function code.

A valid synthetic public Settings proof includes seven route AX captures with
an allowed retry, all three route search/tap/opened bindings, fresh parent/leaf
and action witnesses, before/after/terminal PNG and AX, one action, enabled
observation, termination and all completion markers. Its entire durable journal
replays through the actual derivative Session. There are 758 controls omitting
each required nested field, 758 replacing each with an invalid value and 55
explicit stale-timing controls. The retained public-witness tests also exercise
wrong/ambiguous query counts, metadata/state/geometry/point/binding changes,
freshness boundaries, action anchors and enabled-window boundaries. Host proof
completion never claims official XCTest attachment or native provenance.

The Foundation executable tests 80 full/partial, slash-heavy/all-byte and finite
extrema envelope rows. Its largest observed actual UTF-8 body is 6,995 bytes.
Decoded bytes round-trip exactly and no base64 slash is escaped. These finite
rows do not prove exhaustive binary64 formatting. The closed 316 + 1076 + 6656
= 8048 representation accounting remains a conservative calculation, with the
actual 8,192-byte guard authoritative.

The generated probe uses the actual changed start and upload methods, replacing
only `post` with an explicit in-process stub that retains the real diagnostic
serialization expression and body guard. It verifies exact raw-JSON echo
rejection for missing/wrong/Boolean/string/null/floating/exponent values,
4992.0 and 4.992e3 in particular, session nonacceptance, no fallback, and actual
client chunk packing through maximum file sizes. The unchanged original
DiagnosticTransport and SettingsFailureDiagnostic are host compiled. The
transport checks retain response limits, request cap, absolute-deadline clipping,
two-second ceiling and sticky first failure. The real asynchronous network
`post` path is preserved in the reviewed source but is not executed by this
host stub and is not claimed as a network test.

## Packaging, cleanup and limits

The source review archive, member manifest, complete evidence inventory and
handoff are sealed by `seal.py`; `verify.py` rechecks them without running a
producer. Independent review is pending. Failed preparation assertions, the
initial adapter import/read-order errors and first host compiler failure are
retained. These were host harness failures corrected before the passing run.
The final run's synthetic stores, regular files, directory entries and dangling
symlink targets are retained in the type-aware `synthetic-evidence.tar.gz` before
owned working stores are removed. The first packaging attempt archived regular
files only; its complete regular-file archive and omission receipt remain under
`packaging-attempt-1/`. A fresh passing run supplies the final complete archive. The owned compiler/module-cache directory is removed after every
attempt and all owned child processes reach exit/EOF. No other project process
or store is inventoried, stopped or changed.

No listener, outbound network, simulator/emulator/phone/UI/screenshot, native
product compile, build-for-testing, full-runtime attempt or Git operation is
performed. Full UIKit/XCTest typechecking, a generic runner build, native
execution, official selected attachments and unchanged importer acceptance
require separate source-bound selection. This packet cannot reuse the original
product digest or importer source-tree/product constants for a new execution;
those remain byte-identical historical contracts pending coordinated root
selection. Host consistency evidence does not authorize that handoff.

The frozen V6 result remains Settings failed, dependent Tab skipped, Xcode exit
65 and strict importer rejection. The copied diagnosis/native result receipts
preserve those facts. There is no elapsed-time prediction, native Settings/Tab
pass, full matrix, keyboard/carrier completion, immutable external FieldLog
qualification, signing, store, operational or GA acceptance. Physical phones
remain disconnected and deferred.
