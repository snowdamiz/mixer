# Native HTTP transport implementer evidence

Run `python3 capabilities/verification/http-transport/verify.py` from the repository.
The runner uses installed official toolchains and an isolated loopback TLS server;
it does not contact a remote service, modify trust stores or use a physical device.
The ephemeral TLS private key is destroyed with its temporary directory.

The receipt records the committed base tree and an exact SDK/capabilities source
manifest including uncommitted implementation files. Its SHA256 is
`1b004fc3d0eee04a1bb1338aacc4edfc0eb68adccb4c96694a5d87039dd1e257`.
All those files were unchanged during the final run. The implementing agent was
`gpt-6.1-sol` with `xhigh` reasoning; this is implementer evidence, not independent
review or a W06/GA gate approval. The previous capability receipt is intentionally
preserved at its earlier source revision.

The final run passes24 capability tests (13 previous,11 native HTTP),23 existing SDK
tests,11 native HTTP tests with Thread Sanitizer,20 Java checks and the unchanged
Swift/Java codec differential (24 valid,66 hostile inbound,38 completion directions,
four forged completions). The native suite exercises pre-I/O typed validation,
explicit request headers, exact64KiB request/256KiB response boundaries, unknown and
misleading lengths, empty/HEAD/204 bodies, malformed metadata, compression/redirect
rejection, cancellation/deadline/quota cleanup,100 completion/cancellation schedules
(66 start native I/O), denied installed policy before I/O and original completion
ownership. System frameworks are not instrumented by the sanitizer.

Monotonic deadline tests hold back the watchdog and advance an injected internal
clock. Late success still fails, and an expired preflight never starts I/O. The
runner also copies the owned source into a private temporary snapshot and removes
only the final success/deadline guard. That intentional mutant must fail the late
success regression with exit1; its failure is retained and explicitly expected in
the receipt. No shared production source is changed by that experiment.

The actual macOS URLSession rejects a local self-signed certificate whose IP name
matches the request: one connection, failed TLS handshake, no successful handshake
and zero application bytes. This proves only that negative trust path on this host.
Injected URLProtocol tests do not establish actual HTTP parsing, successful TLS or
device networking behavior.

iOS arm64 source compilation treats Swift warnings as errors. Android aarch64 API28
dynamic test runner and static Swift probe link successfully; neither was executed.
The WASI value module compiles with native networking excluded, without guest linking
or owned-VM execution. The original Android static-link attempt failed because
FoundationNetworking's static curl dependencies were missing. Its complete original
command, source digest and failure output remain in `initial-android-static-link.json`
and `logs/initial-android-static-missing-libs.log`. Explicit official SDK link flags
`-lssl -lcrypto -lz` resolve that attempt; no stale `libcurl.pc` absolute build paths
are used. This does not establish exact shipped backend versions, security approval,
license/notice completeness or APK dependency packaging.

The schema remains1 and all wire hashes are unchanged. The generated native identity
changes from `29c018b8c58166a3397ac285bcd1ec54fd2880d1e22679c079ae75d0d58058e9`
to `14f7257965a5d468d8901e5456253298346025ccdfba0a5d70554cea0c7ba305` because
the installed native HTTP implementation is new. It requires a new native binary
and installed runtime fingerprint; matching wire hashes cannot install it by OTA.

Open gates include successful production TLS and Android runtime CA configuration,
actual redirect/auth/cookie/cache/parser behavior across platforms, system-internal
buffer bounds, radio/background/minimum-OS device lifecycle, native dependency
packaging/review, signed network-grant activation, guest imports/JNI, immutable
published-package FieldLog integration, all wider Section9 families and external
security/operational qualification. Phones remain disconnected; no new device runs
were attempted.
