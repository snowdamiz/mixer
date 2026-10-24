# Private resource Linux artifact preparation

This packet prepares the next artifact prerequisite for the accepted V5 private
resource harness. It performs source/hash replay and read-only Docker metadata
inspection on macOS. It builds no image, release, helper or NIF and starts no
container, BEAM, namespace or resource test. Linux compilation, ABI resolution,
resource enforcement and all 30 runtime matrix rows remain pending. The full
product scope and every GA gate remain required.

The executable host replay is
`verification/stripe-resource-linux-artifact-preparation/audit_inputs.py`.
Its output and negative controls are host evidence only. `preparation.json`
records commands, host tool identity, source revision context and exact input
hashes. `build-plan.json` records proposed operations; none is executed here.

## Selected source and candidate image

The V5 producer seal is
`22e44e7b2a5d507e0fa2d6cd84aa1b835123d322d8b91baf7004b827490e8c85`.
Its independent review seal is
`829f24609f9033c462ffb0b72f276535da68721acf438f0571e432cef6732348`.
The root source acceptance receipt explicitly declines Linux compilation,
Linux runtime and runtime authorization. This packet preserves that scope.

The accepted baseline contains 73 inputs, digest
`1b2f03d474f825a6265e0a10f9baf2adda62dffe6c747542207f32753b4df997`.
The historical 93-input closure digest is
`93b25f059192187ca6376bb843fcf2a6c7647dd569fd322a43b8cf81e65eff74`.
Every live non-`PLAN.md` binding matches. The selected execution-index amendment
permits that file to change; the build receipt must retain the historical input
map returned by `source_inputs()`, and separately record current source context.

The already installed candidate is
`hexpm/elixir:1.20.4-erlang-29.1.1-ubuntu-noble-20260911`:

| Identity | Value |
| --- | --- |
| OCI parent index | `sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde` |
| Inspected Linux arm64 platform manifest | `sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de` |
| Docker architecture | `arm64` |
| Required Python machine / ELF machine | `aarch64` / `183` |
| Required Elixir / OTP / ERTS | `1.20.4` / `29.1.1` / `17.1` |

Both index and platform observations are retained. The tag is context; the
platform manifest is the proposed immutable builder input. Metadata does not
prove the executable payload, compiler availability, NIF headers or ERTS version.
The final artifact's `imageDigest` must identify its actual final build image;
if a derived compiler image becomes necessary, retain both base digests and the
derived image digest, recipe and tool inputs. Do not label a derived environment
with the base image's digest.

The root's discovery records Docker 29.8.2, Linuxkit 7.0.14, Linux arm64,
cgroup v2 with cgroupfs and 8,318,844,928 bytes daemon memory. This is environment
inventory, not delegated cgroups or namespace capability proof. The current
lane has not read or changed Linux core, cgroup or namespace policy.

## Existing supported build inputs

Use `hosted/mix.exs`, `hosted/mix.lock` and `hosted/.tool-versions` unchanged.
The lock SHA-256 is
`59e6fe5d6bc76ae0057745fe7eb3fb292f225b6a37cd1c99c214f9447c60ff8a`.
It pins 21 Hex packages, including Bandit 1.13.1, Plug 1.20.3, Phoenix 1.8.16,
Thousand Island 1.6.0, HPAX 1.1.0, Jason 1.4.5 and Mint 1.11.0. The exact full
dependency set and package checksums remain in the lock, not an alternate lock.

All 914 dependency source files match
`verification/hosted-identity-metrics-output-check/linux-final/dependency-manifest.json`.
The installed Hex 2.5.1 archive's 133 files and the existing rebar3 match that
prior Linux tool receipt; rebar3 SHA-256 is
`8dead71212b8008ec830c085607c23ec2997ab1c36a3c91901ac42c9814ee08c`.
Reuse owned copies of these verified source/tool inputs offline. Exclude every
`_build` directory and compiled Mac dependency object. No credential, production
configuration, `.git`, controller HOME or service environment is a build input.

The supported production sequence is the existing
`MIX_ENV=prod mix release --overwrite` in `hosted/scripts/test-local.py`.
The CI locked-resolution command is `mix deps.get --check-locked`. Reuse those
commands in isolated staging with network disabled; a missing input fails the
attempt. `hosted/scripts/dependency-inventory.exs` produces the dependency report.
Do not run `test-local.py` wholesale for artifact preparation: it also launches
PostgreSQL and tests. Do not reuse identity lane launchers wholesale: they grant
NET_ADMIN and execute network setup that this artifact build does not need.
Compiler, libc, OpenSSL and binary inspection tools still need exact Linux pins;
this packet does not install arbitrary packages or claim they exist in the image.

## Actual root filesystem and compiler contract

The authoritative validator is inherited `run.py:165`;
the V5 backend compiler is `v5/linux_backend.py:242`. `source-contract.json`
records the exact manifest field set and compiler argv extracted using Python
AST without importing or executing those modules. This is inspection, not OTA
release authorization.

