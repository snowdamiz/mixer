# Retained audit display correction

Root selects a narrow follow-up to AS05 in
[the atomic storage correction contract](hosted-atomic-storage-corrections.md).
The independent correction reviewer has reproduced valid PostgreSQL audit rows
that the separate Elixir row checker rejects. SQL storage, CBOR reconstruction
and replay succeed; the mismatch is in exact JSON display serialization.
Repository acceptance remains pending.

PostgreSQL renders otherwise unnamed ASCII control escapes with lowercase hex,
such as `\u000b`. The candidate's `Codec.postgres_display/1` delegates strings to
Jason, which can emit `\u000B`. JSON decoding gives the same string, but the
selected retained-byte comparison correctly distinguishes the bytes. The fix
belongs in the independent expected-byte formatter, preserving the original
SQL rows, CBOR and hash contracts. Do not weaken equality, normalize stored
bytes on read, reject all otherwise valid control characters, or rewrite the
old evidence.

Implement the exact string formatting needed by this closed audit schema. Keep
PostgreSQL's object key order and spaces, arrays, integer schema value and null
representation. Preserve UTF-8 bytes, quote/backslash escaping and the usual
short control escapes; other representable controls need the observed lowercase
four-digit form. Literal source text such as `\\u000B` must remain literal and
case-preserving. A global substitution over an already encoded JSON string is
not an acceptable implementation. PostgreSQL's rejection of U+0000 and malformed
Unicode must remain explicit; neither is a successfully stored valid row.

The next candidate stays isolated. Copy the frozen corrected specimen, change
only the necessary formatter and focused tests, and retain an exact delta.
Resolve the independent review's original failed assertions without changing
their intended outcomes. Verify against actual PostgreSQL output, including
all representable ASCII control characters, quote/backslash and literal escape
text, multibyte UTF-8, embedded separators, mixed strings and the existing byte
limits. Exercise both pure display parity and complete stored/uploaded/replayed
rows. Preserve all original positive, corruption, timing, privilege and
lost-COMMIT-response cases.

Bind the final independent review packet before claiming the correction complete.
Retain failing attempts, exact source/tool/output hashes and owned cleanup. A
fresh independent check and root acceptance are still required. This changes no
live migration, HTTP/repository path, provider, native or GA qualification.
