# Identity image prerequisite source review

This packet proposes an exact-toolchain official image replacement for root review. It changes no canonical source, executes no image binary, selects no runtime, and accepts no product or GA gate.

The failed delivery is parent-supplied commit `0b99469dfbeb06ac53ad0223bd070a35f2a6a700`, Actions run `40730443928`. The independently retained command `logs/0019.json` runs the prerequisite helper under Elixir 1.20.4 and fails at `File.stat!("/usr/bin/openssl")`. It does not reach its OTP, Mix, OpenSSL or tar version assertions. Absence at that path does not establish absence elsewhere. The retained shutdown log also reports missing `libsctp.so.1`; that warning is separate from the primary failure.

The selected Noble AMD64 manifest `3571d320…`/config `6631543f…` records an AMD64 final-stage install using `libssl3t`, while ARM64 uses `libssl3t64`. The matching [official recipe at pinned source](https://github.com/hexpm/bob/blob/576c9253bd7a81c628d4e731ef406a44246db4a4/priv/scripts/docker/erlang-ubuntu-noble.dockerfile) has those exact spellings and separates install/cleanup commands with semicolons. The recipe retrieved at current pinned Bob revision `dc98c8b766f3174fe3a8e3ee6375cce284c5e1bf` is byte-identical. This matches the image history; it is not a verified image-to-source provenance attestation.

The root-selected 32-byte OCI package-install layer `4f4fb700…` is a digest-verified, zero-member empty tar: uncompressed 1,024 bytes, diff ID `5f70bf18…`. Thus that layer adds no OpenSSL, CA store, SCTP or other package objects. A failed package install masked by later cleanup is an inference consistent with the recipe, empty layer and runtime warning; no historical build log was observed. The image's other layers were not inventoried here, so no whole-image absence claim is made. No path-only correction is supported by this evidence.

The concrete alternative is:

| Identity | Value |
| --- | --- |
| Official tag | `hexpm/elixir:1.20.4-erlang-29.1.1-debian-bookworm-20261005-slim` |
| OCI index | `sha256:1ae099301985ddf8a723ad50cc25e37dd854497aec12cebf984c195570b0d83e` |
| Linux AMD64 child | `sha256:ed110657152803079f311913be4effe02874e2c714a1b5a38891873b7f2a16c5` |
| Config | `sha256:857e84a618d1f76390220fbff2e7d54d588aea4f772ab1e60dacfe3fa02602cc` |

Official tag/API metadata and exact registry JSON are retained. The [pinned Bookworm recipe](https://github.com/hexpm/bob/blob/dc98c8b766f3174fe3a8e3ee6375cce284c5e1bf/priv/scripts/docker/erlang-debian-bookworm.dockerfile) installs `ca-certificates`, `libodbc1`, `libssl3`, `libsctp1` and `netbase` with `&&`; source matching is comparison evidence. Its actual four OCI layers were fully inventoried, including whiteouts, file modes, symlinks and hardlinks. Compressed SHA256 and all four uncompressed config diff IDs matched. No image was imported, mounted or extracted to a filesystem. Only inventories and bounded selected text remain.

| Required source object | Observed archive evidence |
| --- | --- |
| `/usr/bin/env` | executable regular ELF; coreutils `9.1-1` |
| `/usr/bin/tar` | executable regular ELF; tar `1.34+dfsg-1.2+deb12u1` |
| `/usr/bin/openssl` | executable regular ELF; OpenSSL/libssl3 `3.0.22-1~deb12u1` |
| `/usr/local/bin/elixir`, `mix` | links resolve to executable files; `elixir.app`/`mix.app` declare `1.20.4` |
| `/usr/local/bin/erl`, `escript` | links resolve to executable script/ELF; installed `OTP_VERSION` says `29.1.1` |
| `/etc/ssl/certs/ca-certificates.crt` | 224,449 bytes; SHA256 `714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5`; 150 PEM certificates; package `20250419~deb12u1` |
| `libsctp.so.1` | resolves to regular AMD64 ELF in candidate image |

`analysis/capabilities.json` records exact hashes and link traces for 13 relevant paths, source package versions and 20 recursively resolved ELF objects. PT_INTERP/DT_NEEDED objects are present as immutable source objects. This does not prove dynamic symbol compatibility, provider loading, kernel execution, command capability or Docker policy compatibility.

The [exact OTP 29.1.1 CA loader](https://github.com/erlang/otp/blob/OTP-29.1.1/lib/public_key/src/pubkey_os_cacerts.erl) tries `/etc/ssl/certs/ca-certificates.crt` first on Linux unless the public-key application explicitly overrides its CA path. The collector's fixed HTTPS bootstrap uses `verify_peer`, `cacerts_get`, SNI and HTTPS hostname validation. The proposal retains that contract and requires actual nonempty CA loading and real endpoint TLS evidence; PEM shape/source hashes are not a TLS verification result. [Debian's package metadata](https://packages.debian.org/bookworm/ca-certificates) declares its OpenSSL dependency, and [its OpenSSL file list](https://packages.debian.org/bookworm/amd64/openssl/filelist) corroborates `/usr/bin/openssl`; actual candidate layers provide the decisive file evidence.

Hex `2.5.1` and Rebar `3.28.0` keep the predecessor's exact official OTP-29 artifact URLs/SHA512 values. They were neither downloaded nor executed here. Their actual version commands and compatibility under Elixir 1.20.4/OTP 29.1.1 remain required before dependency resolution. The alternative needs no opportunistic package install, path fallback, host cache, TLS exception or product/test fixture change.

`analysis/amendment-candidate.json` identifies every proposed pin/metadata/inventory change. Root must preserve the historical contract packet, seal a selected amendment, bind old and new metadata in the collector, update positive/rejection controls, and add the amendment path to both workflow filters and sparse checkout. `THIRD_PARTY.yml` must retain historical Noble entries and append the candidate and packaged verification-tool inventory. The 177 frozen product blobs, dependency lock, PostgreSQL image, bootstrap checksums, no-credentials environment, read-only root, no-bind isolation, network/capability policy, resource bounds and two selected tests remain the same.

All HTTP requests were public official source/metadata or root-selected exact OCI blobs, bounded to at most 55 seconds each. Five layer responses totaled 86,423,309 compressed bytes; verified inventories total 175,285,760 uncompressed bytes. The first parser attempt refused an ELF incorrectly listed as text; its partial output and source are retained, and the already verified OTP blob was reused without another download. A later source-only analysis initially demanded an executable bit on the SCTP shared library; that check was corrected for a data-loaded shared library. Neither parser issue involved image execution. All five owned compressed blobs were removed after complete digest-bound inventory retention. No Docker, PG, test-local, process inventory, native/UI/capture action, Git/index/metadata write, credential change or canonical source edit occurred.

Actual fresh remote tool/crypto/CA/bootstrap execution, offline compilation, the two synthetic network tests, isolation and cleanup remain unqualified. Root chooses the next source amendment; this packet authorizes none of those actions by itself.
