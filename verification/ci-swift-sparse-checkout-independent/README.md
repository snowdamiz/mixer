# Independent Swift sparse-checkout audit

Accepted for the bounded source/offline checkout slice. No missing Swift job
repository input or additional workflow change was found. This is not a remote
CI, product-runtime, OTA, native-device, operational or GA acceptance receipt.

Reviewed candidate `.github/workflows/verify.yml` SHA-256:
`80d09b839d91a8be0a50bb19fc84b63b421193af26e1b2a95aa668f98b7a4680`.
The canonical source is `114a2632fd58076574bd5b2444c511861c3b30d4`, tree
`8666138ed9c87272a35759df84ce968db690abc8`; its workflow SHA-256 is
`2c701a47ef42129547048623eff7db7db721fb2fe39d3dabf4bb7bb6d1f939a0`.

## Independent observations

`audit.py` does not import or execute either producer checker. Its Git
subprocess allowlist contains only read commands. It checked the workflow byte
delta using an independent sequence comparison: exactly 26 inserted lines in
`swift.steps[0].with`, immediately after the existing `fetch-depth: 0`. Commands,
artifacts, toolchain pins, timeouts, triggers and all other jobs are byte-equal to
the canonical workflow. Non-cone mode is explicitly false for the cone-mode
input, and the actual workflow patterns equal the producer's observed patterns.
`workflow.diff` retains the exact delta.

Read-only `git sparse-checkout check-rules` over the canonical full path roster
selected exactly 5,054 blobs / 208,685,831 bytes. An independently declared input
predicate and the producer's final materialized inventory agree on every path,
mode, Git object ID and size. Every one of 3,353 non-verification paths remains;
the selected set has no symlinks or submodules. The full canonical tree contains
330,288 files / 17,638,540,012 bytes. This audit did not materialize a checkout.

The policy script's actual `os.walk` exclusions and eleven manifest basenames
were read through Python AST without executing the script. All 645 canonical
manifest paths survive, including the complete effective policy walk. Read-only
Git controls additionally covered each future manifest basename in a hidden,
deeply nested verification directory, ordinary excluded verification files, and
a future non-verification source path. No manifest inspection scope is removed.

Canonical Git blob contents, obtained through one `git cat-file --batch`, were
independently checked for 1,080 distinct sealed/manifest/corpus/external inputs:
270 producer framing members, 624 review framing members, the 86-member envelope
packet, all 90 guest corpus cases, the seal/sidecar/manifest files and four exact
external JSON fixtures. The two sealed documents outside the framing directories
are under `docs/` and remain included. The envelope's entire tracked inventory,
total bytes and manifest tree pin match its runner; source includes and relative
oracle inputs stay inside that complete packet. No historical runner was run.

## Every existing Swift command's input closure

