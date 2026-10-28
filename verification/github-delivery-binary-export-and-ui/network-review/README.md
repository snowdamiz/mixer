# Actual binary-export correction review

The byte-transparent export correction passed in actual CI. Run [40753111388](https://github.com/snowdamiz/mixer/actions/runs/40753111388), attempt 1, job `123044764614`, used delivered commit `56ff14c925168284761c5aca4f0bd4129cf3c995` and tree `75989099938ed5256c4144cbc9e62979ee323183`. The run failed after successful offline compilation because the strict dependency manifest included a new Rebar build metadata file. Neither product network method ran.

The retained ZIP is artifact `12845285898`: 11,377,187 bytes, SHA256 `2f0e7761685d64924bc743c3b8ad73d944ed726ecc0e4b14228010a840552be9`. The connected tools supplied run/job/artifact metadata and the complete job log; the signed transport URL was neither printed nor persisted. Transport was capped at 64 MiB and 50 seconds. The offline verifier bounded expanded files at 256 MiB and execution at 50 seconds. It read archives as inert data and never imported or executed collector, product, dependency, compiler, container or archive code.

`verify_artifact_v2.py` passed the independent joins for all 350 safe ZIP members and 349 manifest files, four exact committed controls, 104 selected metadata files, seven literal helpers, 177 unchanged frozen product files, six Git input/output batches, and all 107 command receipts. The artifact tree digest is `344764d6a8b5a50cfa789fcc19934af2c463183a948f6d539a2b4d6524698811`. Every actual stdout/stderr stream is retained and matches its recorded length; binary streams also match their command hashes. The 111 remote collector controls passed in 1.021 seconds.

## What actually advanced

Preparation and test mounts satisfied the selected exact tmpfs flags, sizes, modes and child hierarchy. Both environments passed the seven tool hashes, Elixir 1.20.4, OTP 29.1.1, Mix, OpenSSL and the exact selected CA bundle with 150 loaded roots. Image identity, configuration, capability, environment and resource checks remained unchanged.

The bootstrap completed verified TLS downloads, exclusive cross-mount Rebar copy, final hash verification and direct Rebar execution. Export command 28 retained the exact 1,133,941-byte Hex artifact, SHA256 `05ec9f68a512381b0053cf7e92eebea201709b7754dc288ea9b2663f88314730`. Export command 30 retained the exact 823,379-byte Rebar artifact, SHA256 `4df37f2f7570e0b5af15b5dcbad6b7a864202575d94e1d8663166c7643ee3a09`. Both match the unchanged pinned SHA512 values, and both contain all 256 byte values. Their complete zero-exit command receipts join the retained public bytes and accepted bootstrap copies. This is actual evidence that the selected export correction resolves the prior Unicode corruption.

Locked dependency preparation succeeded. The prepared tar contains 1,232 regular files: 177 source, 914 dependency, 134 tooling and seven helper files. Its 15,196,160 bytes have SHA256 `cc847fa424bc4668ba4638edafaebfd0e956b45d9547fc18d85e9ec54b26cfa5`. Every member matches the prepared manifest and the exact restore transfer. The networked preparation container was removed before test-container creation. The test namespace had only loopback, no default route and the exact selected capabilities. PostgreSQL 16.15 shared that namespace, used UID 999 and exposed only the expected disposable databases. Two initial readiness responses were followed by success within the existing bound.

Commands 85 (`mix deps.compile`) and 87 (`mix compile --warnings-as-errors`) exited zero with complete streams. Dependency compiler warnings remain in command 85 stderr. Product compilation had empty stderr.

## First causal failure

Command 89 successfully returned the postcompile manifest. Its sole difference from the prepared/restored manifest was this added dependency-tree entry:

```
hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl/source.dag
bytes: 895
sha256: 71360df95b056715d6215b91ba581e4dd91d850f4894c13720f142075a53d685
```

No existing dependency entry changed or disappeared. Frozen product, tooling and helper manifests remained identical. The helper recursively includes every regular file below `hosted/deps`; `validate_source_unchanged` compares the complete manifests. Therefore the new file causes the observed `source/dependency/tool mutation` rejection immediately after command 89, before the test authorization flag, observer or either product method is invoked. The path and compile-phase timing support classifying this as Rebar-generated compiler metadata; the new file's raw bytes are not retained, so its contents and internal format have not been independently validated.

Preserve this failed baseline. The next bounded correction should distinguish expected compiler output from immutable dependency inputs while continuing to reject modifications/deletions of original inputs and unknown additions. A blanket `_build` ignore or checksum relaxation is not supported by this evidence. No correction is implemented or accepted by this review, and no rerun is dispatched.

## Cleanup and limits

All three exact created IDs have successful stop/remove commands, terminal exit 0, PID 0, no OOM, and the exact daemon absence response: preparation at command 47, PostgreSQL at 98 and test at 107. Finalization preserves the failed primary outcome and verifies cleanup within the original deadline. Owned host scratch was removed. Container teardown is not application lifecycle proof.

Compiled-module collection, test authorization, both production DNS/TLS methods, semantic receipts, the ten-migration check and post-test source/key checks remain unrun. Full mountinfo bytes are not retained; the selected lines and whole-read hash are. All native, process/custody, provider, customer, release and GA holds remain. This review accepts only the observed bounded preparation/compilation progress, not the complete network lane or a GA gate.

Only this review directory was written. No canonical edit, commit, push, dispatch, rerun, local Docker/Elixir/compiler/PostgreSQL/native/UI/capture runtime, held-process probe or private FieldLog access occurred. The first verifier used bare capability names where Docker records `CAP_` prefixes; its failed assertion and original script are preserved. The corrected sibling normalizes that documented representation and passes. The generated result retained an old literal command label; `verification-result-amendment.json` records the actual passing invocation and its source hash without replacing the original evidence.
