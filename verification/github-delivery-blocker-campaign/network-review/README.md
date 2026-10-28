# Failed network run: Rebar execution permission

**First new failure: command 22 cannot execute `/workspace/tooling/rebar3 --version`; Erlang reports `:eacces`.** The amended image passes its actual preparation prerequisites. The two selected network methods did not run. Exact owned-container cleanup passed.

This independently reviewed artifact belongs to commit `cc350d3303ca71c5d57e87846f6a61304b658fa7`, tree `07f2b0e23e58dd445e2731930fc66b00ed49ec2e`, [Actions run 40740023326](https://github.com/snowdamiz/mixer/actions/runs/40740023326), job `122998787581`, artifact `12837649788`, attempt one. Reviewer model is `gpt-6-astra`, `xhigh`; this follows the prior source review and preserves all earlier failed attempts.

`artifact.zip` is 2,778,386 bytes, SHA256 `932f877ed0fc8cf8ad9457e0ba1b4888ff7bd5a58762b86975f6e887f9673231`. Its 108 safe regular members expand to 13,884,727 bytes. All CRCs, sizes and 107 manifest entries pass; canonical artifact root is `616274ea3bccd45a7b506a0b71de1016b004cbe55e9ca5f3da9fb2cfb9d394bf`. The reusable GitHub file reference was consumed in memory, within 64 MiB ZIP / 256 MiB expanded limits; no signed URL was printed or retained.

The offline verifier binds four collector/control/workflow/doc files, all 87 selected old/new metadata files, six literal helpers and all 177 product blobs to the delivered commit. Product blobs also equal frozen commit `9e860ea12074ca31bef4087ce34177a03f295dd8`. All 31 command records, environments, raw log sizes, immutable image identities, archive-transfer stdin hash and container snapshots agree. Remote Python controls passed all 84 tests in 0.568 seconds. The verifier reads data and immutable Git blobs; it does not import the product/collector or execute a runtime.

Command 20 supplies actual passing preparation evidence: Elixir 1.20.4, OTP 29.1.1, Mix 1.20.4, OpenSSL CLI/library `3.0.22 25 Aug 2026`, all seven exact source-pinned executable sizes/hashes, and explicit loading of all 150 DER roots from the selected 224,449-byte CA bundle. This closes the prior missing-OpenSSL prerequisite for this preparation instance only. No test-container repetition is claimed.

Command 22 runs the exact retained bootstrap helper. Its first failure is:

```text
** (ErlangError) Erlang error: :eacces:
  * 1st argument: invalid port name
:erlang.open_port({:spawn_executable, ~c"/workspace/tooling/rebar3"}, ...)
/workspace/collector-bootstrap.exs:86: MixerIdentityNetworkCollector.Bootstrap.run/0
```

The retained helper at line 86 directly invokes Rebar after its fixed TLS downloads, SHA512 assertions, rename/chmod, Hex installation and exact Hex version assertion. Reaching this line supports those earlier control-flow assertions. The helper aborted before emitting `bootstrap-observed.json`, and no bootstrap artifact bytes were copied out, so this review does **not** accept a complete bootstrap receipt or Rebar execution. The generic failure handler marks both command streams incomplete; the retained 434 stderr bytes are manifest-bound without treating those flags as a successful complete capture. The failure took 1.198 seconds and was neither timeout nor overflow.

The recorded Docker engine is 28.0.4. Its [matching official tmpfs source](https://raw.githubusercontent.com/moby/moby/v28.0.4/daemon/oci_linux.go) starts with `noexec,nosuid,nodev`, appends supplied options and merges them. Recorded `/workspace` options have no `exec` override. This makes the implicit `noexec` default the source-supported explanation consistent with `EACCES`, despite the preceding successful `File.chmod!(..., 0o755)`. No actual mountinfo was retained, so this remains an inference about the effective flag rather than a measured mount observation. No image, TLS or checksum guard failed.

The alternatives are decisive:

- **Bootstrap-only interpreter invocation:** retire as an incomplete correction. Exact [Elixir 1.20.4 `Mix.Rebar.rebar_args/2`](https://raw.githubusercontent.com/elixir-lang/elixir/v1.20.4/lib/mix/lib/mix/rebar.ex) invokes `MIX_REBAR3` directly on Unix; changing only the version probe leaves dependency compilation affected.
- **Enable execution for the full workspace:** broader than required; do not select by default.
- **Preferred bounded candidate:** a separate explicit executable tmpfs at `/workspace/tooling` in both preparation and test containers, with its capacity carved from the existing workspace allowance. Keep parent workspace and other temporary mounts non-executable, read-only root, nosuid/nodev, immutable images, exact Rebar path/hash, no host mounts, capabilities, networks and custody constraints. This requires a closed runtime-contract amendment and strict positive/negative mount controls; it must not edit either immutable historical packet or silently broaden an allowlist. Capture actual mount flags and Rebar path/mode/hash in the next already-required remote run, then continue the unchanged workload. Root owns selection and implementation coordination; no correction is applied here.

Cleanup has independent command evidence: the single created preparation CID `8045b6fc71361d996fe117a9caa6f159034e821664df8a71c5b7d5a701ffcfb5` was identity-checked, stopped successfully, observed exited with PID zero / exit zero / no OOM, removed with volumes, and queried to the exact daemon absence response. Finalizer preserved the failed primary outcome and confirmed cleanup within the original deadline. Host scratch removal is recorded. No PG/test container was created; dependency resolution, compilation and both selected methods remain unrun. Container teardown is not product lifecycle proof.

`verify_artifact.py` passed under its 50-second alarm. Download/read commands were bounded to at most 55 seconds. Only this new review directory was written. No local Docker, PG, Mix, native/UI/capture runtime, held process/custody probe, CI rerun, canonical edit, index/status/gates/memory write, credential change or publication occurred. The previous source review is preserved. The named unlock remains the unchanged two Linux production-DNS/TLS methods, followed by artifact acceptance; all GA and existing holds remain pending.