| Step / command group | Source review and preserved transitive inputs |
| --- | --- |
| Apple toolchain verifier | Complete `scripts/ci`; its external runner installation inputs and all toolchain arguments are unchanged. |
| CI selection unit discovery | All five modules and imported runners under `scripts/ci`. Framing controls consume the two frozen packets; envelope controls consume the exact full pack; dependency controls copy the policy script plus gate/work-graph/milestone JSON. Android binding controls use synthetic dependency/native inputs and reject invalid native receipts before staging the positive sibling-job source closure. |
| Policy and acceptance integrity | `scripts/check-policy.py`, every effective manifest, `gates/ga.json`, `work-graph.json`, `dogfood/receipts/milestones.json`. Excluded-directory behavior remains identical. |
| Standalone framing runner | Both complete frozen directories, seal/sidecars, all sealed members including two `docs/` files, four selected Rust source files and 17 historical stream/sidecar pairs. The runtime test's historical-directory environment points at its output snapshot. |
| Standalone envelope runner | Full exact `verification/swift-envelope-ci-pack`, including manifest, inventories, library/producer/independent source, relative Rust modules/includes, raw oracles, historical input and all API probes. Other root-review paths in the runner are evidence-reference strings, not file reads. |
| Schema generator and capability Swift tests | Complete `capabilities/`, `sdk/`, `contracts/`; schema/generated inputs, local `../sdk` package, Swift targets/tests and C NativeIO target. |
| Debug/release transport corpus commands | Complete guest contract packet, pinned `cases.json`, all 90 referenced raw files, frozen transport contract and public Swift probe/package closure. |
| Capability TSAN filter | Same complete capability/SDK targets, resources and native C inputs; its filter, sanitizer and scratch path are unchanged. |
| SDK public/development package check; root Swift tests | Root and SDK manifests/targets plus complete SDK tests. The V1 appearance fixture, V2 appearance fixture and fifty-case design corpus are the three individually retained external JSON paths. |
| Updates and CLI Swift tests; CLI Python discovery | Updates' pinned Swift Crypto manifest/resolution, all updates/CLI resources and fixtures, local SDK/updates dependencies. Python compatibility/staging/appearance modules retain the shared fixture helper, Android build driver, committed compatibility profile and its SDK/adapter map inputs; the external created-descriptor JSON is retained exactly. |
| Android engine host Swift tests | Complete engine targets/tests, local SDK dependency and all SDK source. This command remains host testing; this audit did not run it. |
| Runtime identity vector checks, Swift tests and Python discovery | Complete `runtime-identity`, updates dependency, activation runtime-identity fixture, contract/schema/VM header inputs, imported capture/embed modules, and synthesized consumer source templates. Their input snapshots are created during the existing commands. |
| VM builder unit discovery, canonical VM archive and runtime/activation/review Swift tests | Runtime builder/test source; committed `vm` and session contract archived at CI revision; matching working wrapper header; runtime C/Swift targets; activation's runtime/updates/identity dependencies and fixtures; complete `verification/runtime-review` test package with local `../../runtime` dependency. |
| CLI create/test/iOS build generated consumer | CLI resources and all `sdk` snapshot inputs, generated application templates and iOS project builder. The default SDK path is derived from CLI source location. SDK directory inventory is unchanged because all non-verification paths, including nested SDK verification material, remain included. Generated application paths and runner tools are created/selected by the unchanged commands. |
| Artifact upload steps | Read generated files under the unchanged runner-temp paths; they introduce no additional repository fixture reads. |

The independently re-read canonical VM archive equals the producer's archived
byte digest; its file roster and header match the complete canonical VM source
and retained wrapper. Full Git history remains selected by unchanged
`fetch-depth: 0`. All nine retained historical pin reads were re-read and their
hashes match the producer receipt; the pin's three additional VM source blobs
are also available. This historical positive builder belongs to the unchanged
`swift-capability-native` sibling, not the edited Swift job.

## Checker and custody review

The producer's independent `wanted` predicate is an inclusive superset of every
non-verification input and all manifest basenames. Its tiny/canonical negative
controls detect broad recursive directory inclusion and dropped manifests. The
final collector parses seal/pack/corpus membership, verifies actual sparse path
and blob equality, checks sealed contents and corpus bytes, and reads the archive
and historical pin without compiling. Its optional isolated Git writes are
recorded as producer-only past work; this audit did not replay them. The final
collector matches the retained collector hash/source. Earlier failed producer
receipts remain present; only `materialization-2` supplies passing materialization
evidence. All final producer commands passed and recorded reaped children/gone
owned groups; the final owned scratch removal is recorded.

This audit hashed the complete frozen 160-file / 6,414,704-byte producer packet
before and after; its aggregate inventory SHA-256 remained
`f9f3aa4d0371d8a8bd21bcc6ad5f6681e13acbf83ad6a5f09f7b1e6a02b03978`.
Reviewed source hashes and HEAD also remained unchanged. All reviewed source
files except the explicitly changed workflow match canonical Git blob IDs.
`reviewed-source-inputs.json` records the exact read set and its SHA-256 digest.

Run recorded by `receipt.json`:

```sh
python3 -B verification/ci-swift-sparse-checkout-independent/audit.py
```

Python 3.14.8 and Git 2.56.0 on macOS arm64; 22 read-only Git subprocesses.
Commands, input/output hashes, exact revision/tree, candidate/source/evidence
hashes and limits are retained in the receipt. The final run passed after adding
the canonical source equality guard; no audit run failed. No compiler, product
command, network, native runtime, UI/capture, global process inventory, Git
mutation or checkout materialization was used. Writes were confined to this
independent directory. Remote GitHub checkout behavior/timing and all existing
CI job commands remain pending remote CI. The phone/native runtime pause and all
GA acceptance boundaries remain in effect.
