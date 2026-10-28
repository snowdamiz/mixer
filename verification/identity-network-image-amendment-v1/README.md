# Identity network image amendment v1

This packet authors the root-selected, closed replacement of the preparation/test
image after Actions run `40730443928` for `0b99469dfbeb06ac53ad0223bd070a35f2a6a700`
completed tar transfer and failed the required `/usr/bin/openssl` prerequisite.
It does not execute an image, authorize remote runtime, or accept a product/GA
gate. No product engine/test/fixture source is changed.

The immutable amendment is `metadata/image-amendment.json`, SHA256
`6a2ec88721d89a28e40961f834b856598ba0f6f14d88708906cf3931e0e33afa`.
`metadata/packet-manifest.json` seals 78 files with canonical tree SHA256
`9ddc12c8277b120dcd8ef7577dd9da03d245b8502802db85399a6f1104bcbdc8`.
Implementation receipts and snapshots are outside this metadata self-seal. The
outer `packet-manifest.json` seals this review packet separately.

The amendment binds the historical contract SHA256
`695a165d41e9d4eac5fdc582b835a60f5c3bbdd6f0fb3131c0ad27ffbbe135bc`, its exact
packet bytes and tree root, both old and new image identities, the 177-file
product/lock freeze, unchanged PG/bootstrap/method contracts, seven exact tool
source rows, and the exact CA bundle plus 150 sorted source DER hashes.
`metadata/source-review/` is an unmodified complete copy of the FINAL 71-file
prerequisite source packet, root
`261023b77cb55255f666959f367330783a354174252ed23b71145566f87ba597`, plus its original
manifest. Its source-only capability/ELF/CA observations remain source evidence.

The new official image is
`hexpm/elixir:1.20.4-erlang-29.1.1-debian-bookworm-20261005-slim`:

| Object | SHA256 |
| --- | --- |
| OCI index | `1ae099301985ddf8a723ad50cc25e37dd854497aec12cebf984c195570b0d83e` |
| Linux AMD64 child | `ed110657152803079f311913be4effe02874e2c714a1b5a38891873b7f2a16c5` |
| Config | `857e84a618d1f76390220fbff2e7d54d588aea4f772ab1e60dacfe3fa02602cc` |

The collector validates the two immutable namespaces and their OCI
index/child/config relationships before Docker operations. The retained
`selected-contract-metadata.tar` contains old Elixir/PG metadata and the entire
new amendment under distinct full paths. No overlay, image fallback, package
installation, custom build, opportunistic tool download, path substitution or
TLS weakening is introduced. The workflow retains its existing runner, limits,
pinned Actions, permissions, cleanup and upload behavior; both filters now
include this packet and sparse checkout includes its sealed `metadata/`.

Both actual preparation and test prerequisite results must match source-pinned
executable sizes/hashes and version identities. They must observe the regular
`/etc/ssl/certs/ca-certificates.crt` file, 224449 bytes, SHA256
`714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5`, explicitly load
that selected OS bundle, obtain nonempty loaded roots and match all 150 DER
hashes to the immutable source inventory. Full actual crypto library identity
is retained; the accepted structured library is OpenSSL with a positive numeric
identity and version prefix `OpenSSL 3.0.22 `, without inventing a release date.

The [pinned OTP 29.1.1 API source](https://github.com/erlang/otp/blob/OTP-29.1.1/lib/public_key/src/public_key.erl)
is retained in `metadata/inputs/official/`. It establishes that `cacerts_load/1`
loads the supplied file and `cacerts_get/0` returns combined certificate records.
The helper hashes the DER member of each record. Bootstrap runs in its own VM
and independently checks and loads the same exact bundle before the existing
`verify_peer`, HTTPS hostname and SNI verified downloads. Existing endpoint,
HTTP, SHA512, byte/time, no-redirect/no-encoding and installation rules remain.

`implementation/canonical.diff` and `implementation/{before,after}/` retain the
five canonical source changes. `implementation/source-bindings.json` pins their
final bytes; canonical source tree digest is
`bb21492941740aed5ed9202f8aa744461ed1c90be582da5b4b03ea7cabafc773`.
`THIRD_PARTY.yml` appends six verification image/tool/library entries and preserves
every prior entry. Image/component licenses and notices that were not examined
remain explicitly unresolved; no legal or redistribution approval is inferred.

The final guarded command `python3 -B hosted/scripts/test_identity_network_collector.py`
passed 84 tests in 0.440 seconds on Python 3.14.8. All 68 original test method
bodies are byte-for-byte unchanged; only their global Elixir fixture identity
changes to the selected image. Sixteen new controls cover positive selection,
old-image/index refusal, every missing metadata file, byte drift, stale and
self-recomputed seals, extra overlays, both metadata archive namespaces, actual
CA/roots/tool/crypto/version facts and collector gating before image/bootstrap
operations. The test module globally refuses child processes and sockets;
its existing 50-second alarm bounds each run.

The first 82-control run passed. The first 84-control run exposed a fixture
mistake: a new wiring control read the intentionally protected dirty working
store instead of committed product bytes, and source admission correctly
refused it before the intended assertion. That failure is retained. The two
new boundary controls now explicitly stub unrelated product-source admission
and assert the intended metadata/prerequisite refusal; they are not source or
runtime qualification. The independent source controls remain unchanged, and
`implementation/verify-source.py` separately reads all 177 committed Git blobs
and confirms digest `023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e`.
The full original 46-file contract packet also rehashes exactly.

The source-check command observed root-owned HEAD
`b6410e917fab899731dece2678fe2ade2e854464`, tree
`0aa557395a247d99eaf8267f63976ff439c04c6e`; the task began at `0b99469dfbeb06ac53ad0223bd070a35f2a6a700`.
This author made no commit/push. Live `.github/workflows/hosted.yml` remains
`fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57` and the protected
`hosted/lib/mixer_hosted/browser_auth/store.ex` remains
`8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299`.
The committed 177-source identity and protected live source are recorded
separately; working-directory bytes do not authorize the collector.

No Docker/PG/product/native/UI/capture runtime, held harness, process inventory,
package install, build, publication, credential change, or broad cleanup was
performed. Test temporary directories were owned and automatically removed.
Only one additional public official API source was fetched, bounded to 25 seconds
and 256 KiB; the exact response is retained. No source-review layer blobs were
reintroduced. Syntax/source analysis and pure controls prove no executable
Elixir/OTP behavior. Actual remote tool/crypto/CA loading, TLS downloads,
Hex/Rebar execution, dependency resolution, compilation, the two methods,
isolation and cleanup remain pending independent review and selected runtime.
