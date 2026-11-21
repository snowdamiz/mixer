# Retain a private source map for a local release

Use the local operator command to deposit or retrieve the exact
`.source-map.json` bytes of a committed v3 publication. The command uses the
configured local release target and the current authorization of a human
project owner with a verified `mixer.release.publish` bearer. It checks the
publication sequence, manifest digest, signed assignment, and signed map digest.

## Prepare the disposable local database

Use the existing [local signed release setup](replay-configured-release.md)
and apply `priv/local_source_map_retention/20261120000022_add_local_source_map_retention.exs`
as the local migration owner after release migrations 000001, 000002 and
000010. This migration is outside the default migration path. Run the
following in the disposable database as its administrator, with the psql
variable `writer` set to the existing local writer login.

```sql
GRANT SELECT, INSERT ON public.mixer_release_source_maps TO :"writer";
GRANT EXECUTE ON FUNCTION
  public.mixer_release_source_map_allowed(text,text,text,text,text,text,text,numeric,text)
TO :"writer";
ALTER ROLE :"writer" IN DATABASE :"DBNAME" SET log_parameter_max_length = 0;
ALTER ROLE :"writer" IN DATABASE :"DBNAME" SET log_parameter_max_length_on_error = 0;
ALTER ROLE :"writer" IN DATABASE :"DBNAME" SET log_error_verbosity = 'terse';
```

The command opens a fresh writer connection and checks these settings before
passing map bytes to PostgreSQL. It starts the configured identity verifier and
writer pool without an HTTP listener. The private map has no HTTP route.

## Retain and read

1. Publish with the existing signed release flow. Use the same local release
   API configuration for the operator command, including the configured
   identity verifier and `MIXER_LOCAL_RELEASE_WRITER_ENABLED=true`.
2. Supply your bearer through `MIXER_RELEASE_TOKEN`. From `hosted/` run the
   command with `MIXER_LOCAL_SOURCE_MAP_RETENTION_ENABLED=true` for each
   operation. Set `sequence` and `manifest_sha256` to the committed publication
   values. Set `retain_until` to the absolute Unix timestamp in seconds.

   ```sh
   MIXER_LOCAL_SOURCE_MAP_RETENTION_ENABLED=true \
     mix run --no-start scripts/private-source-map.exs \
     retain "$sequence" "$manifest_sha256" "$input_file" "$retain_until"
   ```

   Use the untouched regular file of 1 byte to 4 MiB. The command prints the
   deadline. An exact retry returns the same deadline. A different deadline
   conflicts while the first retention is live.

3. To retrieve the map, use a trusted `python3` on your PATH and choose a new
   file by absolute path in an ACL-free directory owned by your effective user
   with mode 0700. Use the actual path, including `/private/tmp` on macOS when
   applicable. The command refuses symlinks and checks each ancestor for ACLs
   and ownership by your effective user or root. Group- or world-writable
   ancestors must have the sticky bit set. Run the command under a user ID you
   control, in a namespace controlled by trusted administrators.

   Use local APFS with ownership enabled on 64-bit macOS, or a Linux ext2/3/4,
   tmpfs, XFS or Btrfs filesystem with POSIX ACL inspection available on 64-bit
   x86 or Arm Linux. The complete path must use supported filesystems. The
   command checks ownership, mode, and ACLs on a private staging directory and
   an opened 0600 file before writing. After the write completes, the command
   authorizes the helper to publish with an atomic rename that refuses an
   existing destination. A successful export prints the deadline.

   The foreground Python command owns the publication process. Mix performs
   the identity and signed release checks and sends the authorized response
   through an inherited anonymous Unix socket. The header carries the stored
   retention timestamp, the effective read cutoff, and the size. The cutoff is
   the earliest of retention, the latest eligible owner-grant expiry, and any
   bearer, credential, or credential-family expiry. The timestamp printed on
   successful export is the stored retention timestamp.

   Python checks the header before requesting the body. On the Unix readiness
   backend, Mix checks the cutoff before each nonblocking send, including after
   a writable notification for a partial send. Python checks the cutoff during
   receipt and before the final rename. Map bytes stay off standard output
   and standard error.

   During authorization, Ctrl-C closes the private transfer. The foreground
   waits for a pending launch to return the Mix PID. It stops Mix if necessary
   and checks both direct-child reap and process-group absence before accepting
   a response or reporting `authorization_interrupted` with status 130. When
   the foreground cannot confirm closure, it reports
   `authorization_indeterminate` with status 2, the Mix PID and process group,
   and whether Mix was reaped. Preserve that report and reconcile the named
   process group before retrying. Processes that leave the isolated group and
   forced termination of the foreground are outside this custody check.

   The first response byte has a 30-second limit after Mix launch returns.
   Once the authorized transfer begins, Mix and Python each enforce a
   five-second monotonic window, shortened at setup to the wall-clock time
   remaining until the effective cutoff. Each subsequent check also reads
   wall time. Use an accurate host clock. A backward clock step before a
   process samples the cutoff can affect its initial monotonic cap. Clock
   changes between samples and time spent in host sleep follow the clocks
   exposed by the operating system and each runtime.

   A process can be descheduled between a clock check and a system call.
   The cutoff governs the checks before each send and before rename
   authorization. The kernel may deliver previously buffered bytes after the
   cutoff, and an authorized rename may finish afterward.

   An ordinary output refusal prints `output_unavailable`. On an uncertain
   publication result, the command prints `output_indeterminate` with the
   publisher PID and returns status 2 after reaping it. The foreground command
   stays active while an outstanding launch or filesystem operation resolves.
   Preserve the destination and any `.mixer-source-map-*` staging directory
   until publication is accounted for.

   ```sh
   MIXER_LOCAL_SOURCE_MAP_RETENTION_ENABLED=true \
     python3 -I -S -B priv/local_source_map_retention/private_output.py \
     read "$sequence" "$manifest_sha256" "$output_file"
   ```

   A read started after the stored retention expires reports `not_found`
   and exits with status 1.
   The publication cannot be retained again.

## Clear expired bytes in the disposable database

As the local database administrator, run the purge script. It clears up to
100 expired payloads per run and keeps each publication key and deadline.
Access expires independently of the purge. The transaction allows up to one
second to acquire each lock and five seconds for the purge statement. A
timeout rolls back the batch.

```sh
psql -X -h 127.0.0.1 -v ON_ERROR_STOP=1 -f priv/local_source_map_retention/purge_expired.sql
```

The purge clears logical payloads in the live database. Physical erasure,
backups, and production cleanup are outside this workflow.
