# Actual failed-run review: binary export corruption

**Decision: retain the delivered execution-mount correction and correct `copy_file_out` standard-output encoding.** The new run reached and completed direct Rebar execution. It then failed closed when the host rejected the corrupted Hex export. Neither product network method ran.

Run [40746908101](https://github.com/snowdamiz/mixer/actions/runs/40746908101), job `123023004128`, attempt 1, used commit `fb7c7f20f8a308424ef4b7092d19d3d4de2c7627`, tree `509093e0fcc9f4c83583f8d0ecd61b8b3c9d83d4`. The job passed 103 collector controls in 1.022 seconds, then failed its qualification step. Finalizer and artifact upload completed successfully. Artifact `12842685657` has 2,913,212 ZIP bytes and SHA-256 `f417f539debbe00a5a07933761ec6fac5653f794039cfff73328c4d4413f7c42`, matching GitHub metadata and upload logs.

`verify_artifact_v2.py` independently checked all 127 safe ZIP members, the 126-file artifact manifest, four exact committed control sources, all 104 selected contract metadata files, seven literal helpers, all 177 frozen product files against both delivery and original commits, six Git input/output batches, and all 37 command receipts. It does not import or execute archive, collector, application, Elixir or compiler code. The artifact tree is `055c62040b51a5e3c0243b64edc0e74980beab236bd7723bcf9de5c132d0f5fa`. Full raw bytes remain in the original ZIP; selected observations are extracted as regular inert files. ZIP transport was capped at 64 MiB, expanded data at 256 MiB, and review execution at 50 seconds.

## Actual execution and first new failure

Only preparation container `4b9dbfc6e7b76a9093add70953272712d0465349cba5e244f66d5adbc593da3c` was created. Its immutable image, read-only root, exact environment, capabilities, network, memory, CPU, PID and tmpfs configuration match the delivered source. Command 22 observed `/tmp` and `/workspace` as `noexec,nosuid,nodev` tmpfs; `/workspace/tooling` was an executable `nosuid,nodev` tmpfs child. Actual sizes were 64 MiB, 960 MiB, and 64 MiB respectively, and modes were 1777/0755/0755. The observer retained selected lines and a hash of the complete mountinfo read, not the complete mountinfo bytes. No test container existed, so the test-only `/run` mount was not observed in this run.

Command 24 passed the seven exact executable hashes, Elixir 1.20.4, OTP 29.1.1, Mix, OpenSSL 3.0.22 and the selected CA bundle with 150 loaded certificates. Command 26 completed the bootstrap helper with exit 0 and complete stdout/stderr. It reported verified TLS downloads with the fixed Hex and Rebar SHA-512 values, exclusive complete cross-mount Rebar copy, close-before-hash, removal of its owned download, Hex 2.5.1, and direct `/workspace/tooling/rebar3 --version` output for Rebar 3.28.0. The preceding EACCES blocker is resolved for this observed preparation path.

The next command, 28, exported `/workspace/downloads/hex.ez` using:

```elixir
path = "/workspace/downloads/hex.ez"
true = File.stat!(path).size <= 16777216
IO.binwrite(File.read!(path))
```

It exited 0, with no timeout/overflow, complete streams, empty stderr, and output length **1,693,010**. The bootstrap record says the verified source file was **1,133,941** bytes. The collector then raised `observed bootstrap artifact digest mismatch` at the unchanged host SHA-512 check. The exported bytes were placed in `.scratch/copy.bin` and unlinked before validation, so those failed raw bytes are absent from the retained artifact; the complete-stream flag, size, and SHA-256 `9ec3f63426780b4b34d6486a64785e6e499fec9167ac7c81eaad6de7f0c195f6` are retained. This missing raw stream is an evidence-retention limitation, not a truncation or a pass.

## Discriminating evidence and correction

The exact [Elixir v1.20.4 IO source](https://raw.githubusercontent.com/elixir-lang/elixir/v1.20.4/lib/elixir/lib/io.ex), retained under `official/`, documents that `IO.binwrite` is inappropriate for Unicode standard output and can change binary bytes. Current [Erlang IO documentation](https://www.erlang.org/doc/apps/stdlib/io.html#setopts/2) explains that raw standard-output bytes require Latin-1 encoding; otherwise bytes 128–255 become UTF-8 sequences. This is consistent with the delivered command's default Unicode standard output and `LANG=C.UTF-8`.

One bounded HTTPS download of the already selected public Hex URL was retained as inert data. It matched the original exact SHA-512 and 1,133,941-byte length. Independently converting those bytes from Latin-1 to UTF-8 produced **exactly the recorded 1,693,010-byte output and SHA-256**. `transcoding-evidence.json` records this result, and the offline Python verifier recomputes it. This cryptographic equality discriminates standard-output transcoding from a changed upstream archive, a TLS failure, arbitrary Docker corruption, a truncated command, or a new Rebar/mount failure. The failed export itself was not recovered or replayed.

The minimal selected candidate is to configure only the dedicated export invocation's standard output before emitting bytes, and require both operations to succeed:

```elixir
:ok = :io.setopts(:standard_io, encoding: :latin1)
:ok = IO.binwrite(File.read!(path))
```

Keep the explicit path allowlist, per-command timeout and output cap, source-size check, host hash checks, aggregate limits, fixed images/bootstrap/source, exact container ownership and cleanup. Add a bounded all-byte-values/NUL/high-byte export test to the next selected remote preparation command, checking exact length and hash; ensure failed `setopts` and incomplete/nonzero output fail closed in pure controls. Keep the unchanged pinned Hex export as the decisive real artifact regression before dependency resolution and the original two-method workload. Retain bounded rejected bootstrap-export bytes under the existing artifact capacity so future host validation failures preserve their evidence; do not widen the artifact limit. These changes affect prepared archive and evidence exports through the same method as well as Hex/Rebar.

Retire checksum relaxation, new image selection, broader executable mounts, and unchanged retries: none addresses the demonstrated byte transformation. Kernel-wide encoding changes and a new executable prerequisite are unnecessary. This review selects a source correction for root implementation; it does not claim that a corrected Elixir invocation has run or that the full bootstrap export phase passed.

## Cleanup and remaining scope

The exact preparation CID was rechecked, stopped successfully, observed exited with PID 0/exit 0/no OOM, removed with volumes, and queried to the exact daemon absence response in command 37. Its nonzero inspect result is the expected absence result and not the primary failure. Finalization preserved the failed primary outcome and confirmed cleanup within the original aggregate deadline. Owned host scratch removal is recorded. There were no unresolved creates or cleanup errors.

Rebar host export, locked dependency resolution, prepared archive export/restore, test/PostgreSQL creation, offline compilation and both product network methods remain unrun. Preparation teardown is not product lifecycle proof. No production, provider, customer, native, process/custody, release or GA gate is accepted here.

The review wrote only this directory. It started no local Docker, Elixir, escript, compiler, PostgreSQL, guest, native, UI or capture runtime, and did not inspect held processes, private FieldLog source/logs, rerun CI, dispatch, edit canonical sources, commit, push or change status/gates. Downloads completed; no owned runtime remained. The initial offline verifier encountered a local variable-name collision only after completing the evidence assertions; its exact script and stderr are retained. A new `verify_artifact_v2.py` corrected the extraction variable and passed. This is a reviewer-script correction, not a runtime retry.
