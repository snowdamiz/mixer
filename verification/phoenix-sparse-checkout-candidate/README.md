# Phoenix checkout-only candidate

This is a source-only candidate for root review. The canonical workflow and Git
index were not edited, staged, committed, or pushed by this lane. Only this new
packet was written. No hosted command, dependency install, compiler, test suite,
Docker/database/native/UI command, process probe, network request, or CI mutation
was run. The temporary selected-source materializations were removed after hash
validation.

`workflow.patch` adds 19 lines of inputs to the existing `actions/checkout@v4`
step. `hosted.yml.before` is the committed workflow at
`756695fb9b0f6ec85d978202e2b3c586aa3db16f`, with SHA-256
`5b242f70831c135d8b18845b992c78e8c85797ec45565e9b9e64cdd19d2edbf9`.
`hosted.yml.candidate` is that committed workflow plus only the checkout inputs.
Removing the exact insertion reconstructs every baseline byte. All action refs,
versions, commands, timeouts, environments, tests, production release/test-helper
exclusion checks, and artifact upload inputs are preserved.

The live `.github/workflows/hosted.yml` is protected, dirty work owned by root.
It was read only to compare its SHA-256 before and after validation:
`fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57`.
Its contents and held Unit A steps were not copied into this packet. Root must
preserve those additions separately if integrating this checkout-only change.
The selectors qualify the **committed Phoenix workflow only**. Any future
integration of held Unit A steps needs its own readset review before using these
selectors with those steps.

## Readset

- All 179 tracked files under `hosted/`: the ordinary application, configuration,
  private resources, migrations, tests, support modules, format/version metadata,
  lockfile and scripts. The whole directory is required because
  `hosted/scripts/test-local.py` hashes it and includes it in `source.tar.gz`,
  excluding `_build`, `deps`, `__pycache__`, `cover` and `erl_crash.dump`.
- Both shared protocol fixtures: `signed-release-v3.json` and
  `release-v3-cases.json`. The host harness hashes/archives both; default ExUnit
  protocol/authorization/storage tests consume them.
- Browser protocol runner plus its explicit source/test/metadata arrays. This
  adds root `AGENTS.md`, `THIRD_PARTY.yml`, and
  `docs/hosted-browser-auth-protocol.md` outside the hosted directory.
- `docs/hosted-browser-session-storage.md`, explicitly hashed by the storage
  fixture runner. Its remaining source/migration inputs and all ten migration
  runner inputs are inside `hosted/`.
- `console/package.json`, `console/package-lock.json`, and exactly the workspace
  TypeScript import closure: `workspace-client.ts`, `workspace-transport.ts`, and
  `workspace-directory.ts`. The existing command compiles an explicit source file
  with command-line options. No tracked root/console `.npmrc`, local/link package,
  additional package import, or dynamic import was found in this audited closure.
  The copied Node HTTP driver is retained at its original verification path.
- `verification/hosted-customer-artifact-event/golden_event.hex` and
  `golden_hashes.txt`, read by the ordinary `customer_artifact_event_test.exs`.

`readsets.json` lists each group and the complete TypeScript import edges.
`source-read-points.json` gives committed source line pointers. Both PG relation
manifests' tracked source bindings were SHA-256 checked. Their sixteen Oban
source bindings are dependency-install outputs, supplied by the unchanged locked
`mix deps.get --check-locked`; they are recorded separately and were not fetched
or qualified here. Dependency BEAMs and `node_modules` are likewise produced by
unchanged workflow commands, not repository checkout inputs.

Historical verification attempts are deliberately excluded. The protocol/storage
runners create fresh output directories; the storage runner's optional legacy-log
move is consequently inactive on a fresh sparse checkout. The unchanged upload
globs will collect this run's generated attempts instead of copied tracked
historical attempts. No historical log or receipt is a source/test input.

## Evidence

The original analysis is pinned to `756695f`. `current-head/` repeats the same
closed readset validation at the explicitly pinned root commit
`c450ed48d14df1f2cf1140dd3f8807890a8fe9d0` (Git tree
`36e12990047d05be7c29ef63b7867a324486a896`). Its committed workflow and candidate
patch are byte-identical to the original. Only the two network collector/control
Python sources changed within the selected set; these remain source-manifest
inputs and are not invoked by the committed Phoenix workflow.

| Pinned tree | Tracked files | Tracked logical bytes | Selected files | Selected logical bytes |
| --- | ---: | ---: | ---: | ---: |
| `756695f` | 338,637 | 18,155,684,426 | 194 | 4,722,121 |
| `c450ed4` | 338,908 | 18,159,039,063 | 194 | 4,723,119 |

The selection retains 0.02601% of tracked logical bytes. All counts and sizes come
from `git ls-tree -r -l` object metadata, not a filesystem inventory. A repeated
blob counts once per tracked path in this table. Receipts also give deduplicated
blob counts/bytes: at `c450ed4`, 91,320 unique tracked blobs total 10,427,290,329
uncompressed bytes, versus 194 selected blobs totaling 4,723,119 bytes. Neither
measure is a transfer, pack, archive, allocation, or checkout-time measurement.

Validation used Git 2.56.0 and Python 3.14.8. `commands.json` records bounded
read-only Git commands, output hashes, tool versions and environment overrides.
Git lazy fetching, prompts, optional locks, and replacement objects were disabled.
Each subprocess has a 50-second timeout. Final audits completed in under three
seconds each.

- Git's canonical `sparse-checkout check-rules --no-cone --rules-file` selected
  exactly the audited file set; no isolated repository or worktree was created.
- Each selected blob was read by object ID, Git blob SHA-1 checked, materialized
  only inside this packet, and SHA-256 checked again. The temporary tree was then
  removed.
- `test-local-source-inputs.json` reproduces the original harness's clean tracked
  source-manifest and replay-tar member set. The selected tree supplies the same
  names and bytes; the harness itself was not executed.
- Fifteen omission controls confirm that each explicit external source/fixture
  selector is necessary. Ten anchoring/unrelated-file controls exclude copied
  attempts, sibling client files, other documentation and compiler artifacts.
- Exact byte reconstruction rejects any additional commands/steps, changed
  secrets/env/timeouts, moved tests, altered dependency versions, or action-ref
  changes in the candidate.

To reproduce the packet without runtime work:

```sh
python3 verification/phoenix-sparse-checkout-candidate/audit.py
python3 verification/phoenix-sparse-checkout-candidate/audit.py c450ed48d14df1f2cf1140dd3f8807890a8fe9d0
```

## Limits and review risks

This source audit establishes the current checkout readset and a minimal workflow
delta. It does not prove GitHub Actions checkout behavior, fetch reduction,
checkout speed, or successful Phoenix CI. A fresh CI run remains pending after
root's authorized integration. The existing 15-minute timeout is unchanged.

The action ref remains `actions/checkout@v4` exactly as committed; its remote
implementation was not downloaded or inspected. Current local Git rule semantics
were exercised. A runner/action compatibility failure must be handled from the
actual CI result rather than treated as passed here.

New workflow commands, TypeScript imports, metadata readers, external fixtures,
or hosted tests can expand the readset. Re-run/review the closure when they change.
Full `hosted/` retention handles new in-directory sources, but does not implicitly
admit new external paths. No native, browser, provider, production, customer or GA
gate is qualified by this packet.
