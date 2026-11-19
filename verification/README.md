# Verification evidence

New checkouts retain CI fixtures, current held evidence, campaign reports and
compact receipts. Generated payloads from historical runs are preserved in Git
at `refs/tags/verification-archive/2026-11-10-204428` (commit
`05f4f3fe38f17140b14e4f8cf80ed37710f641a7`).
[`archive.json`](archive.json) records the immutable verification tree and the
removed counts per campaign. The tagged Git tree is the complete file manifest.
No published history was rewritten.

## Run verification from a clean checkout

1. Start with the tracked test or documented command and its pinned inputs.
   Use an exact source revision for each checkout. Create any disposable
   checkouts and dependency installs for the run inside the current worktree.
2. Create a unique run directory under `verification/local/`. Put one-off
   scripts, build outputs, proofs, raw receipts, logs, recordings, and test
   data there. Set `TMPDIR` and tool-specific output, cache, and data paths
   inside that directory for the run and its child processes.
3. Record the exact command, source and input identities, environment, result,
   limitations, cleanup, and reviewer in the applicable tracked gate or status
   record. Include the command that rebuilds any input a later step needs.
   Maintained tests and required fixtures can be tracked as source inputs.
4. Remove closed run files when finished or when removing the worktree.
   Preserve held paths and keep any worktree containing held resources until
   the hold is released. Follow the separate cleanup rules for owned processes
   and devices.

Every ongoing verification step must work when `verification/local/` starts
empty and previous worktrees are gone. If tracked results lack enough evidence
for a decision, rerun the applicable check from pinned inputs. See
[the binding policy](../mixer-product-plan.md#worktree-local-verification).

## Inspect a historical campaign

Restore archived files only to investigate a specific past run. For a shallow
or partial clone, fetch the archive tag first.

```sh
git fetch --filter=blob:none origin refs/tags/verification-archive/2026-11-10-204428:refs/tags/verification-archive/2026-11-10-204428
mkdir -p verification/local
python3 scripts/restore-verification-artifacts.py \
  verification/android-authored-toggle-input/candidate-2/coordinator-join.apk \
  --fetch-missing-from origin \
  --output verification/local/restored-toggle
```

Pass a campaign directory instead of the APK path to restore its files. The
output directory must not exist; the tool preserves paths beneath that output
directory and verifies blob hashes. The output parent must already exist.
`--fetch-missing-from origin` explicitly permits fetching only requested missing
blobs. Omit it when the archive is already available locally. The tool refuses
non-regular Git entries and unsafe destinations. Restore only the files needed
for the investigation. A full historical checkout requires about 18.5 GB.

## Check tracked verification inputs

- Add new required fixtures deliberately with `git add -f`. The staged-tree guard
  rejects generated files and files above 1 MiB unless the policy names their
  exact Git blob, size and reason. Updating an exceptional fixture requires
  updating that record; the exception does not cover future files.
- Run `python3 scripts/check-verification-artifacts.py` after staging. The same
  check runs in CI and before `scripts/verify.sh`. It includes sparse paths and
  caps verification at 1 GiB and 75,000 files.

## Local completion and later release evidence

L01–L08 in [`gates/local.json`](../gates/local.json) govern implementation-plan
completion. Include actual local app and service behavior, failures, and
substitutions in the tracked gate record.
Simulator/emulator and pinned public-checkout evidence can satisfy this milestone.
No live deployment, store approval, payment implementation or activation, registry
publication, customer uptake, or physical-phone run is required.

Keep original G01–G38 and D0–D8 qualification evidence in its existing scope.
A local pass does not establish a production, physical-device, or commercial pass.
All exact custody holds and retention limits remain active.
