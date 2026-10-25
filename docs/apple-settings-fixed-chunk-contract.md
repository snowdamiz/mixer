# Fixed Settings upload format selection

Root selects an isolated derivative of the exact V6 Settings diagnostic client
and receiver using **4,992 decoded bytes per chunk**. This selects implementation
and host verification only. Independent review, generic runner compilation and
any future native execution require separate source-bound acceptance. The V6
Settings failure and skipped Tab test remain authoritative.

The source and rationale are bound by
`verification/apple-settings-chunk-deadline-diagnosis/handoff.json`, SHA-256
`019746fbd6344209c69ffde35a7a0933378943c280bbc3a69147b2afb532c40b`.
Use the selected 32-file runtime archive and accepted 40-file compile archive
named there; do not substitute a historical template or live application.

Both endpoints use one fixed format. Start requires exactly `chunkBytes: 4992`,
and the host echoes that exact integer on the accepted start response. The
client must validate the echo before accepting the generation/session. Reject
missing, wrong-type or wrong-value format fields, old/new endpoint mixtures and
mixed chunk sizes. There is no negotiation, retry or automatic fallback. A bad
start must not commit or advance the host cursor; an invalid echo must prevent
the client from accepting the session. Add no per-chunk format field.

Serialize the diagnostic envelope with `.sortedKeys` and
`.withoutEscapingSlashes`. Preserve the actual 8,192-byte body guard. Full chunks
encode to 6,656 canonical base64 characters; partial chunks retain exact padding.
Use `ceil(bytes / 4992)`, a maximum of 401 PNG chunks and 41 AX chunks, and exact
decoded length `min(4992, bytes - index * 4992)`. Preserve strict canonical base64,
ordered indices/slots, complete reassembly bytes and digest, PNG/UTF-8 validation,
publication, durability, retirement and every existing origin check.

The closed metadata calculation is 316 bytes excluding uptime/data. The
diagnosis retains a conservative 1,076-character exact decimal representation
calculation for finite nonnegative binary64, yielding `316 + 1076 + 6656 = 8048`.
This is a representation calculation, not exhaustive Foundation formatting
evidence. Test actual Foundation output for finite extrema and slash-heavy/full
and partial payloads; the unchanged actual body guard remains authoritative.
Do not introduce a narrower metadata or uptime restriction to make the bound fit.

Preserve all required public route captures, searches/taps/opened witnesses,
fresh parent/leaf/action binding, before/after/terminal PNG and AX files, bounded
polls, enabled-state timing, termination/completion markers and official test
attachments. Keep the importer and application oracle byte-identical. The
format must not skip evidence, reuse captures, infer a missing terminal file or
substitute summaries. Count reductions for the eleven observed descriptors
(179 to 116 chunks) are arithmetic only, not a timing or acceptance result.

Keep the existing 2,500 requests, 8,192-byte body/response bounds, 200,000-byte AX,
2,000,000-byte PNG, 7,000,000 total declared bytes, 32 uploads, 100 events and 40
polls. Keep the client/host 29-second session deadline, two-second request ceiling,
three-second anchored observation rule and sticky first failure. No concurrency,
deferred durability, extra diagnostic writes, limit increase or app/UI change.

The derivative must retain failing-original evidence and include executable
positive and negative controls for exact format agreement, boundary payloads
(1, 4991, 4992, 4993, multiples and both maximum file sizes), byte/hash identity,
canonical encoding, wrong/missing/reordered/duplicate/mixed fragments, no state
advance on rejection, malformed PNG/AX, every required Settings proof predicate,
deadlines and existing transactional failure/rollback/retirement controls.
Use new owned copies and scratch, record commands/tool versions/source/output,
and clean only owned processes and stores. Frozen inputs remain unchanged.

The ownership lane is `docs/apple-settings-fixed-chunk-implementation.md` and
`verification/apple-settings-fixed-chunk-implementation/**`. Changes outside the
two endpoint implementations and derivative fixture/binding material require
coordination. No simulator/emulator or phone is selected by this contract.
