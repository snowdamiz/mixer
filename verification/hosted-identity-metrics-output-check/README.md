# Final Linux identity metrics output check

This packet verifies the final root-owned metrics-output helper changes against
the complete existing 46-case isolated Linux identity matrix. It does not change
product code, tests, dependencies, prior evidence, or root's collector.

The collector creates an owned snapshot of current hosted sources and all local
locked dependencies, sets
`MIXER_TEST_IDENTITY_EVIDENCE=/workspace/identity-metrics`, and executes the three
existing identity test files. All nine expected metrics must be valid JSON in
that explicit directory. The previous source-relative
`/workspace/verification` path is deliberately absent; the collector fails if
it is created. Guards also require `/private/tmp` to remain absent and the
system temporary directory to contain no retained TLS fixture directories.

`linux-final/source-differences-from-repair.json` records the exact file hashes
against the frozen one-line repair snapshot. Only these three files differ:

- `hosted/scripts/test-local.py`
- `hosted/test/mixer_hosted/identity/key_owner_test.exs`
- `hosted/test/mixer_hosted/identity/key_owner_linux_network_test.exs`

The TLS fixture and every production source and dependency remain identical to
the repaired accepted matrix. The complete source/dependency manifests bind
every copied input, including the unexecuted root collector file. This packet
tests the identity helper's explicit output path; root's separate hosted suite
checks the collector's own invocation behavior and the unset helper path.

The Docker image digest, exact argv, output hashes, Docker tool information,
OS/Elixir/Mix/OpenSSL/OTP/SSL versions, Hex archive and Rebar source closure,
network namespace setup, and source diff are retained. The container has
`--network none --cap-add NET_ADMIN` so the existing production DNS/rebinding
test can use public `8.8.8.8` only inside its own namespace. No host or other
container route is changed.

Cleanup checks remove only the owned scratch directory and uniquely named
container, retain all preexisting container IDs, and compare both frozen
historical evidence trees and the original CI failure log to their pre-run
hashes. `receipt.json` and `evidence-manifest.json` bind the final result after
the run. Reruns require a new output directory; old results are not overwritten.

This is a Linux host component check. It does not establish physical-device,
store, GA, customer/provider, hosted production-startup, database, full-hosted
suite, or rerun GitHub CI acceptance. Those scopes remain separate.