`release-manifest.json` has exactly 19 fields:

```text
schema platform architecture libc elixir otp erts compiler imageDigest
sourceDigest sourceClosureDigest lockSha256 files runtimeLibraries
productionExportsDigest buildReceiptDigest nifHeaders
controlNifSourceSha256 controlNifCompilerSha256
```

Every rootfs entry must be a real directory or a singly linked regular file,
UID 0, with `(mode & 0o6022) == 0`. This forbids set-ID and group/other write;
the validator does not itself forbid owner write. Proposed final modes are
0555 directories/executables and 0444 other files. Runtime makes the mounted
root read-only separately. No symlink, hardlink, device node, FIFO, socket,
nested mount or `sys/fs/cgroup` entry is allowed. The absolute rootfs path must
resolve to itself. List every regular file except the single top-level manifest
in `files`; nested manifests receive no exclusion. Bound is 1–50,000 files.

Required rootfs inputs are:

| Path or group | Required provenance and behavior |
| --- | --- |
| `usr/bin/elixir`, `bin/sh` | Real materialized files from the selected Linux toolchain, with their complete script/interpreter/tool dependencies. Verify the Elixir launcher can find the copied runtime at these exact paths. |
| `opt/mixer/release/lib/*/ebin` | Fresh Linux production `mix release` output and locked runtime dependencies, with test support absent. Include the release's runtime files required by the selected launcher. |
| `runtimeLibraries` | At least libc, libcrypto, libssl and beam.smp; each closed `{path, sha256}` entry must be in `files`, ELF64 little-endian, machine 183. Include every additional loader, shared library and runtime-loaded native dependency actually required. |
| `usr/include/erl_nif.h`, `erl_drv_nif.h`, `erl_int_sizes_config.h` | Exact three files from matching ERTS 17.1 toolchain, bound under `nifHeaders`. Compiler's Linux system headers and tool closure are separate build inputs. |
| `opt/harness/role.exs` | Exact sealed V5 role source, SHA-256 `43f5c3b5f7285b9670c506308389f75af285199503364b82c5a8cace56a5bd02`. |
| `opt/harness/fault_helper` | Actual sealed Linux ELF compiled from V5 `fault_helper.c`, source SHA-256 `d0ffe3524d3ae41d95a4cffebb40806bc11f8a3a9361151490832761d64f17c8`. |
| `opt/harness/control_nif.so` | Actual sealed Linux ELF compiled from V5 NIF source, SHA-256 `ffbb62dc0d5853a70a56b54565bfbe011b00e193adc2fb995e4d2c1645b212fb`. |
| `dev/null` | Empty regular bind target, not a copied device node. The later private launcher binds actual `/dev/null` over it. |
| `proc`, `tmp` | Empty real directories with preflight-compatible modes. The later launcher mounts read-only proc and the fixed 8 MiB tmpfs; rootfs `/tmp` must not start as mode 1777. |
| `opt/mixer/build-receipt.json` | Linux, exact historical sourceInputs map, lock, Elixir and OTP; also retain full build/tool/image/source/artifact provenance for independent replay. |
| `opt/mixer/production-exports.json` | Actual production BEAM export and test-helper exclusion receipt, bound by its bytes. No fabricated export report or Mac export substitution. |

The old Linux artifact prose describes empty helper/NIF placeholders. The actual
V5 compiler compares fresh compiler output with these paths' manifest digests;
therefore empty files cannot qualify. The rootfs must hold real expected ELF
bytes at both bind targets. The inherited NIF source binding is compatible:
v1 and V5 NIF source bytes match. The helper source differs from v1; use V5.

The exact compiler commands use the existing controller environment only:

```text
PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8
ERL_CRASH_DUMP=/dev/null ERL_CRASH_DUMP_SECONDS=0

/usr/bin/cc -std=c11 -O2 -Wall -Wextra -Werror <absolute-V5>/fault_helper.c -o <owned-scratch>/fault_helper
/usr/bin/cc -std=c11 -O2 -Wall -Wextra -Werror -fPIC -shared -I <absolute-rootfs>/usr/include <absolute-V5>/control_nif.c -o <owned-scratch>/control_nif.so
```

`compiler` is the exact first ASCII line of `/usr/bin/cc --version` and
`controlNifCompilerSha256` hashes its resolved executable on the future Linux
controller. A compiler copied only inside rootfs is insufficient: the backend
executes the controller's `/usr/bin/cc`. Pin the driver, linker, compiler helper
executables, system headers, libc development inputs and search paths in the
builder receipt too. Fresh compilations have a 20-second maximum each and must
exit zero with no stdout or stderr. Output must be ELF64 little-endian for the
actual machine and byte-identical to the two manifest entries.

