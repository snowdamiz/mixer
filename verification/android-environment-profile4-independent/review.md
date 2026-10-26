# Independent Android source-pair profile4 review

Recommendation: accept the exact `mixer.android-source-pair.4` CLI/profile bytes
for bounded private host/source development. No blocking product finding was
reproduced. Root acceptance is separate. This does not admit a rendering context,
select public V2, or qualify native runtime, OTA, signed distribution, or GA.

The review verifies all 156 producer members (1,376,600 bytes), the supplied
producer seal `046f1a5a4f69dae7dafb529d55caf7fcd475a54614c40103f90be1d7fd6d39b4`,
all 111 frozen source identities and their current canonical counterparts, and
the exact native producer/review/root-selection seals. Native packet custody
covers 1,455 additional members. Native implementation behavior is accepted by
its separate review and root receipt, and is not rerun or counted as fresh here.

The independently recomputed projection is unchanged 22 SDK identities, with
23 adapter identities: only `NativeEnvironmentV2.java` changes and
`NativeEnvironmentPlatformV2.java` is added. The SDK projection is
`4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7`;
the adapter projection is
`2b001980e07e0d1c8a5139e79de6ad6ca83d8db66d386bd4f77689ab32a6325a`.
The SDK map, wire record, and 9,587-byte descriptor remain identical to profile3.
Both new environment source identities match the independently accepted native
candidate. The compiled Swift profile literal, actual generated driver profile,
copied file bytes, independently recomputed whole-tree locks, and typed copied-SDK
descriptor producer all agree.

Fresh isolated Debug and Release CLI products were built from the frozen111
sources, with the additional exact local update-verifier build dependency inputs
recorded separately. Apple Swift 6.4 and Python 3.14.8 versions, complete commands,
stdout/stderr, before/after CLI binary hashes, source maps, and cleanup are retained.
There are 118 successful command outcomes in the main corrected replay, including
expected refusals and the release assessment's expected exit2:

- Actual Debug creation and actual Release source export pass. A new authored
  variation changes both starter titles to `Independent profile4 variation`.
  Export preserves every admitted file; the four existing copied host methods
  run on this variation and pass. Earlier custom variations receive no fresh
  credit. No copied session test suite is claimed as freshly rerun here.
- Three newly authored copied-SDK host methods consume the actual exported
  descriptor, reproduce it from the typed SDK default, verify deterministic
  canonical bytes and V1/V2 separation, and reject selected noncanonical bytes.
- Fifteen independent fixtures each exercise six actual CLI entrypoints and the
  actual rendered direct-driver entrypoint: 105 refusals. They cover stale full
  profile3, a forged profile4 id retaining the old adapter hash, missing profile,
  missing Android lock and lock file, each environment source's same-size edit,
  removal, case rename and recomputed profile, plus descriptor and SDK edits.
  Changed source fixtures recompute the unauthenticated whole-tree locks. Two
  also recompute the source-profile projection. Every command refuses before a
  tool trap is reached, preserves the entire fixture inventory and seeded prior
  APK/receipt/build-input files, and creates no export output.
- Two additional actual create commands refuse edited observer/platform input
  before compiler/tool traps, destination creation, or staging residue.
- Actual positive release inspection returns `technicalEligibility: blocked`,
  `policyAssessment: pending-project-review`, and `publicationAllowed: false`.

Nine additional newly authored rendered-policy methods pass under both normal
and optimized Python. They exercise inert raw import, unrendered/stale-profile
build refusal, recomputed incomplete maps, inconsistent projections, strict
scalar shapes and bounds, duplicate keys and unsupported authority fields.
Build-input/tool/output tripwires remain unreached for rejected policy data.
The final separate official tool-distribution inspection is host-only; it does
not query devices or running processes and is not a native runtime receipt.

The first attempt is preserved in `attempt-1/`: its review oracle incorrectly
required empty directories to survive a file-only export. The corrected replay
records `Resources` as the sole omitted empty directory and compares all files.
That correction changes only independent review code. All eight first-attempt
subcommands completed, the harness failed after export, and its owned scratch
was removed. This failure is not a product finding or a hidden successful run.

The source-profile lock and rendered driver establish local compatibility under
the trusted CLI/driver assumption. They do not authenticate a release, establish
an immutable build sandbox, or resist arbitrary replacement of that trusted
program. The negative cases mutate locks and sources while retaining the exact
generated driver. Independent test-executable hashes are not exhaustive; all
owned build/test products are deleted after evidence collection. The producer's
historical Release relink and its focused regression counts remain separately
recorded and receive no new independent execution credit. The independent
`.xctest` executables were not hashed or retained; retained product hashes cover
the CLI executables and Release dSYM only.

Every owned host child was reaped and every owned temporary directory removed,
including the failed attempt. No product source, old packet, root metadata, or
Git state was modified. Native runtimes, UI, capture, devices, and running-process
inventories were not queried or started. Android API28..36 runtime/class loading, whole-library compatibility,
API28..35 rendering blockers, public V2, TalkBack/design parity, final physical
matrix, immutable published separate-repository FieldLog dogfood, signing,
OTA/store/operations/customer and accountable GA gates remain pending.
