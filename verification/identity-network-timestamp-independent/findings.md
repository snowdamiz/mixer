# Independent timestamp review

Decision: accept the three frozen canonical sources for one fresh isolated CI
attempt. This is source and pure Python archive-admission acceptance. JOSE
compilation and the two unchanged product methods remain runtime-pending.

The failed artifact is run `40766689512`, source
`8888d8e2c8431ee311c68e94a1abbb280f84802a`. Its preparation and test prerequisite
receipts both identify Elixir/Mix 1.20.4 and OTP 29.1.1. Its archive includes locked
JOSE 1.11.13 and all 113 Erlang sources. Dependency compilation exited zero after
compiling 16 Erlang sources, while both product methods subsequently failed at
`:jose_jwk.generate_key/1`; the actual product result remains **0/2 passed**.

I independently fetched the official Mix v1.20.4 sources through read-only GitHub
`fetch_file`. The retained complete files have verified Git blob identities and
match all producer platform excerpts. The relevant platform behavior is the
[missing-target zero timestamp and strict comparison](https://github.com/elixir-lang/elixir/blob/v1.20.4/lib/mix/lib/mix/utils.ex),
the [source/include stale check](https://github.com/elixir-lang/elixir/blob/v1.20.4/lib/mix/lib/mix/tasks/compile.erlang.ex),
and [dependency compile arguments](https://github.com/elixir-lang/elixir/blob/v1.20.4/lib/mix/lib/mix/tasks/deps.compile.ex).
The last task does not forward `--force` to the nested compile task. Dependency
context defaults to `:prod`, and the actual locked JOSE project omits Erlang
warnings-as-errors in that environment.

A separate line-by-line include-attribute traversal of the archived sources
predicts exactly the observed 16 compiled Erlang modules: they reach the external
`public_key/include/public_key.hrl`. The other 97, including `jose_jwk`, `jose_jwt`
and `jose_jwe`, have only archive-local source/include timestamps at zero. With a
missing target also at zero, the strict source-greater-than-target comparison
does not mark these sources stale. A source time of one is strictly greater.
This is a source-derived causal discriminator; the historical artifact does not
record external OTP header timestamps, and no local Erlang evaluator or compiler
was executed.

`python3 -B verification/identity-network-timestamp-independent/verify.py` passed
all six independent test methods in under one second, with a 50-second ceiling.
The real 15,196,160-byte archive was reheadered in memory. All 1,232 payloads,
membership, length and metadata other than mtime/checksum remain byte-identical.
Its candidate SHA256 is
`a0d9ec2cefbe62b0bfd22f3b1113b7880f5d53046a3419678f67d88f30bdc65e`, matching the
producer's independently constructed candidate. The real transfer and prepared
validators admit it and reject the original zero-time archive.

The independent suite rejects a single time of -1, 0, 2 or 4,294,967,295 in each
actual manifest section, a valid PAX fractional time of 1.5, and a malformed
octal timestamp. It also rejects actual-archive payload mutation, missing
membership, manifest hash mutation, prepared build-output contamination and an
exceeded archive byte cap. The initial source-only transfer still produces time
zero.

After normalizing only the added constant, exact timestamp admission and the
preparation tar argument, the complete collector AST equals the archived 8888
collector AST. This bounds all resource, capability, mount, dependency, product,
semantic and existing admission logic to the unchanged baseline. All original
126 Python test-method ASTs remain equal; exactly three methods were added by
the producer. The 177 frozen product entries and every dependency payload are
unchanged within the actual archive. The checkout workflow and browser-auth
store protected hashes also remain exact. The checkout has separate active work;
its current product files were not mistaken for the historical frozen archive.

The first review-harness attempt failed because its assertions included the
necessarily changed checksum, used a 13-byte malformed field, expected a
different JOSE helper spelling and compared historical frozen product entries
against current checkout work. Its full unittest output is retained in
`attempt-1-audit-output.txt`. These harness assumptions were corrected only in
this owned review folder; the subsequent complete run passed. No canonical
source changed during review. `git diff --check` passed for the three canonical
paths and this review directory. The observed Git revision/tree stayed
`dfd0e3196543cc1749c9cc924cc7accf28c9dc25` /
`3cc58d6744649fdd138b9d3963b436db62480ecf` across the review.

`readset.json` binds all five producer files, the exact canonical sources,
immutable failed-run inputs, protected checkout files and independently fetched
official files. The verifier rechecks this readset before emitting its receipt.
`packet-manifest.json` seals the complete review packet. `audit-output.txt` retains
the complete passing unittest output; `audit.json` records the audit event counts
and zero denied child/socket attempts. A write audit restricts verifier writes
to this review directory.

No local compiler, Elixir runtime, container, PostgreSQL, native instance, UI,
capture, custody or held-process probe ran. No commit, push, dispatch, canonical
edit or global status change was made. No persistent resources were created;
archives were never extracted and the candidate existed only in memory.

The named next executable acceptance is a fresh isolated CI compile followed by
both unchanged production-path methods and independent artifact review. This
packet does not mark that runtime acceptance, phones, held lanes or any GA gate
verified.
