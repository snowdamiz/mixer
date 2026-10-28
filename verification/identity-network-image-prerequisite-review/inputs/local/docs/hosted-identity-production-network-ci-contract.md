# Isolated identity network qualification

This lane runs the two existing Linux networking methods that ordinary Phoenix
CI skips. K03 exercises production DNS classification, TLS peer verification and
rebinding refusal. IS04/IS05 exercises actual configured application startup,
cold token admission, restart and in-flight shutdown. The tests and production
modules remain unchanged.

The collector is `hosted/scripts/test-identity-network.py`. Its source contract
and official image/bootstrap metadata are retained in
`verification/identity-production-network-contract/`; the independent contract
review is in `verification/identity-production-network-contract-independent/`.
The contract is a finite qualification of 177 frozen product blobs from
`9e860ea12074ca31bef4087ce34177a03f295dd8`, with product digest
`023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e`.
The delivered commit must contain exactly those bytes at the selected paths.
Changing product inputs requires a reviewed refresh; a stale freeze fails.

## Runtime boundary

GitHub's Ubuntu 24.04 AMD64 runner uses immutable HexPM Elixir 1.20.4/OTP
29.1.1 and PostgreSQL 16.15 image manifests. `THIRD_PARTY.yml` inventories the
images and checksum-pinned Hex 2.5.1/Rebar 3.28.0 bootstrap tools. Metadata alone
does not prove that an executable exists or works in an image.

One preparation container downloads the pinned bootstrap artifacts, verifies
their SHA512 values and resolves only locked dependency sources. The fixed OTP
downloader verifies the HTTPS certificate and hostname, permits only the
selected endpoint, and requires a bounded HTTP 200 response with an exact
Content-Length, no redirect or transfer encoding, at most 16 MiB and a
25-second deadline per artifact. It hashes chunks before installation.
Fixed paths `/usr/bin/env`, `/usr/bin/tar`, `/usr/bin/openssl` and
`/usr/local/bin/{elixir,mix,erl,escript}` must pass actual prerequisite checks.
OTP File and crypto/SSL facilities supply the remaining bootstrap operations.
Missing tools fail the attempt; no package install,
alternate image, host cache or fallback is permitted. The Rebar executable is
installed at `/workspace/tooling/rebar3`, the exact `MIX_REBAR3` path. Preparation
exports bounded regular-file archives and is removed before tests start.

One test container uses `--network none`, a read-only root, bounded tmpfs mounts
and only `NET_ADMIN`/`NET_BIND_SERVICE`. Inside its own namespace, the collector
assigns `8.8.8.8` to loopback and checks the address, routes, interfaces,
capabilities and namespace identity. A PostgreSQL container shares only that
network namespace, listens on `127.0.0.1` and owns a disposable tmpfs cluster.
The startup fixture applies the current ten migrations to `mixer_startup_test`.
There are no published ports, host source/socket mounts or production secrets.

Static source, lock, image/config and host-platform checks precede container
creation. Tool checks run in the already-owned containers. Restored source,
dependency/tool manifests, resource settings and namespace checks must pass
before the collector supplies `MIXER_ISOLATED_NETNS=1` to the test command.
An inherited flag never grants isolation. After preparation is removed, the
collector performs no downloads; compilation and both tests run offline.

## Evidence and bounds

The existing Mix test alias remains unchanged. The collector selects exactly
the two frozen test files, retaining the CLI formatter and adding an observer
that records actual suite/test events and loaded module identities. Acceptance
requires both exact methods to pass, zero skipped/excluded/invalid methods, a
complete suite, exit zero, matching fresh semantic receipts, unchanged source
and dependency/tool manifests, migration evidence and owned cleanup. Pure
collector controls do not establish actual Docker isolation or product behavior.
The existing TLS fixture discards successful OpenSSL command output. This
ordinary fixture lane does not provide a trace of all nine OpenSSL child commands
or qualify the separate held local custody protocol.

The workflow has a 15-minute limit. The collector has 660 seconds including a
30-second cleanup reserve; individual pull, bootstrap, dependency, compilation,
test, copy and cleanup bounds also apply. At most three containers are created
per attempt and at most two coexist. Output/archive/resource limits are fixed
in the collector. Reaching a bound produces failed or partial evidence.

Every Docker operation after creation uses the retained exact container ID and
checks its identity. Cleanup proceeds PostgreSQL, test, preparation. Permission
refusal, identity loss or an uncertain create response remains unknown; neither
another actor nor name/global enumeration is a fallback. Container force-stop
is recorded separately from graceful application shutdown. The finalizer uses
the original attempt identity and deadline. Hard cancellation or runner loss
can prevent cleanup/upload; missing evidence never counts as a pass.

The artifact retains command logs, input/tool/module manifests, bounded safe
archives, namespace/resource observations, both semantic receipts and cleanup
outcomes for 14 days. Root must download and independently verify the
digest-bound artifact before acceptance. A green workflow or successful upload
alone is insufficient. Private keys and tokens are excluded.

This lane does not qualify real OIDC issuance/rotation/discovery, public ingress,
browser sessions, Neon/Cloudflare operations, held local custody controls, UnitA,
native devices or GA. Production fixture exclusion is qualified by a separate
ordinary Phoenix run for the delivered source, or explicitly reviewed reuse of
unchanged-source evidence. Native runtime and computer-use pauses remain active.
