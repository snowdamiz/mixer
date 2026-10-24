# Independent retained audit display review

Recommend root acceptance of the isolated **formatter-only CR01 correction**.
The exact copied candidate freshly passes **88/88**, and the reviewer-extended
full suite passes **94/94**, both with zero skips or exclusions. No new blocking
finding was observed within this selection. Root acceptance and repository
integration remain separate decisions. This review does not accept the production
startup catalog, combined authority schema, or full AS05/product implementation.

The [selected formatter contract](hosted-atomic-display-correction-contract.md)
and [root direction](../verification/hosted-atomic-storage-root-review/display-correction-direction.json)
select exact PostgreSQL retained display reconstruction. The
[producer packet](../verification/hosted-atomic-display-correction/receipt.json)
and [prior independent CR01 review](hosted-atomic-storage-correction-review.md)
were checked before execution. All supplied receipt, seal and codec hashes match.
The producer checker verifies 1,019 own bindings and 488 upstream bindings; the
prior review checker verifies 213. This review binds their 1,509 unique input
files and retains the original failures and all four producer attempts unchanged.

The only implementation delta is the string formatter in `lib/codec.ex`, SHA-256
`7152ab6d9c2fec56cd6e707ef09bb4f5fb3a8477edb7b0b5410a884278fe37ee`.
It validates source UTF-8 and rejects NUL, visits source bytes, escapes quote and
backslash, emits the five short escapes, emits other C0 controls as lowercase
four-digit escapes, and preserves the remaining UTF-8 bytes. Its object-key
path uses the same function and retains PostgreSQL's byte-length/byte-order sort.
Literal backslash-u text is escaped as literal source text, preserving its case.
The implementation performs no substitution over encoded JSON. SQL, catalog
definitions, typed CBOR reconstruction, hashes, row equality and the original 83
test bodies remain unchanged. All original candidate 88 bodies remain intact in
the reviewer extension.

| Fresh execution | Observed result |
| --- | --- |
| [run-1](../verification/hosted-atomic-display-review/run-1/receipt.json) | Exact copied runner/inputs, 88/88; source/runner digest `1beaec6474ddb51257ca8eda34c47777344019d4e02c4213ea5e1030cc9fcd0c` equals the producer's passing full run. |
| [run-2](../verification/hosted-atomic-display-review/run-2/receipt.json) | Original 88 plus six independent reviewer tests, 94/94. No skips, exclusions, or failing review attempts. |

The six independently authored additions establish these scoped observations:

- 407 mixed strings agree byte-for-byte with actual PostgreSQL and independent
  Python standard-library expected bytes. They combine every representable C0
  control and DEL with one through eight backslashes, literal uppercase/lowercase
  escape text, quotes, solidus, multibyte boundaries, noncharacters, separators,
  combining marks and 128 reproducible seeded mixtures. Both typed audit decoders
  also agree on CBOR when each text fills reason and profile.
- 15 nested object/key cases and eight raw JSON escape controls agree with actual
  PostgreSQL. Multibyte key byte lengths, literal/control keys, surrogate pairs,
  and composed/decomposed text retain their exact distinctions. Arbitrary objects
  exercise the helper only; the closed audit schema remains closed.
- 53 new actual uploaded rows retain every column, pass both validators, and
  return the original status/body/event on replay with unchanged rows. Four more
  uploads exercise 512-byte reasons; their pure typed fixtures also exercise exact
  128-byte profiles. Quote/backslash expansion, mixed controls, maximum Unicode
  scalars and combining text all preserve the source-byte limits. 129/513-byte
  typed inputs and a 513-byte upload reject.
- Six decoded-equivalent replacements of actual retained bytes fail both row
  validators and cached replay: uppercase control hex, escaped BMP Unicode,
  surrogate-pair spelling, solidus escape, leading whitespace and compact JSON.
  Restoring the exact original bytes restores exact cached replay each time.
- 15 NUL/malformed UTF-8 strings reject as direct strings, object keys and nested
  array strings. Actual PostgreSQL conversion and actual upload reject them; no
  artifact, audit, idempotency or tenant-head change is committed.

The separately authored [Python oracle](../verification/hosted-atomic-display-review/byte-oracle.py)
imports no candidate encoder or producer oracle. It reconstructs typed CBOR,
standard domain-separated SHA-256 hashes, every retained projection, exact
PostgreSQL display bytes, and adjacent edges for **185 actual chain rows** across
the two runs, plus the corruption-control original row. This is captured-row
verification of the selected schema; it does not prove arbitrary-input product
decoding or whole-history/key provenance against privileged coherent rewrites.

Both full runs freshly execute the completed-COMMIT response-drop proxy: the
server completes COMMIT, the client receives no CommandComplete, an owned server
restart follows, and retry returns the original bytes without another event.
The original clock/deadline, late blocking reads, private helper execution denials,
and nontransactional before-DML trigger-sequence observations also pass. Expired
and stale attempts never invoke the DML trigger; the unexpired control invokes
both INSERT triggers. Review instrumentation is removed after the case. These
are full executions; the producer's focused run remains five passing assertions
with 83 explicitly excluded, and is never relabeled as a full pass.

All four producer cleanup receipts and both fresh reviewer cleanup receipts are
verified, including absence of their owned scratch paths. Both reviewer clusters,
proxies, sockets and scratch directories were removed. No native process or
simulator was started, and no other project's cluster/process was touched.
Physical phones remain disconnected and deferred.

The environment is local macOS/arm64, PostgreSQL 17.11 (Homebrew), Elixir/Mix
1.20.4 with OTP 29, Python 3.14.8, and Go 1.26.4, with the unchanged seven
archive-verified dependency sources. Both runs observed source revision
`4250e05a132c04370d5ccb971c9faaf1b82a9395`; per-run inputs, contract/source/tree
digests, exact argv/environment overrides, executable hashes/versions,
stdout/stderr and proxy/server output are retained. No dependency was fetched.

The unchanged catalog digest proves equality only to this frozen synthetic
specimen. It does **not** accept production trigger enablement, internal FK
enforcement, persistence classes, parameter grants, default privileges or the
separate authority/catalog correction. No repository/migration/HTTP/provider,
signed-admission composition, Neon/R2/Cloudflare/Oban lifecycle, native, FieldLog,
customer, operational, security or GA qualification follows. Fixed synthetic
policy/clock/tenant/target inputs also do not supply the complete authoritative
credential/profile/membership resolver. Full AS05 and the combined authority
schema remain outside this acceptance recommendation.

Run `python3 -B verification/hosted-atomic-display-review/check.py` for the frozen,
read-only independent checker. The [receipt](../verification/hosted-atomic-display-review/receipt.json),
[findings](../verification/hosted-atomic-display-review/findings.json), manifest and
seal bind this review. Root remains accountable for accepting and integrating
the narrowly selected formatter correction.
