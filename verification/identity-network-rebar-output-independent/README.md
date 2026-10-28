# Independent Rebar output correction review

Decision: accept the current three-file source correction for a fresh isolated
`identity-production-network` CI attempt. No blocking finding was identified
within the existing ordinary, serial, owned fixture scope. This decision does
not qualify the changed Elixir helper, either product method, or a GA gate.

The review rehashed all 48 correction files against packet SHA256
`d56a5dde00bc61888d5cdf690cf0e44bf11430ac3bb82a819d3206de390349ac`
and all 483 files of the prior run review against
`148912f1c031a1bdd757376436cd4959235b170f7dd2ae60e6c38df2d6a96d8c`.
The canonical three-file digest remains
`163073180bacc272e3d19209508cf9e625950f1afb8bc7a5b6b1b1c27ae9bf91`.
All 111 prior tests remain byte-for-byte exact. Existing Python function bodies
remain exact except `Collector.collect`; existing assignment ASTs remain exact
except `MANIFEST_EXS`. Protected workflow/store hashes are unchanged.

The independent command `python3 -B
verification/identity-network-rebar-output-independent/review.py` passed 126
producer controls and six independent probe methods in 1.167 seconds under a
50-second alarm. The probes include 54 parent-metadata substitutions, exact
64KiB transport, empty capture rejection with retained facts, immutable-input
rejection after raw retention, invalid-row rejection before execution,
non-mutating validation, helper dispatch and final alias/equality controls.
The audit refused process/socket/native-load/held-custody/write-outside-lane
self-test events without invoking the OS operations. It recorded no unexpected
denials. Every owned temporary directory was removed.

The selected actual prior manifest was also recomputed independently. Command
89 completed and added only the 895-byte telemetry `source.dag` recorded in the
correction. Its raw bytes and actual filesystem metadata were not retained.
That supports the exact path/phase hypothesis; it does not establish the lost
DAG's semantic validity or qualify an old hash as an allowlist.

The correction retains the prepared archive `_build` prohibition and exact
restore comparison. After offline compilation it requires the frozen source
and lock, exact telemetry input anchors, and a single fresh generated row with
the expected file/ancestor metadata. Removing only that row must restore the
entire prepared manifest. Raw capture precedes immutable-input admission and
the isolated test flag, uses the fixed helper branch in the owned test container,
and must match both compiled byte count and hash. The final source comparison
includes the generated row. Generic export paths, resources, mounts, images,
cleanup and the other helper bindings remain unchanged.

The file checks have an explicit concurrency boundary. `lstat` followed by
`File.read!` is not an atomic descriptor-bound identity check. Host `exists()`
followed by `write_bytes()` is not atomic against another same-UID writer in
the output directory. These do not block this serial trusted fixture lane,
whose output is freshly and exclusively created and whose containers have no
host source/socket mounts. They must not be represented as protection against
an adversarial compiler or hostile concurrent writer. Existing `command()`
also may lack partial stdout if an exception occurs before its persistence
point; incomplete or missing capture remains unqualified.

The named unlock is fresh isolated CI that executes the changed helper, checks
the actual root-owned `0644` file and `0755` ancestors, retains complete bounded
opaque DAG bytes, passes immutable-input equality, collects loaded-module
identities and runs both unchanged product methods. Acceptance still requires
their semantic receipts, current ten migrations, post-test equality, key cleanup,
fresh isolation/resource evidence, exact owned container cleanup and independent
artifact review. The metadata expectations remain unrun hypotheses.

No canonical source, unrelated CLI files, status/gates or frozen packets were
edited. No local Elixir/compiler/container/PostgreSQL, new network action,
native/UI/capture, held process/custody probe, private FieldLog access,
commit/push/dispatch or publication occurred. All existing holds remain active.