The runtime picks a fresh random scratch path under the sealed V5 directory.
Before selection, replay both exact compiler commands at distinct scratch paths
with the eventual absolute V5/rootfs paths, same fixed environment and same
controller compiler image. Compare outputs empirically. Do not add alternate
flags, timestamps, wrappers or source rewrites to make hashes agree. Linux
symbol/dependency resolution and actual NIF loading remain separate evidence.

## Proposed staged execution and unresolved prerequisites

1. Root selects a bounded compilation-only qualification using the inspected
   platform digest. No resource role is included. A disposable container would
   run as a nonroot UID, network none, all capabilities dropped, no-new-privileges,
   read-only image and input mounts, and only newly owned staging/tmp writable.
   Suggested limits are 2 CPUs, 4 GiB memory and 256 tasks. These are build limits,
   not the sealed resource profile. No Docker socket, host PID namespace, cgroup
   delegation, provider variables, privileged flag or NET_ADMIN is needed.
2. In that separately selected operation, inspect actual Elixir/OTP/ERTS,
   `/usr/bin/cc`, NIF headers, Hex/rebar, libc/OpenSSL and ELF inspection tools.
   Existing image metadata cannot resolve these checks. Missing compiler or
   inspector inputs stop here until an exact supported tool image/recipe and
   dependency provenance are selected. No automatic apt install or mutable tag.
3. Stage the accepted sources and 914 verified dependency source files without
   compiled outputs. Use fresh owned `MIX_HOME`, `MIX_REBAR3`, build and dependency
   paths; run locked resolution, dependency compile and production release using
   the supported Mix sequence. Capture commands, versions, image identity,
   environment allowlist, bounded logs, hashes and source-before/after checks.
4. Capture Linux production export/exclusion evidence by loading production
   modules without starting the hosted application, provider, transport or
   private role. Reuse the existing production policy assertions in
   `hosted/scripts/test-local.py`; emit a separately reviewed machine report.
   Running this BEAM inspection is proposed future work, not performed here.
5. Build the minimal rootfs from the selected image/release, materializing links
   and complete interpreter/ELF/native runtime closure with exact provenance.
   Inspect ELF program headers, DT_NEEDED, RUNPATH and symbol versions using a
   pinned static inspector. Do not treat `ldd` or four declared library hashes
   as closure proof. Preserve any runtime symbol-loading uncertainty explicitly.
   Compile/seal actual V5 helper and NIF bytes and replay them at distinct paths.
6. Generate the two content-bound receipts and exact manifest from observed
   files. An unprivileged build may produce an archive with UID-0 metadata; that
   is not proof of actual root ownership. Root must select the isolated artifact
   materialization/finalization and inspect the resulting filesystem. Do not
   chown a shared host checkout or alter preexisting images/containers.
7. An independent reviewer replays build provenance, production exclusions,
   compiler equality, ELF closure and manifest rejection cases. Invoke the actual
   inherited `release_manifest()` on Linux and `validate_release()` only after
   its compiler/tool checks are separately selected. This calls no helper or
   role, but does read Linux mount metadata. Mac host controls are insufficient.
8. Only after artifact acceptance does root choose any resource environment and
   issue the exact fresh private-runtime review/authorization receipt expected
   by V5. The existing source acceptance is deliberately not that receipt.

Runtime environment prerequisites remain unproved: a genuine writable delegated
cgroup v2 parent with memory/cpu/pids subtree controllers and acceptable ancestor
limits; exact profile readback and cgroup.kill; setup capabilities
KILL, SETGID, SETUID, SETPCAP, NET_ADMIN, SYS_CHROOT, SYS_PTRACE and SYS_ADMIN;
pidfd APIs; mount/net/PID/IPC/UTS namespace operations; metadata visibility for
per-TID cleanup; and observed core_pattern `core` / suid_dumpable `0` without an
unknown collector. Docker daemon cgroup/version metadata proves none of these.
Any needed policy change requires separate selection; no mutation is proposed
as an automatic fallback. Physical phones remain disconnected and deferred.

The artifact compile lane may qualify its own build only. It cannot qualify
R14/R18 execution, the remaining resource drivers, trailer policy, TLS, deployed
ingress, provider operations, production, customer readiness or GA. The catalog
inspector and authority-driver lanes are outside this packet entirely.

## Host replay

```text
python3 -B verification/stripe-resource-linux-artifact-preparation/audit_inputs.py --root /Users/andreyyurlov/Documents/dev/mixer
python3 -B -m unittest discover -s verification/stripe-resource-linux-artifact-preparation -p test_audit_inputs.py -v
```

These commands check current source/tool file hashes against retained selected
receipts and validate recorded image identity. They invoke no Docker or BEAM
from the replay code. Negative controls mutate only new temporary fixtures;
temporary files are removed. Replaying recorded metadata does not refresh the
daemon. No Linux artifact exists in this preparation packet.
