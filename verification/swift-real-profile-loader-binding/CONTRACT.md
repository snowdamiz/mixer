# Selected macOS retained-source loader/carrier

Root selected this scope in `root-selection.json`; `selection.json` records the lane boundary. `contract-proposal.md` and `provenance_schema_proposal.md` are historical proposals; this document closes the actual implemented schema. The binding product plan remains the completion scope.

## Ownership and authority

The only production ingress is private `load_selected_retained_profile_v1(source: File, build: File, session: File, budget: SwiftValidationBudget, cancellation: &Cancellation) -> LoaderOutcomeV1`. It consumes safe File owners, opens one producer executable File, and returns every retained/opened File on success or failure. No raw descriptor adoption or hidden close-success claim exists. Outcome/file/error types are visible only to the parent private module. The carrier is non-Clone with private fields; its only parent-visible inspectors borrow source bytes from `&self` and copy the captured actual validation budget. There is no raw proof extraction, deserializer or alternate mint path.

The loader records all five actual validation limits, invokes the original complete validator, preserves original `SwiftValidationFailure` inline, and compares the whole returned proof source with the loaded source while both live. It records validator requested-storage observations on both success and failure before any equality or later refusal. Returned Files and original typed I/O/validation errors remain owned independently of the selected carrier. No runtime admission, AdoptedProof sidecar, guard, exporter, result codec route or ledger refund is added.

Provenance is trusted-launcher/quiescent-local correlation only. The trusted runner hashes complete source144+host11 and its actual own bytes before compilation, exact compiler executable/version, Python executable/version and selected SDK declarations; records exact compiler argv/environment; embeds section commitments into the resulting binary; checks the immutable source/tool closure afterward; then creates session preimages from actual source metadata/bytes, process argv/environment/cwd and OS-random nonce before launch. The child hashes actual retained preimages and the actual executable file named by Darwin. It never grants authority to an arbitrary API digest string or boolean.

A colluding/compromised launcher/compiler, concurrent mutation, replacing the executable pathname or mapped image, hostile same-user filesystem changes, signed toolchain/package authentication, replay policy and product release authorization are outside this scope. Hash equality and a nonce do not create those boundaries. The nonce is fresh because the trusted runner obtains it from OS randomness; the loader checks its correlation rather than claiming independent freshness authentication.

## Common byte encodings and bounds

All header words are logical u64 little-endian. Digests are exact32 SHA256 bytes. No Rust object image or Debug text is parsed.

A counted list is count:u64 followed by count repetitions of length:u64 and exact bytes, with no padding or tail. Count<=64; argv requires count>=1. Each string is0..4095 bytes, contains no NUL, and the whole encoded list is<=16384 bytes. Empty argv elements and non-UTF8 bytes are preserved. Environment elements are exact `key=value` bytes, split at their first equals; keys are nonempty and unique, sorted lexicographically by raw key bytes. Values may contain further equals signs and non-UTF8 bytes. Environment count may be0. No lossy conversion exists.

Runtime observations inspect the complete process environment, excluding exactly `MIXER_LOADER_EXPECTED_SESSION_SHA256` and `MIXER_LOADER_EXPECTED_NONCE_HEX`. Each excluded key must occur exactly once; its value must be exactly64 lowercase hexadecimal bytes and is separately checked against the actual session digest/nonce. Duplicate keys, unknown missing identity values, too-long/nonterminated strings, null OS pointers, overflow and encoding/extent anomalies refuse. At most64 total OS environment entries, including these two, are scanned. The raw environment copy and its encoded form each have a16384-byte caller buffer.

Compile environment excludes exactly these five injection variables: `MIXER_LOADER_MANIFEST_SHA256`, `MIXER_LOADER_COMMAND_SHA256`, `MIXER_LOADER_COMPILE_ENV_SHA256`, `MIXER_LOADER_COMPILER_SHA256`, `MIXER_LOADER_COMPILER_VERSION_SHA256`. Their actual values are injected through Rust `option_env!`, must be exact64 lowercase hex, and are separately matched to the corresponding retained build header claims. No identity variable participates in its own preimage. The actual selected compile environment currently contains only PATH, TMPDIR and CARGO_MANIFEST_DIR; the full compiler argv contains all feature/target/optimization/overflow/panic/output flags. The manifest includes actual runner/prepare/selection identities separately from144 distribution and11 host members.

Cwd and executable-path observations use separate4096-byte caller buffers. Supported values are absolute, nonempty, contain no NUL within the returned counted value, and have length<=4095. Raw path bytes are passed to File::open through OsStr::from_bytes. APFS rejects creation of the two invalid-UTF8 pathname test cases with EILSEQ92 before loader execution; those cases are explicitly unrun. Actual invalid-UTF8 environment bytes and pinned raw C-string scanning are tested.

