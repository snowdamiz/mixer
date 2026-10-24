# Private Settings diagnostic: V6 host ordering repair

Root selection `verification/apple-toggle-keyboard-focus-v5-root-review/v6-repair-selection.json`
(SHA-256 `a687f64d09bc04df73842b3a45a4014551497a452cdf5092cd24ee60cbb9a3d7`)
selects host preparation only. All old packets, failures and native evidence remain
immutable. No native launch, instance query, UI, capture, compiler, settings, Git,
live product or tracker operation occurs in this packet.

V5 accepted destination captures preceding the tap even when their journal records
arrived afterward. V6 retains the exact accepted tap completion and sequence per
route. Before accepting any route-opened capture, it requires that route's tap
sequence to precede the observation and `tap.finishedUptime <= captureStartedUptime`.
The existing nested timestamp check then requires capture start <= destination
observation <= capture finish. Equality is valid; any earlier capture is rejected
before destination credit, upload allocation or journal persistence. The existing
transactional Session copy preserves all accepted clocks, counters, route bindings,
files and cursor on rejection. The real Bridge still records the rejection as a
failure. Opened summary bindings expose the matching tap sequence/completion and
capture start; offline replay applies the identical verifier.

Eight focused methods cover all three routes: pre-start, overlapping, immediately
before completion, equality and immediately after; wrong-route tap identity and
older completion; exact retained completion/sequence, internal route identity
faults, actual HTTP rejection, persistence failure, mutated offline journals and
the exact frozen V5 stale journal. The latter still credits all three destinations
on sealed V5 and is rejected by V6 at its first stale capture. Its 45 files remain
unchanged. This is synthetic adversarial evidence, not an observed native result.

The independent 26-method suite retains 25 methods byte-for-byte at AST level.
Its CONTRACT method now expects immediate rejection, retains the false-setup
assertion, checks no destination credit and verifies the last accepted journal.
The original independent suite against V5 still produces the same one CONTRACT
failure. Prior 18+17+44 assertions run against V6 with the exact V5 synthetic
fixture extension; exact V4 39+44, V3 44 and V2 29 regressions also pass. The same
three V3 findings remain reproducible. The V4 failed native replay/analysis match.
The exact previously compiled host transport binaries pass 16+35 checks; no new
compilation is claimed. The initial focused HTTP fixture used the wrong security
header and failed before reaching semantic validation; its source/output is
preserved in `focused-attempt-1.json`.

App closure remains `f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`,
app archive `b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`.
Strict V2 oracle, V5 runner source, products, archive and shared Swift transport
are exact copies. Runner source identity, using the original V5 source path
context, remains `acda99b1fb3b2c4252e346bf57f592a0048cba6a4c291aa08208488c69274af1`;
product `b4b793cf270527e47df3fc73bab3ea30f67c77a413508f5a880dbd4cc9268f84`;
archive `40365412907c311d421ce94d63e147b67a55b0543d5b6ba6f56211497dbea479`.
Historical official compiler/binary receipts are explicitly reused and tool hashes
rechecked. The small production delta and independent test adaptation are saved
as diffs; `immutable-reuse.json` binds each copied path to its original.

Request/event/upload/payload bounds, 29-second diagnostic, two-second request,
600-second session, one conditional switch tap and anchored three-second window
are unchanged. Cleanup, export and inherited strict qualification assertion are
unchanged. Any future native setup remains `DIAGNOSTIC_ONLY`, with six application
cases unrun and keyboard, carrier and GA acceptance false. This packet stops for
independent/root review; native execution is not selected.

```sh
python3 -B verification/apple-toggle-keyboard-focus-v6-preparation/run.py verify
python3 -B verification/apple-toggle-keyboard-focus-v6-preparation/offline_checks.py --check
```

After a separately selected root runtime, its fixed journal can be replayed with
`python3 -B verification/apple-toggle-keyboard-focus-v6-preparation/replay.py`.
