# Private Linux resource harness implementation packet

This packet implements a private controller, namespace/reaper launcher, fixed
FD3 control NIF and finite fault drivers. **It is an incomplete implementation
of the full selected R01–R18 replay and has no Linux runtime acceptance.**
All 30 selected resource/transport/ingress rows remain pending. No hosted source,
ordinary application role, public route, provider connection or trailer policy
changes. No catalog-inspector or authority-driver review is retried.

The controlling selection is
[`selection.json`](../verification/stripe-webhook-resource-ingress-root-review/selection.json).
Its exact profile remains byte bound, including the historical proposal-status
field. The selected
[`mutable-execution-index-amendment.json`](../verification/stripe-webhook-resource-ingress-root-review/mutable-execution-index-amendment.json)
permits root to update `PLAN.md` as execution metadata. Every preflight records
both its historical and observed digest. Every implementation, product-plan,
lock, dependency and source-map input remains strict. The original refusal for
`PLAN.md` drift is retained under `results/macos-preflight-attempt-1`.

## Implemented boundary

[`run.py`](../verification/stripe-webhook-linux-resource-harness/run.py) defaults
to a read-only capability preflight. A runtime invocation requires an explicit
`--execute`, a fresh independent source-review receipt bound to the exact four
implementation files, an explicitly delegated cgroup-v2 parent and a sealed
Linux root filesystem. There is no host-process, weaker-profile, image-pull,
daemon-start or software-install fallback. The controller stays outside the
stress cgroup and creates only one identity-marked child at a time.

Before task admission it configures and reads back the selected cgroup limits,
checks every ancestor and verifies the plain local `core` collector policy with
`fs.suid_dumpable=0`. It refuses piped/unknown collectors. The C launcher sets
hard/soft limits before joining that configured child, then creates private
mount, network, PID, IPC and UTS namespaces before any role/helper fork. The
namespace PID1 reaper and BEAM PID2 share the kill domain. It mounts a materialized
read-only root, read-only private harness files and `/proc`, fixed `/dev/null`,
and an 8 MiB private `/tmp` tmpfs. Only loopback is enabled. Capabilities,
supplementary groups and privilege escalation are dropped before BEAM exec.
The role cannot access a cgroup filesystem or a writable host/secret mount.

The role inherits FD0/1/2 and one AF_UNIX `SOCK_SEQPACKET` control endpoint on FD3.
`close_range` removes all other inherited descriptors. This scoped channel is
controller authority by exclusive owned inheritance, exact launch, source and
controller-minted generation. `SO_PEERCRED` identifies the creating controller;
it is **not evidence of the post-fork sender PID**. The NIF marks FD3 close-on-exec
before any helper can be spawned. Helpers and the reaper never hold the role
endpoint after exec/launch.

The channel accepts only `ready <generation> <port>`, `stop <generation>` and
`stopped <generation> completed`, at most 256 bytes. Unknown, replayed,
wrong-generation, truncated and ancillary-bearing packets fail closed. Both
controller and NIF close all received `SCM_RIGHTS` descriptors before rejecting;
all credential ancillary data is unexpected. No per-message credential or
namespace sender-PID claim is made. The NIF uses fixed FD3 and nonblocking bounded
syscalls; it has no arbitrary FD/path operation or HTTP-selected capability.

Exec can reset dumpability. CORE=0, FSIZE=0 and the verified non-piped collector
protect the interval before the private NIF loads. The NIF then sets and reads
back `PR_SET_DUMPABLE(0)` before transport startup/readiness and reports the
pre-init numeric dumpability separately. The packet does not claim dumpability
survives exec or that the Linux NIF has been compiled on this Mac.

The role invokes the unchanged `WebhookTransport.start_link(private_plug)`,
`capture/1` and `dispose/0` in one standalone VM. The ordinary hosted application
does not start. The original request owner performs each HTTP read. The fixed
synthetic plug returns only the existing non-2xx 418 capture marker, with no
billing authority or provider signature verification. A private admission gate
closes before supervisor disposal. The controller requests this closure before
SIGTERM, records whether it observed the acknowledgment, grants the selected
2000ms grace and then uses `cgroup.kill`; zero tasks are required by 2500ms from
stop, with actual overshoot retained. A dead/frozen VM cannot own this deadline.

Separate stdout/stderr collectors cap each pipe at 1 MiB, accept only fixed JSON
counter schemas, reconstruct allowed records and terminate on unknown/overflow
output. Rejected bytes never enter runtime receipts. Sentinel matches are
booleans and are supplementary checks, not a sanitizer or privacy proof.
Samples retain actual controller observation times and numeric cgroup/VM/RSS/
FD/socket counters. Every observed process's hard/soft limits are collected
separately from numeric samples. Shared binary metadata can double count; RSS
and BEAM sampling are observations rather than absolute peaks. Kernel peak
support is recorded explicitly. OOM attribution requires the cgroup's
`memory.events:oom_kill` delta together with process exit/signal.

## Linux artifact interface

`--release` names a fully materialized, root-owned, non-writable, symlink-free,
hardlink-free root filesystem. Its `release-manifest.json` is a closed schema-1
object with exactly these fields:

