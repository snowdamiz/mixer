# Architecture sources

Independently authored implementation; no claim of legally certified clean-room work.

Primary sources consulted October 22, 2026:

- https://www.swift.org/documentation/articles/swift-sdk-for-android-getting-started.html
  — matching official host compiler/Android SDK and NDK, native shared libraries.
- https://www.swift.org/documentation/articles/wasm-getting-started.html
  — full and Embedded Swift SDK distinction, exact host/SDK match.
- https://webassembly.github.io/spec/core/
  — normative binary encoding, validation and execution semantics.
- https://www.rfc-editor.org/rfc/rfc8949 — deterministic CBOR encoding.
- `mixer-product-plan.md` — owned product requirements and acceptance gates.

The installed 6.3.3 compiler is a qualification candidate, not a claim of the latest
release. Toolchain recipes pin observed installed versions; upgrades require new
cross-target evidence. Public docs currently illustrate 6.4.1.
