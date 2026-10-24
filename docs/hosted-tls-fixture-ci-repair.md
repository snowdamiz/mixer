# Hosted TLS fixture CI portability repair

The test-only TLS fixture now joins its random directory name to
`System.tmp_dir!()` instead of `/private/tmp`. The unchanged accepted identity
matrix passes all **45 Mac cases** and **46 isolated Linux cases**. Independent
root review and the full hosted CI rerun are separate evidence.

## Failure and scope

The hosted CI run at `dd604eca4d3c01ade0dce084aedb2571978632ad` reported
44 passed, 29 invalid, and 1 skipped. Its identity `setup_all` could not create
`/private/tmp/mixer-key-owner-tls-*` because `/private/tmp` does not exist on that
Linux runner. The original record remains unchanged at
`verification/github-ci-dd604eca-phoenix/artifact/tests.log` (SHA-256
`c865ad86878ab09ab00501c1740be3d53a05d2ccd0c1cb1ebdf8dac53895a39e`).
The older accepted Linux collector explicitly ran `mkdir -p /private/tmp`, which
masked the fixture's platform assumption.

The sole source edit in this slice is in
`hosted/test/support/identity_tls_fixture.ex`. This repair changes no production
sources, existing test cases, or dependencies. Neither matrix run changed the
accepted historical packets. The fixture still uses 16 cryptographically random bytes in its
directory name, exclusive `File.mkdir!`, mode `0700`, OpenSSL-created ephemeral
keys inside that private directory, and `after` cleanup before starting its
listener. No fallback path, shared directory, or recursive creation was added.

## Executed matrix

The append-only packet is `verification/hosted-tls-fixture-ci-repair/`.

| Run | Environment | Result |
| --- | --- | --- |
| `macos-final-canonical/` | macOS 27.0.1, Elixir/Mix 1.20.4, OTP 29, OpenSSL 4.0.3 | 45 passed; fixture format check passed; no new TLS key directories retained |
| `linux-final/` | pinned Hexpm arm64 Linux image, Elixir/Mix 1.20.4, OTP 29, OpenSSL 3.0.13 | 46 passed; `/private/tmp` absent before and after; system temporary directory `/tmp`; no TLS key directories retained |

The unchanged Mac command is `mix test --seed 0` with
`test/mixer_hosted/identity/key_owner_test.exs` and
`test/mixer_hosted/identity/access_token_verifier_test.exs`. Linux additionally
runs `test/mixer_hosted/identity/key_owner_linux_network_test.exs` in a disposable
`--network none --cap-add NET_ADMIN` container. Its own namespace binds
`8.8.8.8` on `lo:1` for the existing production DNS/rebinding test. No host or
other container network is changed. The image is
`hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde`.
There is no `/private/tmp` creation in this collector.

Both matrices use owned source/dependency snapshots. The unchanged tests write
their resource observations under those snapshots; the collector copies them
into this packet instead of overwriting the prior accepted key-owner packet.
Per-run manifests record source and dependency file hashes and aggregate tree
digests; execution records contain exact commands, environment, elapsed time,
exit status and output hashes. Tool logs and the Docker image inspection are
retained. Each cleanup receipt verifies owned scratch/container removal,
retention of all preexisting container IDs, and unchanged historical packet and
original CI failure hashes.

The first two Mac collector attempts, `macos/` and `macos-final/`, failed while
compiling JOSE, before tests ran. The macOS temporary path used `/var/folders`
while the physical working directory used `/private/var/folders`, breaking Mix's
relative dependency-header symlink. A conventional build directory alone did
not resolve that alias mismatch. The final collector canonicalizes the owned
scratch directory and passes from a clean build. Both failed outputs, command
records, source/dependency manifests, cleanup receipts, and runner revisions
remain in the packet.

## Source binding and limits

The tested parent revision is
`dd604eca4d3c01ade0dce084aedb2571978632ad` plus the one-line fixture edit.
The fixture SHA-256 is
`1ebb466459c4cf07e23bad66dcabc080b3f3348c5c12d974b28ef88ded1de1e2`;
the complete copied hosted source tree digest is
`52dcbb66accb6e357e6afcd27adecb0919d02c4359db1a48542620110e896125`;
the dependency tree digest is
`99bc0e5256ca834e5cd24bfcd3a1f5b158d5479af5677cccbe998ee005628452`.
The source and dependency aggregate digest is SHA-256 of the UTF-8 JSON file-hash
map with sorted keys and compact separators. Inputs were unchanged during each
passing run. `receipt.json` and `evidence-manifest.json` bind the completed packet.

These are host component tests, including the isolated Linux network case.
They do not establish physical-phone, store, hosted production startup,
external-provider, customer, immutable-package dogfood, or GA acceptance. Full
hosted-suite/release/database and rerun GitHub CI results belong to root review.
Root's subsequent receipt-output hygiene changes and their acceptance use a
separate source-bound packet; they are outside these matrix snapshots.
