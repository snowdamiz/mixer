# Installed capability exit observation evidence

The additive native lifecycle implementation uses a closed
`InstalledCapabilityAdapters` value and `CapabilityHost.submitObserved`.
Each accepted installed call owns one private lease. Reuse/observation requires
both invocation return and adapter cleanup; terminal delivery is independent.
HTTP cleanup is acknowledged at URLSession invalidation after native-counter
release. Storage cleanup is the concrete serial actor method's return, including
operation-local descriptor cleanup. The shared store remains open and reusable.

The observer is retained independently of the host by worker/exchange ownership,
so host close/deinit cannot drop it or fabricate cleanup. Arbitrary legacy HTTP
closures/service conformers cannot use the observed API. Ordinary submit on a
closed-adapter host shares the same retained-capacity semantics.

`receipt.json` records exact commands, tool versions, revision/tree baseline,
scopes, output paths/hashes and limitations. `source-manifest.json` lists the 49
SDK/capability source/test files frozen throughout the run. Its canonical source
digest is `24e6c520347a54fd31e74fdc6db185da6982f412e6068d078e9a64686da4dcc7`.
The digest includes both new helper files. The unchanged source snapshot passed:

- 37 capability tests in debug and 37 in release, including 13 new exit tests.
- 24 native HTTP/exit tests under ThreadSanitizer, including concurrent duplicate
  lease reports and 48 cancellation/success/close races per run.
- 23 existing SDK Core/UI/Apple tests.
- Official iOS arm64 target compilation, official Android static probe and dynamic
  test-runner cross-compilation, and official WASI capability-module compilation.
- Generator determinism, 20 Java codec checks and Swift/Java differential parity
  (24 valid/66 hostile inbound cases, 38 completion directions/four forged cases).

The controlled invalidation callback tests hold the real delegate boundary before
it clears ownership/releases its counter. They demonstrate that task return and
terminal delivery cannot prematurely release installed host capacity. Reverse
ordering holds the worker after invalidation, proving the second side of the join.
Tests also cover no-I/O denial/unavailability, rejected registration, unused
reservation cancellation, cancellation before invocation, acquired-counter expiry
before session creation, quota, redirects/native failures and observer survival
when the last host reference is released.

No new process-wide host/session cap is claimed. The callback is an adapter cleanup
boundary, not a proof of kernel socket destruction, total RSS reclamation, Swift
stack unwinding or durable-effect rollback. System frameworks are not sanitizer
instrumented. URLProtocol test fixtures do not qualify TLS/network parsing.
Cross-compilation does not qualify physical devices or Android trust/runtime
packaging. Phones remain disconnected; no device commands were attempted.

Schema-v1 source/value hashes, codecs and generated dispatch are unchanged.
The source implementation identity changed to
`9e66695878568cbb0859d13cc6505ffd45b1471365af4d236fb9601efc0f6ed2` through the
existing generator. The change requires updated installed native binary identity;
it is not OTA approval. Rust mailbox integration, verified identity/configuration/
grant composition, immutable published-package FieldLog use, signing, stores,
physical lifecycle qualification and accountable independent GA reviews remain
pending. No GA gate is passed by this receipt.

Reproduce from the recorded frozen source with:

```sh
python3 capabilities/verification/exit-observation/verify.py
```
