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

The historical contract remains sealed and unchanged. The selected image-only
amendment is `verification/identity-network-image-amendment-v1/metadata/`.
Its `image-amendment.json` SHA256 is
`6a2ec88721d89a28e40961f834b856598ba0f6f14d88708906cf3931e0e33afa`;
its packet root is
`9ddc12c8277b120dcd8ef7577dd9da03d245b8502802db85399a6f1104bcbdc8`.
The collector requires both the predecessor seal and this compiled amendment
seal before an image pull or container creation. This is a closed replacement
of the preparation/test image. The 177 product files, lock, PostgreSQL image,
bootstrap checksums, selected test methods, paths, isolation and resource bounds
remain bound to the predecessor contract. An arbitrary metadata overlay cannot
supply change authority.

The failed Noble AMD64 image is retained in the predecessor. Actions run
`40730443928` for `0b99469dfbeb06ac53ad0223bd070a35f2a6a700` completed the
corrected tar transfer and then failed `File.stat!("/usr/bin/openssl")` before
its version checks. Its source package-install layer is empty. The full sealed
source review at amendment `metadata/source-review/` records that observation,
all four replacement layer digests/diff IDs and the actual source tool and CA
objects. Source inspection establishes no executable runtime pass.

| Selected replacement identity | Immutable value |
| --- | --- |
| Official image tag | `hexpm/elixir:1.20.4-erlang-29.1.1-debian-bookworm-20261005-slim` |
| OCI index | `sha256:1ae099301985ddf8a723ad50cc25e37dd854497aec12cebf984c195570b0d83e` |
| Linux AMD64 manifest | `sha256:ed110657152803079f311913be4effe02874e2c714a1b5a38891873b7f2a16c5` |
| Config | `sha256:857e84a618d1f76390220fbff2e7d54d588aea4f772ab1e60dacfe3fa02602cc` |

The selected execution amendment is
`verification/identity-network-image-amendment-v2/metadata/`. Its contract SHA256
is `b447fe5919c4e73d86aee4da707570127de2c35ecdae5a7b90b0163eb9bc436c`,
its packet tree is `0e35cd6dcc1685b16745def4fe0217fc60e5d703c95a5cddbfd2409381c63b6d`,
and its exact packet bytes have SHA256
`dcac91f5cae0a2495f79448a76098975edc18db0ce96a1e769106244a0cf8061`.
It preserves the
original contract, v1 image amendment and their source-review packets. V2 is a
closed carve of the existing 1 GiB workspace allowance into these mounts in
both preparation and test containers:

| Path | Bytes | Execution policy | Other required flags/mode |
| --- | --- | --- | --- |
| `/workspace` | 1,006,632,960 | explicit `noexec` | `rw,nosuid,nodev,mode=0755` |
| `/workspace/tooling` | 67,108,864 | explicit `exec` | `rw,nosuid,nodev,mode=0755` |
| `/tmp` | 67,108,864 | explicit `noexec` | `rw,nosuid,nodev,mode=1777` |

The workspace and tooling capacities sum to the previous 1,073,741,824 bytes.
The test `/run` declaration, PG mounts, memory/CPU/PID limits and capabilities
remain unchanged. Test `/run` must actually be `noexec`. Only the exact selected
nested tooling mount may appear beneath the selected paths; additional
submounts fail. No broader workspace execution is authorized.

Run `40740023326` for `cc350d3303ca71c5d57e87846f6a61304b658fa7` supplied actual
preparation evidence for all seven required tools, CA150, VM and OpenSSL
identities, then failed command 22 with EACCES spawning
`/workspace/tooling/rebar3 --version`. Its retained incomplete-stream flags
remain false. Docker 28.0.4's pinned source supplies a default `noexec` flag;
the missing override and EACCES support that cause as an inference. The prior
run retained no actual mountinfo and provides no complete bootstrap result.
The exact Mix 1.20.4 Unix path also invokes Rebar directly, so merely changing
the bootstrap invocation would leave dependency compilation affected.

The nested tooling mount makes the existing download and final Rebar paths
separate filesystems. Bootstrap therefore copies the already checksum-verified
bounded source at `/workspace/downloads/rebar3` into an absent, exclusively
created `/workspace/tooling/rebar3`. It requires a complete write and close,
exact target size and SHA512 before chmod or direct execution, then removes
only the owned download. A structured transfer receipt must join the verified
download bytes, final bytes, checksum, exclusive create, close and removal
facts. Short copy, existing target or hash mismatch fails; there is no rename
fallback or alternate staging path.

