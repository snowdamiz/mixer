# Immutable native package for guest UI

The native-only package at commit
`1adb25c48a8723f56ed2649712fe5e357920c53e` passed four-target static archive and
public C qualification. `2026-10-23-native-2/receipt.json` records all 33 successful
commands, exact tool identities, logs and source hashes. Its SHA-256 is
`6e6c64ce24406fccc6842b3a9437557d4f045bbeaab3cb6e2f63dd18cd0a6eaa`.

The fresh local stage is
`experimental-capability-runtime/build-verification/local/guest-ui-1adb25c-v2`.
Each target contains one `libmixer_vm_capability_experimental.a`, all three reviewed
headers, and 28 public C symbols with one definition each. The additive symbol is
`mixer_vm_capability_guest_ui_validate_v1`. Both existing headers match the earlier
`b25e3b7de2391a80d12e7fd75e60903495bec120` bytes exactly. All four targets consume
the same 90 regular committed inputs; their source-manifest SHA-256 is
`cd913dc2c067022ad627e93ae0d50ee1151b88f5c711a8d92bfd58facba8890b`.

| Target | Static archive SHA-256 | Qualification |
| --- | --- | --- |
| macOS arm64 | `4d3b6dc36ea034d5604299752d560cbbc0615002b6b5ef4e5c25bbb3cb7c6120` | C and UI consumers linked and executed |
| iOS arm64 | `08b5dd24534b085fc1def83f430e87aa875db4decae3b52819a0a56ced93079c` | C and UI consumers linked |
| iOS simulator arm64 | `5d25a53828192483a343086bb7bf7b727916f4e7e8c2338cc4f479b6cda5b9f1` | C and UI consumers linked |
| Android arm64 API 28 | `ec9f7e1e0feccc9e58c8c18635b8b0fba1965265463741f9b90440c68cbae309` | C and UI consumers linked |

The original builder probes pass 24 functions in normal Python and 24 under
`python -O`. Host execution passes 27 existing public C status/alias checks,
52 checks using mixed legacy/capability handles in one 16-slot registry, and
42 new public C guest UI checks. The latter cover valid and invalid UI signatures,
unchanged capability validation, null/range/alias preflight, an unaligned report,
all 16 mixed session slots remaining available after validation, and validation
succeeding while that registry is full. This is executable C/VM evidence; the
separate guest UI VM tests retain responsibility for their larger semantic matrix.

`audit.py` independently re-reads the exact commit inputs, staged headers, archives,
source exports, all evidence hashes, real archive symbols and consumer products.
`2026-10-23-binding-audit-1/receipt.json` records 559 binding checks and four fresh
LLVM archive-inspection commands. It also verifies the earlier qualified archive
and receipt for every target remain unchanged. Its SHA-256 is
`f20392c3f75c28e7961740713227d7efd4d5b7011fef41c9b73c525e0255621f`.

The first qualification attempt is retained in `2026-10-23-native-1`. Its host
archive build passed; its newly authored C UI consumer failed compilation because
`strcmp` required an explicit cast from the public report's `uint8_t` code field
to `const char *` under `-Werror`. The original fixture, compiler output and failed
receipt remain. Only that fixture cast changed before the successful second run;
the immutable VM revision did not change. A fresh stage was used for the second
run, without replacing the incomplete first stage or older qualified packages.

The build selects only `experimental-capability-native`, with the reviewed
guest/mailbox dependency chain and an empty mailbox leaf. Stream/cache features
are not enabled. This package differs from earlier bridge owner tests using a
locally combined stream/cache/native archive: those results do not qualify this
new archive. The bridge verifier now selects this exact package; downstream bridge
and activation execution must receive their own new receipts.

Observed tools are Rust/Cargo 1.99.0, Rust's matching LLVM 23.1.1 inspection tools,
Apple Clang 21.0.0 and Android NDK r27d Clang 18.0.4. Compiler/linker paths, binary
hashes, SDK paths, deployment targets, feature arguments and full version output
are in each target's builder receipt. The existing owned native target cache was
reused; no dependency or tool installation was performed.

No iOS/simulator/Android consumer was executed, and no device command was run.
Physical-device, signing, immutable publication/FieldLog consumption, independent
review, store/customer/operational and GA gates remain pending. This is local
frozen-source package qualification, with no bit-for-bit reproducibility or release
authorization claim.

```sh
python3 experimental-capability-runtime/build-verification/run.py \
  --output /absolute/fresh/evidence \
  --artifacts /absolute/fresh/stage \
  --cache /absolute/owned/native-cache \
  --rustc /absolute/path/to/rustc \
  --ndk /absolute/installed/ndk

python3 verification/guest-ui-native-package/audit.py \
  --qualification verification/guest-ui-native-package/2026-10-23-native-2 \
  --stage experimental-capability-runtime/build-verification/local/guest-ui-1adb25c-v2 \
  --output /absolute/fresh/audit-evidence
```
