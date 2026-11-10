# R101 local Git read diagnosis

The reproduced failure is a blocking OS `open()` in Git's packed-reference
snapshot path, before object decoding. No safe transient resolution was found
within the three-child budget. This is a concrete blocking stack; the underlying
kernel/filesystem/security-policy reason remains undetermined.

## Observed evidence

- Homebrew Git **2.56.0**, macOS **27.0.1 (26A434)**, local checkout
  `/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4`.
- Parent-supplied source identity: branch `t3/84a22cd4`, commit
  `6d2648e4360eeff2527d12792c2b718df512d704`. Object access did not independently
  verify that identity. The parent's push/CI statements were not rechecked.
- Baseline `git --no-pager show HEAD:work-graph.json` produced no output and
  remained running after the bounded observation. Both `GIT_NO_LAZY_FETCH=1`
  and `GIT_OPTIONAL_LOCKS=0` were set.
- All **795** samples in the one-second stack capture follow:

  ```text
  cmd_show -> cmd_log_init_finish -> setup_revisions -> handle_revision_arg
    -> get_oid_with_context_1 -> get_oid_1 -> repo_dwim_ref -> expand_ref
    -> refs_resolve_ref_unsafe -> read_ref_internal -> packed_read_raw_ref
    -> get_snapshot -> git_open_with_retry -> open -> __open
  ```

- The stack identifies the packed-ref snapshot operation. Its expected common
  repository path is `/Users/andreyyurlov/Documents/dev/mixer/.git/packed-refs`;
  the syscall's actual pathname argument was not captured. Exact-path `lstat`
  reports a regular file, mode `0644`, size **43,675**, flags **0**, no symlink
  or FIFO. Metadata success does not prove content-open success.
- Repeating the same command with system/global configuration disabled also
  produced no output and timed out. Both Trace2 logs reach `cmd_name=show`,
  with no recorded child start. Only the baseline was stack-sampled; an
  identical stack for the config-off run is not claimed.
- The observed baseline wait is not an object decompression, lazy-fetch,
  Swift compiler, or lock-acquisition stack. The experiment does not establish
  why the kernel open blocks, repository corruption, or SwiftPM's own cause.

## Bounds and cleanup

Exactly three diagnostic children were launched in separate owned process
groups: baseline **51830**, sampler **51844**, config-off **52514**. The sampler
exited **0**. Each timed-out Git group received SIGTERM and its direct child was
reaped with return code **-15**. An immediate exact-group signal-0 check returned
`ESRCH` for all three groups. The owning exec session **79390** completed **0**.
The child campaign lasted **19.281 seconds**, with no further diagnostic launch.
CPU-heavy diagnostic work was serial; the sampler observed the stalled Git.

All writes are confined to this R101 directory. Source, index, refs, config,
and locks were not changed. Other lanes, held resources and devices were not
touched. No network requests, commits or pushes were made. No physical or
native application verification was attempted.

## Safe delivery option for root

Do not keep retrying local object reads or delete locks. For a committed baseline,
root can use GitHub's revision-pinned content API without consulting the local
object database. This command is an **unexecuted option**, requiring root to
authorize that remote read; this child made no network request:

```sh
gh api -H 'Accept: application/vnd.github.raw+json' \
  'repos/snowdamiz/mixer/contents/work-graph.json?ref=6d2648e4360eeff2527d12792c2b718df512d704'
```

That retrieves only the pushed baseline. Canonical uncommitted R93 driver,
bindings, metadata, and user edits still require direct working-file delivery
with path/content hashes; the remote commit cannot substitute for those edits.
Nothing here authorizes a commit, push, fetch, merge, or permission change.

## Raw records

`launches.json` contains exact commands, environment overrides, PID/PGID,
timestamps, output paths, return codes and cleanup facts. `baseline.sample.txt`
contains the complete native stack capture and platform/tool metadata.
`*.trace2.jsonl`, `*.trace.log`, `*.stdout`, `*.stderr`,
`exact-path-metadata.json`, and `campaign.json` preserve the remaining raw
evidence. `SHA256SUMS` records hashes of the delivered files.
