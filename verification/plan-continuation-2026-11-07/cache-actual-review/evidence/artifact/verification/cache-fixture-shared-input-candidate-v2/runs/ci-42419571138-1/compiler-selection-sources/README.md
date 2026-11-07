# Shared cache fixture: exact prospective compiler proposal

Run `40974383080`, attempt 1 at `5da968ea668ea0c319538321488b98ecda4db0bb`,
refused the actual hosted compiler before compilation: `Actual compiler
host/release not selected`. The retained `compiler-identity.stdout` identifies
Rust 1.99.1, Apple ARM64, commit `58cf8f9c35b355199727627d07ae34a4e2846d67`,
2026-10-13, LLVM 23.1.1. The resolved binary SHA-256 is
`1ba7bb8e273bd64125f4048d2ecce530e0a6470e565ab1b3aecf0b82b532f7b1`.
Only the sysroot and identity children ran; both returned successfully and the
fixture refused admission. Scratch cleanup was recorded successful. The job
log names `macos-15-arm64/20261028.0489.1`; its timestamps are October 29,
despite this investigation's November 7 directory name.

The standard adoption packet admits 1.98.1 and 1.99.0, and explicitly forbids
installation, automatic retry and fallback. This artifact establishes only a
`stable-aarch64-apple-darwin` sysroot, not an installed 1.98.1 path. The separate
`cache-fixture-compiler-admission-v3` packet describes an explicit Rustup install
as an uninstalled candidate requiring root selection; it supplies no authority
to add installation to this ordinary job. Consequently a supported available
pin cannot be established from these inputs. No compiler, Rustup, installation
or machine inventory was run to obtain more information.

`workflow.diff` is a proposed root-owned edit to only `swift-cache-state-fixture`.
It selects this new adapter explicitly, adds this directory to sparse checkout
and upload, and runs the new pure controls after the unchanged three original
control commands. The historical packet, compiler policy, tests, effective pack
and runner remain unchanged. The new adapter binds the historical closure,
delegates its runner loading, and substitutes only the identity callback.
That callback requires the exact retained verbose bytes and exact resolved
binary hash, rehashing it before compilation. It admits only this 1.99.1
identity; it adds no release wildcard, installation or fallback. The runner
still owns all 103 commands, one fixture invocation, 60-second children,
600-second active budget, 60-second cleanup, 8 MiB stream cap, source checks,
negative API controls, original assertions and custody safeguards. The new
adapter retains its own selection sources and always attempts source
postflight; success additionally requires the complete 103-command receipt.

This is an **uninstalled proposal for root review**, not implicit reuse of the
envelope's separate 1.99.1 selection. Applying the exact reviewed workflow is
the explicit shared-fixture selection for ordinary CI. Root must approve that
selection before application. A next ordinary push must run the complete
matching fixture and all original controls; independent actual artifact review
must qualify it. No successful run is promised if the hosted compiler changes.
Keep this run's baseline refusal and the prior full Debug timeout as failures.

Run local controls with:

```sh
python3 -I -B -S verification/plan-continuation-2026-11-07/cache-fix/test_selection.py -v
```

The inspected guard is installed before subject imports. It denies child
processes, process/group probes, signals, waits, sockets and sleeps, and confines
control writes to this new directory. Positives use inert files and explicitly
mocked compiler hash observations; fake fixture receipts establish orchestration
only. `controls.stdout`, `controls.stderr` and `receipt.json` record execution.
The complete original control suites and real 103-command fixture were not run
locally. Native/UI/capture, held processes, devices, OTA, release, immutable
FieldLog packages and GA gates remain untouched/pending. No dispatch, commit
or push was performed by this lane.