```text
schema platform architecture libc elixir otp erts compiler imageDigest
sourceDigest sourceClosureDigest lockSha256 files runtimeLibraries
productionExportsDigest buildReceiptDigest nifHeaders
controlNifSourceSha256 controlNifCompilerSha256
```

`platform` is `linux`; architecture matches the host; Elixir/OTP/ERTS are exactly
1.20.4/29.1.1/17.1. `sourceDigest` is the accepted 73-input digest;
`sourceClosureDigest` covers the complete selected 93-input historical map,
including the preserved historical execution-index metadata. Every current
non-`PLAN.md` input must match. `files` lists every regular file except the one
top-level manifest, by relative path and SHA-256. No nested manifest exclusion,
device file, symlink, hardlink, set-ID file or writable group/other entry is
allowed. A nested mount beneath the root is refused.

`runtimeLibraries` maps at least `libc`, `libcrypto`, `libssl` and `beam.smp` to
closed `{path, sha256}` records present in `files`. Each is checked for Linux ELF,
64-bit little-endian format and the selected machine. `imageDigest` is an exact
`sha256:` OCI image identity. Mac BEAM/native libraries cannot qualify. The
builder must provide its exact Linux dynamic-library inspection and production
export/exclusion receipts; a declared digest is not independent build provenance.
The manifest binds `opt/mixer/build-receipt.json` and
`opt/mixer/production-exports.json`, and the former must identify Linux, the exact
source input map, lock and pinned tool versions. Their actual build replay remains
an independent review gate.

`nifHeaders` binds exactly `usr/include/erl_nif.h`, `usr/include/erl_drv_nif.h`
and `usr/include/erl_int_sizes_config.h` from the matching ERTS toolchain.
`controlNifSourceSha256` binds the owned NIF source;
`controlNifCompilerSha256` binds the resolved existing `/usr/bin/cc`. Compiler
identity, libc/OpenSSL/ERTS files and the complete Linux build environment remain
part of the artifact receipt. No header/tool installation is performed.

Required paths include `usr/bin/elixir`, `bin/sh`, `dev/null`,
`opt/mixer/release/lib/*/ebin`, `proc`, `tmp`, and empty regular placeholders at
`opt/harness/role.exs`, `opt/harness/fault_helper`,
`opt/harness/control_nif.so`. The launcher mounts the exact reviewed harness files
read-only over those placeholders in its private mount namespace. They are not
production release exports or dependencies. The minimal role environment is
PATH, LANG, LC_ALL, two fixed crash-dump settings and two controller-minted
generation/mode variables. No controller HOME, cookies or provider variables are
inherited.

## Driver completeness and remaining work

The sealed packet matrix preserves all R01–R18, T01–T05 and I01–I07 requirements.
R03, R09–R13 and R15 have bounded candidate drivers for independent Linux replay.
They remain unexecuted and unaccepted. R01/R02 controller guards and host negative
controls exist, but comprehensive Linux prelaunch failure fixtures remain pending.
R04–R08 need the full exact-byte H1/H2, overflow, large-frame/header-expansion,
frozen-reader, control-traffic and cancellation replay. R14 needs every selected
shutdown phase. R16 and R17 contain partial synthetic crash/output injectors but
cannot run as accepted cases: crash metadata, every output-overflow/drift control
and complete sink evidence are unfinished. R18 needs exhaustive lifecycle-stage
failure injection and namespace/socket/pipe-holder cleanup proof.

The controller returns `unavailable` for every driver-incomplete row, even on a
capable Linux host. It never substitutes a generic smoke assertion. Therefore
the whole R01–R18 suite cannot currently pass. The private T01–T04/I01 cases,
public trailer decision, deployed ingress/TLS/Cloudflare controls, P15/P16,
Stripe/Neon staging and G23 stay separately pending.

```text
python3 -B verification/stripe-webhook-linux-resource-harness/test_host.py
python3 -B verification/stripe-webhook-linux-resource-harness/run.py \
  --output <packet>/results/<new-owned-preflight-directory>
python3 -B verification/stripe-webhook-linux-resource-harness/verify.py --live
```

Runtime additionally uses `--execute --review <fresh-source-review.json>
--delegated-cgroup <explicit-parent> --release <sealed-linux-root>`. The review
object has exactly schema, status, harnessDigest, profileDigest, sourceDigest,
reviewer; status must be
`independent-source-review-approved-for-private-runtime`. No such approval or
Linux artifact is authored by this implementation packet.

The host tests run the actual Python profile/output/channel parser and real
SCM_RIGHTS transfer/closure. Their isolated Unix DGRAM fixture is explicitly a
host component test, never a runtime substitute for selected SEQPACKET. Selected
SEQPACKET and Linux credentials are platform skips on this Mac. The preflight
returns 78 with zero runtime cases. No role, stress helper, listener, namespace,
cgroup, database, daemon, container image, native instance or provider was started.
Temporary host-test directories and sockets are disposed; initial failures and
all redacted evidence remain sealed. No Linux C/NIF/BEAM compilation or physical
phone qualification is claimed.
