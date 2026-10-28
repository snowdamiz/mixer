# Independent CI fixture-cleanup candidate review

The test correction matches the frozen diagnosis and ownership requirements.
One P2 evidence-validator finding requires a narrow runner correction before
execution. No additional product code, product tests or process audits are
requested. Preserve this unexecuted prepared-1 packet and issue a separately
frozen prepared-2 correction.

Reviewed plan:
a5f9d6393385ab28ba3579ba4f0fd6e3a900099cc341ed8c53263b467940abcf.
Reviewed freeze:
34ab3c96238e0e8100331d42109d834d313b39bec9b86582e7ffd78080f97019.
Preaccess seal:
aa319fb7181e5fafb75c0433e593d557d059757b6c51452f6b3a7ca82945ffd5.

## R01: actual phase artifact membership is not checked

The runner's finalization loop reads only names from phase.required_artifacts
into artifact_observations. validate_terminal_artifacts then checks this
constructed map has exactly eight keys. That does not check the actual output
directory: an extra openssl-05.json or any other unexpected file is ignored and
cannot affect the eight-key map. The fourteen reported offline controls include
an extra aggregate-map artifact, which does not exercise this directory-to-map
boundary. This is a source-derived validator counterexample, not an executed
runtime fault or product security defect.

Before reading the required artifacts, require actual corrected phase membership
to equal the eight required artifact names plus command.json and stdout.txt:
exactly ten ordinary files. Reject unexpected files, directories and symlinks;
reject missing files. Perform this after owned child/group cleanup is confirmed
and before terminal acceptance. Preserve the complete directory, extra names and
outputs on failure. Add bounded pure-Python filesystem controls for this boundary
in the separately frozen runner correction. Do not add product test methods or
erase unexpected files to make membership pass.

## Source, selection and runner review

The beforeimage exactly equals fd92138's delivered test source. The only patch
gives ExUnit the fixture owner as a temporary child, explicit start_fixture MFA,
unique name id and infinite shutdown, after its worker supervisor. Reverse
teardown drains the owner first. on_exit now only asserts captured owner/worker
PIDs, exact registrations, ETS table destruction and pointer absence; it contains
no racing stop, catch, sleep, retry or erase. K07g adds stopped-owner/no-replacement
assertions, preserving its suspended-controller barrier and explicit stop. All
other methods remain unchanged.

The complete 29-method module compiles; the bootstrap includes the six exact CI
failure names plus K07g and verifies their unique registration/tag equality.
Expected terminal counts are total 29, executed 7, excluded 22, skipped 0,
failures 0. Exclusions are not passes or full-suite qualification. Existing
run-local evidence behavior is preserved. The product closure is exactly the
accepted prepared-3 eighteen files; active canonical inflight-supervisor edits
are excluded. Three unchanged support modules compile without starting the
unselected DNS fixture.

The reused runner retains reviewed exact child/group ownership, scratch
preservation on cleanup uncertainty, exclusive output directory, bounded
40/46/52/55-second stages, posthashes and finite signal cutoff. Aside from R01,
the strict fixed artifact schemas and OpenSSL record validation check required
fields/types, counts, exact argv, scratch-local ephemeral fixture paths, output
byte caps, success and reaping. The wrapper has no separate process group, so
outer group cleanup covers interruption; it locally kills/waits for its exact
OpenSSL child on deadline/output failure. Each command has a five-second work
bound and 8192-byte output cap. The four commands are a version probe and the
existing fixture's three certificate commands. Argument templates write private
keys only into the fixture directory, removed in its existing after block.
The bootstrap additionally checks scratch-local fixture directories absent.

Fresh independent custody checks pass 221 packet members, 220 prepared pins,
25 canonical pins and 980 tool pins. Dependencies/product sources match accepted
prepared-3 bytes. The top-level offline-validator-controls.json is outside the
producer freeze; its plan-bound hash is retained in audit.json. Its one accepted
and fourteen rejected controls were read, not replayed.

No compiler, formatter, OpenSSL, TLS, test/runtime, producer Python or process
inventory ran in this review. After R01 is corrected and reviewed, root may
release one exact targeted host run. Fresh terminal evidence and later full
Phoenix CI remain required. The remote six-failure receipt remains historical
failure evidence. Native/UI/capture/devices, production operation and GA remain
outside this slice.
