from pathlib import Path
p=Path('.github/workflows/identity-network.yml');s=p.read_text();s=s.replace("      - 'verification/identity-production-network-contract/**'", "      - 'verification/identity-production-network-contract/**'\n      - 'verification/identity-network-image-amendment-v1/**'");s=s.replace('            /verification/identity-production-network-contract/**','            /verification/identity-production-network-contract/**\n            /verification/identity-network-image-amendment-v1/metadata/**');p.write_text(s)
p=Path('docs/hosted-identity-production-network-ci-contract.md');s=p.read_text();needle='## Runtime boundary\n';add='''The historical contract remains sealed and unchanged. The selected image-only
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

''';assert needle in s;s=s.replace(needle,add+needle)
s=s.replace('''OTP File and crypto/SSL facilities supply the remaining bootstrap operations.
Missing tools fail the attempt; no package install,''','''Each observed executable's size and SHA256 must equal its sealed source object.
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
authorization. No package install,''')
s=s.replace('''The artifact retains command logs, input/tool/module manifests, bounded safe
archives,''','''`selected-contract-metadata.tar` preserves both full path namespaces: the old
contract and its original Elixir/PostgreSQL metadata, plus the complete selected
amendment and source-review metadata. The workflow checks out the sealed
amendment metadata and both push/PR filters include its parent path.
Implementation and pure-control receipts live outside the metadata self-seal.

The artifact retains command logs, input/tool/module manifests, bounded safe
archives,''')
s += '''\nThe image amendment's authoring receipt covers source and pure Python controls
only. Fresh remote tool/crypto/CA execution, TLS downloads, Hex/Rebar execution,
dependency resolution, compilation, the two product methods, isolation and
cleanup remain pending until independently reviewed runtime evidence exists.
'''
p.write_text(s)
p=Path('THIRD_PARTY.yml');s=p.read_text();needle='# Selected by the October 24 hosted-stack plan.'
assert needle in s
entries='''  - name: Hex Elixir Debian Bookworm AMD64 identity verification image
    origin: https://hub.docker.com/r/hexpm/elixir
    version: "1.20.4-erlang-29.1.1-debian-bookworm-20261005-slim"
    license: image-component-license-and-notices-review-pending
    purpose: isolated-remote-production-DNS-and-TLS-fixture-verification
    distribution: external-verification-tooling-never-linked-into-product
    owner: cloud-verification
    parent_digest: sha256:1ae099301985ddf8a723ad50cc25e37dd854497aec12cebf984c195570b0d83e
    platform_digest: sha256:ed110657152803079f311913be4effe02874e2c714a1b5a38891873b7f2a16c5
    config_digest: sha256:857e84a618d1f76390220fbff2e7d54d588aea4f772ab1e60dacfe3fa02602cc
    platform: linux-amd64
    inventory_receipt: verification/identity-network-image-amendment-v1/metadata/image-amendment.json
    source_inventory: verification/identity-network-image-amendment-v1/metadata/source-review/analysis/capabilities.json
    historical_predecessor: Noble-AMD64-entry-retained-run-40730443928-failed-required-openssl-stat-after-successful-tar-transfer
    historical_failure_receipt: verification/github-delivery-identity-network-transfer/network-review/selected/artifact/logs/0019.stderr
    qualification: all-four-layer-digests-and-source-object-inventory-verified-actual-runtime-tool-CA-TLS-and-tests-pending
  - name: Debian image-supplied OpenSSL and libssl3 identity verification tools
    origin: https://packages.debian.org/bookworm/openssl
    version: "3.0.22-1~deb12u1"
    license: source-license-and-component-notices-review-pending
    purpose: fixture-certificate-generation-and-OTP-crypto-TLS-runtime
    distribution: external-verification-image-only-never-product-linked
    owner: cloud-verification
    inventory_receipt: verification/identity-network-image-amendment-v1/metadata/source-review/analysis/capabilities.json
    qualification: source-package-status-executable-and-library-hashes-only-actual-load-and-version-commands-pending
  - name: Debian image-supplied CA certificates identity verification bundle
    origin: https://packages.debian.org/bookworm/ca-certificates
    version: "20250419~deb12u1"
    license: source-license-and-individual-certificate-notices-review-pending
    purpose: selected-OS-trust-bundle-for-peer-and-hostname-verified-bootstrap
    distribution: external-verification-image-only-never-product-linked
    owner: cloud-verification
    path: /etc/ssl/certs/ca-certificates.crt
    bytes: 224449
    sha256: 714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5
    inventory_receipt: verification/identity-network-image-amendment-v1/metadata/source-review/analysis/capabilities.json
    qualification: source-bytes-and-150-DER-hashes-only-actual-OTP-loading-and-HTTPS-chain-verification-pending
  - name: Debian image-supplied GNU tar identity verification tool
    origin: https://packages.debian.org/bookworm/tar
    version: "1.34+dfsg-1.2+deb12u1"
    license: source-license-and-component-notices-review-pending
    purpose: bounded-archive-transfer-in-readonly-owned-verification-containers
    distribution: external-verification-image-only-never-product-linked
    owner: cloud-verification
    inventory_receipt: verification/identity-network-image-amendment-v1/metadata/source-review/analysis/capabilities.json
    qualification: immutable-source-object-hash-and-package-status-only-actual-command-pending
  - name: Debian image-supplied GNU coreutils identity verification tools
    origin: https://packages.debian.org/bookworm/coreutils
    version: "9.1-1"
    license: source-license-and-component-notices-review-pending
    purpose: exact-env-entrypoint-for-container-environment-allowlist
    distribution: external-verification-image-only-never-product-linked
    owner: cloud-verification
    inventory_receipt: verification/identity-network-image-amendment-v1/metadata/source-review/analysis/capabilities.json
    qualification: immutable-env-source-object-hash-and-package-status-only-actual-command-pending
  - name: Debian image-supplied identity verification runtime libraries
    origin: https://www.debian.org/distrib/packages
    version: "libc6-2.36-9+deb12u14_libodbc1-and-libodbc2-2.3.11-2+deb12u1_libsctp1-1.0.19+dfsg-2_libstdc++6-12.2.0-14+deb12u1"
    license: per-source-package-license-and-component-notices-review-pending
    purpose: image-supplied-OTP-OpenSSL-and-system-tool-runtime-prerequisites
    distribution: external-verification-image-only-never-product-linked
    owner: cloud-verification
    inventory_receipt: verification/identity-network-image-amendment-v1/metadata/source-review/analysis/capabilities.json
    qualification: source-package-status-and20-static-ELF-object-closure-only-dynamic-symbol-loading-and-runtime-pending
'''
s=s.replace(needle,entries+needle);p.write_text(s)