V2 binds that raw failed-run proof and the unchanged actual prerequisite
invariants. Every fresh attempt still executes its own prerequisites. After
copy-in, a fixed helper reads at most 64 KiB from `/proc/self/mountinfo` inside
the exact owned preparation or test container. It retains only the selected
paths and any descendant contradictions, plus their actual modes and a hash
of the bounded read. Independent consumer checks require tmpfs, `rw`, `nosuid`,
`nodev`, exact capacities, workspace/tmp/run `noexec`, tooling executable and
tooling's parent mount matching the workspace mount. This actual evidence and
the existing Docker inspection guards must both pass before bootstrap or test
authorization. The helper starts no child process or mount operation.

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
Each observed executable's size and SHA256 must equal its sealed source object.
The prerequisite helper also checks the regular CA file
`/etc/ssl/certs/ca-certificates.crt`: exactly 224,449 bytes and SHA256
`714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5`.
It explicitly loads that selected OS bundle with OTP `cacerts_load/1` and records
all 150 loaded certificate DER hashes. Nonempty loaded roots must match the
sealed source certificate hashes. Both preparation and test prerequisites
require actual Mix, OpenSSL and tar version output and structured OpenSSL
library name, numeric identity and full version text from `crypto.info_lib/0`.
Source package declarations remain separate from command observations.

The bootstrap starts a separate VM, verifies the same exact CA-file identity,
and explicitly loads the same bundle before its existing peer, hostname and
SNI verified HTTPS downloads. The pinned OTP API source is retained in the
amendment. OTP File and crypto/SSL facilities supply the remaining bootstrap
operations. Missing or mismatched prerequisites fail before bootstrap or test
authorization. No package install,
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

The shared file exporter explicitly requires
`:ok = :io.setopts(:standard_io, encoding: :latin1)` before checked
`IO.binwrite`. This preserves stored bytes for both public bootstrap tools,
the prepared tar archive, events, semantic receipts and runtime identity.
Elixir's standard IO defaults to Unicode; its exact 1.20.4 IO source warns
that binary writes through a Unicode device alter bytes.

Run `40746908101` for `fb7c7f20f8a308424ef4b7092d19d3d4de2c7627` passed actual
preparation mount policy, prerequisites, exclusive Rebar transfer, direct
Rebar version and bootstrap. It then failed host validation of the Hex export
after command 28. The command returned exit zero with complete streams, but
its output was 1,693,010 bytes instead of the 1,133,941 downloaded bytes.
A fresh exact pinned Hex download transformed from Latin-1 to UTF-8 matches
the recorded export length and SHA256. The failed raw export was deleted by
the old scratch cleanup, so that explanation is a source- and hash-supported
inference; those original failed bytes are unavailable. The sealed review is
`verification/github-delivery-runtime-followup/network-review/`.

Only the fixed public paths `/workspace/downloads/hex.ez` and
`/workspace/tooling/rebar3` now retain bounded actual command stdout under
`bootstrap-exports/{hex,rebar}-actual.bin`, before any host length or SHA512
rejection. Each capture has an actual byte count, SHA256/SHA512 and exact
command completion/exit facts; partial output stays partial. Each is at most
16 MiB and the existing total artifact cap still applies. Repeat capture
cannot overwrite retained failure evidence. Host acceptance requires the
exact downloaded length and unchanged pinned SHA512. Verified bootstrap
filenames are written only after those checks. Other allowed export paths
retain their previous scratch handling; no additional container path or
private file retention is authorized. Source and pure control evidence is in
`verification/identity-network-binary-export-correction/`.

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

`selected-contract-metadata.tar` preserves all three full path namespaces: the
original contract and Elixir/PostgreSQL metadata, the complete v1 image
amendment/source review, and the complete v2 execution amendment/raw proof.
The workflow checks out both sealed amendment metadata packets and both
push/PR filters include their parent paths.
Implementation and pure-control receipts live outside the metadata self-seal.

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

The binary-export correction covers source and pure Python controls only.
The reviewed prior run qualifies actual preparation tool/crypto/CA and mount
results, complete bootstrap/direct Rebar execution, and exact owned cleanup
for that failed attempt. Corrected Hex and Rebar host exports, locked dependency
resolution, prepared archive transfer/restore, compilation, the two product
methods and all new-attempt isolation/cleanup remain pending independently
reviewed runtime evidence.
