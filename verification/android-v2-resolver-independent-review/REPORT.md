# Android V2 resolver independent review

No actionable product finding was identified in the reviewed pure-data boundary.
This review recommends accepting this bounded Java resolver slice only. It supplies
no native operation, installed resource/font, rendering, transaction, signed
presentation, release, or GA qualification.

The final execution is `candidate-3/receipt.json` (SHA-256
`56051de78385280a3a0180196eb7a2e34557e9f7d24dcbdde5d3d82a4c5ed845`),
recorded at Git revision `b858e91147e6c13decf924977581a5a5c4b7486e` and committed
tree `dc4632b0d7499f9774436d2d07f560959e4480d4`. The separate frozen input manifest
binds actual working-tree bytes, including the then-untracked Java resolver; its
SHA-256 is `e3f2ff66a10b9e1c0d810cd16ab4fb628bc18464356f8587a1e6251082bc44d7`.
The reviewed production resolver SHA-256 is
`04237c1ffdcc777294fa70e0d7c7ecbdd4bee882ca19ce50fac795ef883ace9f`.

## Executed evidence

`ReviewProbe.java` was independently authored for this review. It serializes
reviewer-authored JSON trees and descriptors into raw bytes and calls actual
`AppearanceResolverV2.prepare`. It never feeds fabricated product Nodes to the
resolver, uses the producer's semantic expectations as an oracle, or claims
installed bytes from synthetic data. Both JVM modes compile separate exact copies
of the five production Java files and the review probe into new output directories.

- OpenJDK/Javac 25.0.4.1, `javac --release 17 -Xlint:all -Werror`, JVM default and
  `-Xint`: **23 accepted preparations, 115 explicit rejections, 6,279 assertions per
  mode**, with identical output. The receipt retains full argv, absolute cwd,
  tool versions, source manifests, stdout/stderr and class digests.
- The reviewer oracle uses different authored colors for every platform, scheme,
  role, value and state. It checks full button, field and toggle paint fields,
  authored unpremultiplied alpha, independent focus, disabled suppression, ordinary
  text paint retention, and custom canvas/alignment/gap values.
- It checks exact original text/revision/child order, inherited disabled state that
  descendants cannot clear, immediate versus nested Section contexts, existing
  source/row identities, direct-run grouping, invisible and header-only groups,
  first-visible top padding, headed/unheaded gaps, interior-only separators,
  explicit zero and fractional ties-up spacing, theme-default baseline retention,
  immutable lists/raw-array ownership, and style nonmutation.
- Adversarial raw checks cover null environment fields, malformed UTF16 before
  replacement encoding, supplementary format characters, exact UTF8 locale bounds,
  exact canonical UInt64 generations/revisions above 2^53 and at UInt64.max, raw
  packet numeric token restrictions, safe-area sums, unknown nodes/properties,
  explicit baseline/nested-list packet restrictions, nonroot navigation, required
  actions, scalar types, strings, 1,000 children and 1 MiB bytes. A separate
  4,096-node List uses five large Section groups and checks all 4,090 row placements;
  1,000 immediate groups with an invisible prefix preserve first-visible padding.
- Complete-descriptor validation rejects an invalid profile, missing font reference
  and invalid clear paint in the **unselected** iOS theme while selecting Android.
  Unknown descriptor support fields and V1-format descriptors fail admission.
- Eight source mutations in isolated copied inputs compile successfully and fail
  at their intended oracle assertion: disabled press, invisible-group padding,
  nested Section context, UInt64 double rounding, unselected-theme semantic bypass,
  raw UTF16 admission bypass, collapsed role paints, and explicit-zero spacing.
  Mutation runs use JVM default; both unchanged production variants pass.

