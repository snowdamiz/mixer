# Verification evidence

New checkouts retain CI fixtures, current held evidence, campaign reports and
compact receipts. Generated payloads from historical runs are preserved in Git
at `refs/tags/verification-archive/2026-11-10-204428` (commit
`05f4f3fe38f17140b14e4f8cf80ed37710f641a7`).
[`archive.json`](archive.json) records the immutable verification tree and the
removed counts per campaign. The tagged Git tree is the complete file manifest.
No published history was rewritten.

## Restore an old campaign

Fetch the archive when using a shallow or partial clone:

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
blobs; omit it when the archive is already available locally. It refuses non-regular Git entries and
unsafe destinations. Use a separate checkout of the archive tag if a historical
campaign requires symlinks or its exact historical product source:

```sh
git worktree add --detach /path/to/owned/archive-checkout \
  refs/tags/verification-archive/2026-11-10-204428
```

That full historical checkout requires about 18.5 GB. Prefer restoring only the
needed campaign. Historical drivers and report links may require the archived
inputs; retaining a report does not claim its old driver runs in the reduced
checkout. The current CI inputs and complete held plan-continuation campaign
remain tracked unchanged.

## Keep new runs small

- Store generated apps, compiler output, dependency installations and copied
  repositories in `verification/local/` or owned external scratch.
- Store new compact receipts in `verification/receipts/`. Include source revision,
  command, result and artifact hashes instead of embedding generated payloads.
- Add new required fixtures deliberately with `git add -f`. The staged-tree guard
  rejects generated files and files above 1 MiB unless the policy names their
  exact Git blob, size and reason. Updating an exceptional fixture requires
  updating that record; the exception does not cover future files.
- Run `python3 scripts/check-verification-artifacts.py` after staging. The same
  check runs in CI and before `scripts/verify.sh`. It includes sparse paths and
  caps verification at 1 GiB and 75,000 files.

The checkout reduction does not shrink shared Git history or update existing
active branches. Those branches benefit after integrating the retention commit.
Existing working files and recovery archives were not cleaned by this change.
