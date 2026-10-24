# Private Linux compiler/header payload preparation

V3's missing compiler prerequisite remains explicit. Its actual isolated probe
observed Elixir 1.20.4 / OTP 29.1.1 / ERTS 17.1 and matching NIF headers, then
exited 78 because native C tools and system development headers were absent.
V3 seal is `0286c4cf72503a913520b19bdd7f1b877da995d5d95cf62cc85744015603bf87`.
This packet performs source/read-only preparation only: no new container,
package/index/keyring download, package extraction, compiler execution, image
build or resource rootfs construction occurs.

The smallest proposed package root set is `gcc:arm64`, `libc6-dev:arm64` and
`binutils:arm64`, plus only their required dependency closure. This is a proposed
root set, not a resolved or proven minimum byte count. Noble's libc development
package supplies C headers and depends on exact libc plus Linux headers;
binutils supplies assembler/linker tools and native aarch64 components.
[Ubuntu libc6-dev](https://packages.ubuntu.com/noble/arm64/libc6-dev),
[Ubuntu binutils](https://packages.ubuntu.com/noble/binutils).

## Already-local evidence

The local `rust:1.90-slim` image has parent index
`sha256:7fa728f3678acf5980d5db70960cf8491aff9411976789086676bdf0c19db39e`
and inspected Linux arm64 child
`sha256:b16537bc14600b0dba0666efc948ef8f8067fa7e25d2bea70e4862f97eebe6d7`.
Its descriptor explicitly identifies `debian:trixie-slim`. Metadata does not
prove that its compiler/sysroot exists or runs against the observed Ubuntu
Noble runtime. No files were copied or tools run from that image. It is an
unqualified alternate candidate, not an accepted compiler payload.

Targeted retained-file and hosted/Stripe source searches found no native Linux
aarch64 GCC/libc-development compiler receipt. Retained Rust sysroot logs and
Swift guest sysroot bindings describe other targets; they do not qualify this
native GNU/Linux C compiler contract. The search scope is recorded; this is not
a claim that every local image or disk location lacks a compiler.

Host PATH discovery found curl/xz/ar/tar but no `gpgv` or `gpg`. The selected base
image's APT verifier, package status and archive-keyring identities have not yet
been observed. A separate bounded read-only probe should establish them first.
Do not bootstrap signature verification by silently installing a host package.

## Concrete official acquisition proposal

Use the official Noble arm64 ports archive, component `main`, with suites
`noble`, `noble-updates`, `noble-security`:

```text
https://ports.ubuntu.com/ubuntu-ports/dists/noble/InRelease
https://ports.ubuntu.com/ubuntu-ports/dists/noble-updates/InRelease
https://ports.ubuntu.com/ubuntu-ports/dists/noble-security/InRelease
```

The official Noble arm64 index exposes compressed `Packages` and `by-hash`.
Capture each signed release first, then use its authenticated compressed-index
hash/size and the strongest available collision-resistant by-hash path; prefer
SHA-512 when present, with SHA-256 minimum. Hash and retain all metadata locally.
[Official Noble arm64 index](https://ports.ubuntu.com/ubuntu-ports/dists/noble/main/binary-arm64/).

Use the Ubuntu archive public keyring from the already pinned base only after
its hash and signing fingerprints are observed, or separately select the official
keyring endpoint:
`https://archive.ubuntu.com/ubuntu/project/ubuntu-archive-keyring.gpg`.
Require full signer fingerprint
`F6ECB3762474EDA9D21B7022871920D1991BC93C` using a standard, content-pinned GPG
verifier. This is Ubuntu's documented 2018 archive signing key. Do not trust a
short key ID, TLS alone, `trusted=yes` or unauthenticated APT flags.
[Ubuntu archive fingerprints](https://wiki.ubuntu.com/Security/FAQ),
[Ubuntu key authenticity guidance](https://documentation.ubuntu.com/security/software-integrity/image-verification/).

Ubuntu authenticates release metadata, then index checksums, then package
checksums. The proposal does not assume that each `.deb` has its own signature.
Check expected Ubuntu origin, suite/codename, arm64, release dates and validity
before resolving candidates. No bypass of signature or date checks is selected.
[APT authentication chain](https://manpages.ubuntu.com/manpages/noble/man8/apt-secure.8.html).

Resolve against the exact base image's captured package status, with recommends
and suggests excluded. Emit a closed lock for every required `arm64` or `all`
package: exact name/version/architecture, suite/component, official relative
Filename, byte size, SHA-256, dependency reason and authenticated release/index
digests. The initial three package roots are not a complete filename list.
Reject other architectures, PPAs, unexpected origins, unsafe paths and unselected
redirects. Retain signed metadata and the complete archive cache for offline
replay; later mirror availability is not a reproducibility assumption.

Exact package revisions, filenames, sizes and hashes are **unresolved** here.
Current package-description pages are supporting documentation, not an
authenticated package lock. The generic timestamp snapshot documentation does
not establish a verified Noble arm64 ports endpoint in this packet; the proposal
therefore freezes authenticated ports metadata directly rather than inventing
an arm64 snapshot URL.

## Bounded phases for root selection

1. Read-only base-tool probe: exact pinned parent/child image, isolated user,
   no network; capture `dpkg` package status, APT and GPG verifier identity, archive
   keyring identity and any existing package cache. No update/install/download.
2. Metadata-only acquisition: a clean bounded downloader fetches only the three
   official signed releases, their selected `main/binary-arm64` indexes and an
   explicitly selected keyring if necessary. New private storage, no host APT
   configuration/cache or inherited credentials/proxy configuration. Verify
   before parsing or solving. Emit the closed package lock and stop for root
   selection before any `.deb` transfer.
3. Root selects that exact lock and a separate bounded package transfer. Fetch
   only official URLs formed from authenticated safe package filenames. Enforce
   signed size and SHA-256 before any extraction. No rolling `apt install`,
   source build, C++ compiler, make, build-essential or unrelated development
   tools are part of the proposed roots.
4. Separately selected offline private tool-payload/image assembly uses only the
   verified package data and pinned base. No global/shared host install and no
   maintainer script runs on the host. Preserve required compiler links and
   installation-prefix layout inside the owned payload; any generated `/usr/bin/cc`
   link must resolve to the recorded native compiler bytes, without a wrapper or
   changed compiler flags. Record every payload file, link, tool component and
   library dependency. Any required package setup not represented by audited
   package data is an explicit blocker for separate review.
5. Root selects a fresh offline nonroot compilation probe using unchanged V5
   source, flags and environment, then static ELF inspection. No helper execution,
   NIF loading, hosted application or resource row is included.

All five phases are unselected proposals. `proposal.json` splits metadata
capture, dependency resolution, package transfer, assembly and compilation into
six machine-readable phases so each has a concrete review boundary.

| Bound | Proposed hard limit |
| --- | --- |
| Metadata transfer / expanded metadata | 32 MiB / 256 MiB |
| Keyring / each signed release | 1 MiB / 1 MiB |
| Package transfer / each package | 128 MiB / 64 MiB |
| Package count / expanded package data | 48 / 512 MiB |
| Newly owned storage | 768 MiB |
| Metadata / package transfer wall bound | 120 s / 180 s |
| Per request / retries / parallel fetches | 30 s / 0 / 1 |
| Retained stdout / stderr | 512 KiB each |

These are safety ceilings, not measured package sizes or delivery estimates.
An over-limit closure or transfer fails; it does not expand its own authorization.
Use a new mode-0700 directory with isolated metadata/cache/partial/payload paths.
Keep new artifacts until root has reviewed the receipt; remove only owned
partial data and disposable workspaces after evidence collection.

The observed base has glibc 2.39, but its exact Debian package revision is not
recorded. `libc6-dev`'s exact libc dependency makes that status a required input.
Choose development packages compatible with the captured installed runtime;
if a runtime library replacement is required, stop for root selection of the
complete derived-image file/hash delta. The prior V3 runtime hashes cannot
silently qualify new libc, compiler or loader bytes.

The future compiler closure must include the resolved `/usr/bin/cc`, cc1,
collect2, assembler, linker, GCC private headers/libraries, libc/Linux headers,
crt startup objects, linker scripts and their runtime libraries. Existing V3
ERTS header hashes remain inputs. Availability of a gcc binary alone is
insufficient. A private tool image is distinct from the later resource rootfs;
this packet constructs neither.

## Host-only verification and remaining blockers

```text
python3 -B verification/stripe-resource-linux-compiler-preparation/host_checks.py
```

The replay checks the preparation proposal and preserved packet hashes. Seven
finite controls cover the valid unselected proposal plus rejection of invented
acceptance, a fabricated resolved lock, claimed container execution, unauthenticated
acquisition, excessive package bytes and a selected future phase. These are
host/data controls, not a tested downloader or signature verifier.

Unknown package status, verifier/keyring identity, authenticated indexes,
dependency lock, package bytes, payload assembly and actual compilation remain
blocking prerequisites. No compiler artifact, Linux enforcement, all-30-row
matrix, production or GA acceptance follows. No namespace/cgroup/core-policy,
provider/native/device, catalog-inspector or authority-driver work occurs.