`producer-output-audit.json` independently reopens the frozen producer command
streams, checks their hashes and exact full JSON/error equality across actual
Swift Debug/Release and JVM default/-Xint. Each has 185 cases: 170 accepted and 15
rejected. Without rerunning the large corpus, the reviewer additionally checks
4,807 accepted node records, 19,228 state records, 4,022 text metric records and all
72 profile/role pairs against independently written profile sizes/weights and
structural/state rules. All ten node kinds appear. This audit does not treat the
producer's empty mismatch files or assertion-count text as proof.

The reviewed producer is exactly `android-appearance-v2-resolution/candidate-5`:
receipt SHA-256 `4fe1e9500ed24e2e145b58a8c8e11bfc58811f282c86bd857313cb50bf51756f`,
input digest `7ab9c87aabdd15fe4c660674012234aefc183ce04ae7c7a43d112abc53613d26`.
Its own `verify_seal.py candidate-5 --with-binaries --check-live` passed 453 checks
and is captured by the independent receipt. The five reviewed production source
hashes equal that candidate's frozen inputs. The reviewer did not regenerate
Swift outputs or repeat the full producer corpus.

## Source boundary review

`prepare` has one raw packet/raw canonical descriptor admission path. The complete
descriptor is decoded and validated before platform selection. The complete
existing UiPacket decoder enforces identity coverage, unsigned tokens, actions,
closed node/property sets and packet restrictions; resolver preflight additionally
rejects every nonroot navigation. Counts/frontier/derived references are admitted
before recipe retention. Exact strings carry revision/generation values without
double conversion. Output collections are immutable copies; all plan data is
independent of the caller's input arrays.

The resolver has no default theme table, platform renderer call, resource loading,
native font installation, JNI/bootstrap change, action binding, public support
proof, signed field, or release path. The descriptor's fixed profile-family table
is admission validation; it does not substitute a Java default theme. A selected
profile and generation remain raw host data. Theme-default baseline recipes are
retained data and cannot authorize native baseline support.

Existing unsupported contexts are explicit: nested Lists and explicit first/last
baseline properties fail through the unchanged V1 packet profile; Bold Text,
increased contrast and nonroot navigation fail explicitly. Unselected-platform
data is validated. Android preference conversion, native support and required
operation acceptance remain future native-owner responsibilities.

## Reproduction and retained attempts

From `/Users/andreyyurlov/Documents/dev/mixer`:

```sh
python3 verification/android-v2-resolver-independent-review/verify_seal.py candidate-3 --with-binaries --check-live
python3 verification/android-v2-resolver-independent-review/run_review.py NEW_UNIQUE_CANDIDATE
```

The first command checks retained evidence. The second requires a fresh label and
creates new copies/build outputs; it also requires the frozen producer streams and
local producer binaries for its `--with-binaries` seal check. Local build outputs
are ignored by Git and their digests remain in receipts. After those outputs are
cleaned, omit `--with-binaries` to check retained source/log/output evidence.

`candidate-1` is a retained **review harness** failure: the wrong profile mutation
used `size64=1`, which correctly rejected with primitive numeric-bounds `number`
before `unsupportedProfile`. Changing it to the admissible but wrong `1089` tests
the intended semantic family check. `candidate-2` passed both JVM modes before
adding the independently checked 72 metric pairs and eight mutation checks.
`candidate-3` is the final unchanged-product pass. No product edits were made.

## Pending evidence

This lane did not compile DEX or run Android framework code; root owns separate
Java-to-DEX compilation. That compilation cannot demonstrate native runtime
behavior. Native resource/font capture and coverage, coherent window/preferences,
shaping/baselines/layout, drawing, scrolling/IME/focus/selection/accessibility,
failure-atomic attachment and stale-environment enforcement remain pending.

Phones remain disconnected: no device discovery, run or reconnection request was
performed. Physical iOS/Android parity, signed display/input/health, immutable
published FieldLog packages consumed from a separate repository, signing, store,
customer, operational and every specified GA gate remain pending. No tracker,
commit or push was performed by this review lane.