## MIXLBD01

Fixed512-byte header plus exactly four nonempty sections; total<=131072. No trailing bytes.

| Bytes | Content |
| --- | --- |
| 0..8 | MIXLBD01 |
| 8..32 | version1, header512, actual total length |
| 32..48 | distribution144, host11 |
| 48..80 | four section lengths |
| 80..88 | actual output length1..67108864 |
| 88..152 | aarch64-apple-darwin plus zero padding |
| 152..280 | SHA256 of manifest, compiler argv, compile environment, compiler version output |
| 280..312 | compiler executable SHA256 |
| 312..344 | actual compiled output SHA256 |
| 344..512 | zero |

Sections are complete source/host/orchestration/tool manifest<=65536; counted compiler argv<=16384; counted selected compile environment<=16384; exact compiler version output<=16384. All four section digests are recomputed. Manifest/argv/environment/compiler/version claims must equal independently embedded compile-time commitments. Actual current executable bytes must match output extent/digest. The output digest is deliberately computed after compiler completion and is not embedded into that same output, avoiding a cycle. The manifest is a trusted-runner canonical JSON preimage; the loader binds its exact bytes to the compiled commitment rather than claiming to authenticate arbitrary manifest JSON.

## MIXLSE01

Fixed512-byte header plus exactly four nonempty sections; total<=65536. No trailing bytes.

| Bytes | Content |
| --- | --- |
| 0..8 | MIXLSE01 |
| 8..32 | version1, header512, actual total length |
| 32..40 | actual source byte extent |
| 40..72 | four section lengths |
| 72..112 | actual source_bytes, metadata_bytes, scratch_bytes, work_credits, deadline_ms |
| 112..144 | launcher nonce32 |
| 144..176 | exact original source SHA256 |
| 176..208 | complete retained MIXLBD01 SHA256 |
| 208..240 | actual producer executable SHA256 |
| 240..368 | SHA256 of the four sections |
| 368..512 | zero |

Sections are exactly64-byte source identity; counted actual argv<=16384; counted complete actual environment minus the two checked identity keys<=16384; exact absolute raw cwd1..4095 bytes. Source role is fixed to the sole original-input File by this version/entry point. Identity is dev, inode, extent, mode as four u64s, then mtime seconds/nanoseconds and ctime seconds/nanoseconds as four signed64 two's-complement little-endian values. The actual complete budget must equal the session's five fields; unsupported widening refuses before source read/allocation, while admitted original validation failures retain their original typed payload.

## I/O, cleanup and unsafe conditions

All four Files must be regular. Every pair is checked for dev/inode alias, including clones/hardlinks and the current executable. Each admitted read requires offset0, exact observed extent<=its selected cap, exact-capacity try_reserve_exact, complete bounded reads and explicit EOF. Source<=actual source limit<=67108864; executable<=67108864; build<=131072; session<=65536. Each4096-byte block/one-byte EOF request permits at most32 explicit Read calls including Interrupted. Completion on32 succeeds; incomplete32 refuses; no33rd call. Overreport, zero-before-completion, extra bytes and original OS I/O error retain exact role/offset/attempt coordinates.

Dev/inode/extent/mode/mtime/ctime observations are checked pre/post read and again after validation. The executable byte allocation is destroyed before source/proof allocations coexist. Refusal destroys only temporary byte/proof storage; it returns actual File owners. File::drop, process exit, descriptor reuse and host directory removal are never called proven close success. The trusted runner terminally waits every child, removes only its owned scratch names and separately records cleanup. External close/name uncertainty is not converted into a Rust ledger zero.

CommonCrypto CC_SHA256 is the platform cryptographic foundation; its official ABI has u32 input length and32 writable digest bytes. The input slice remains live and disjoint from output for the synchronous call. No custom primitive is implemented. Darwin crt_externs supplies valid process-lifetime argc/argv/environ slots; bounded C-string scanning requires those pointers to remain valid for each returned borrow, no concurrent mutation and no callback/reentry. _NSGetExecutablePath/getcwd write into the declared4096-byte buffers; API failures preserve typed refusal/OS error. Limits bound source-authored calls and named storage, not kernel/library internals or a blocking syscall's elapsed time. The SDK declaration identities are in receipt.json and platform dependencies are recorded by root in THIRD_PARTY.yml.

Full shared runtime adoption/cleanup and sidecar accounting, immutable snapshot export, constructor/cleanup/result semantics, code applicability, real context/custody/replay, canonical integration, native/simulator/emulator/device qualification, separate-repository FieldLog with published packages, OTA/store/customer/operations and GA remain pending.
