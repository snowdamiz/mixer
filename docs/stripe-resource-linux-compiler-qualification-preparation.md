# C6 compiler qualification prepared; native selection pending

The new packet prepares one bounded private compiler qualification. No container
was created or started and no compiler, helper, NIF or BEAM ran in this lane.
The authoritative current data report is
`verification/stripe-resource-linux-compiler-qualification-preparation/data-audit-final.json`.
`proposal.json` and `root-selection.template.json` provide the exact next
selection. The adapter defaults to a refusal and checks a separately saved,
hash-bound root selection before any native command.

The C5 seal remains SHA256
`3ab8ace95199d687132e0709e033cd219a6f5053780a2b3c4ef16b732f5f0dfd`.
The original 177,326,080-byte compiler-only tar remains SHA256
`30583d60dc1206350578b75b34aa93af77de321c6efb606fe51c5c5371e1347b`.
The 36-package signed lock remains SHA256
`4db8b41afffdf796acaec18bcc3b5574be593af0c11c4cb860b39da5d64a36b4`.
The host audit verifies the C5, C4 acquisition and C3 metadata seals, including
the local archive caches, all 2,313 payload paths and 175,622,203 regular bytes.
It parses all 88 ELF objects as data and follows symlink ancestors as well as
complete link chains. It preserves the prior native signature/index/lock byte
graph; it does not claim a fresh cryptographic signature-verification run.

All 23 missing targets are preserved: nine library links and fourteen
documentation links. None is referenced by the selected compiler ELF closure.
The apparent extra README alias in the early development report resolves
through `gcc-13 -> gcc-13-base`; the corrected resolver has an explicit regression
control. The four earlier unsealed data reports remain historical development
outputs and do not supply the current closure. Missing documentation is not
silently repaired or called notice-completeness acceptance.

The selected compiler roots are GCC 13, `cc1`, `collect2`, GNU `as`, GNU `ld.bfd`,
GNU `readelf` and GCC's implicitly loaded `liblto_plugin.so`. Their payload
dependencies resolve to exact original file hashes. Six base ELF names remain
requirements; `libgcc_s.so.1` is also required for GCC's default output-link
contract. Retained installed-package versions alone do not prove these files.

| Base name | Retained byte evidence | Next observation |
| --- | --- | --- |
| `libc.so.6` | V3 original pinned image hash | Recheck bytes, dependencies and GNU versions |
| `ld-linux-aarch64.so.1` | V3 original pinned image hash | Recheck bytes, aliases and GNU versions |
| `libz.so.1` | C5 pinned base-library hash | Recheck ELF and versions |
| `libzstd.so.1` | C5 pinned base-library hash | Recheck ELF and versions |
| `libgmp.so.10` | Exact baseline package inventory only | Obtain bytes and transitive/version closure |
| `libm.so.6` | Exact baseline package inventory only | Obtain bytes and transitive/version closure |
| `libgcc_s.so.1` | Exact baseline package inventory only | Obtain bytes and transitive/version closure |

The proposed adapter first creates one stopped container from
`hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde`,
arm64 child
`sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de`.
It streams fixed base files with `docker cp -L` into bounded retained tar files,
inspects their bytes in memory without host extraction, and recursively proves
`DT_NEEDED` providers and required GNU version definitions. Unrecognized search
paths, files, formats or bounds fail before start. It also captures the complete
original ERTS include directory, rechecks the three previously pinned ERTS 17.1
headers and retains the hashes of any additional original headers. This avoids
inventing an incomplete NIF include closure. Five inherited base-library notice
files are captured as data where available; component licensing and
redistribution acceptance remain root-owned and pending.

After that preflight, the same one selected attempt starts. The unchanged C5
tar is extracted only in the container to
`/opt/mixer-compiler/toolchain`; all 1,996 regular file hashes are rechecked.
Original payload files and symlinks remain unchanged. Selected exact base ELF
files are added under the private prefix's `usr/lib/aarch64-linux-gnu`. A new
prefix-only `lib -> usr/lib` alias and a verified loader copy at
`usr/lib/ld-linux-aarch64.so.1` satisfy the unchanged libc linker script's
absolute sysroot paths. These are compiler/sysroot prerequisites. They do not
produce a service image or a runnable service root filesystem.

The exact driver is
`/opt/mixer-compiler/toolchain/usr/bin/aarch64-linux-gnu-gcc-13`.
`native-qualify.sh` supplies explicit GCC subprogram/start-object prefixes,
`--sysroot=/opt/mixer-compiler/toolchain`, explicit system-header and library
directories, and a single private library search directory. It clears inherited
compiler search overrides. Before compiling, GCC-reported compiler, assembler,
linker, libc and startup-object paths must remain within the prefix.
The unchanged reviewed `fault_helper.c` and `control_nif.c` are each compiled
twice with C11, O2, Wall, Wextra and Werror; the NIF additionally uses fPIC,
shared and the original verified ERTS include directory. Link traces, compiler
version/search output, complete `readelf` output, exact artifact bytes, hashes,
ELF dependencies and repeat-build equality are retained. The outputs live under
noexec `/tmp` and are never invoked or loaded.

The attempt retains the original 120-second total, 30-second command, 20-second
compile, 1-GiB memory, two-CPU, 128-PID, core-zero and 768-MiB owned-storage
ceilings. The total private tmpfs stays 512 MiB. The exact proposed policy change
splits it into a 256-MiB executable compiler prefix and 256-MiB noexec `/tmp`.
This explicit exception is necessary to execute the newly assembled compiler.
Exports have a separate cumulative 80-MiB ceiling; base/header/product file
counts and individual sizes are bounded. The container remains nonroot,
network-none, readonly-root, capability-free and no-new-privileges with one exact
readonly input mount. Cleanup checks the random ownership token, exact name,
image and ID before removal and records observed absence. It removes the owned
temporary input snapshot on every outcome. The attempt directory is exclusive;
failed attempts remain immutable and no retry or budget increase is automatic.

The unchanged V5 backend hardcodes controller `/usr/bin/cc` and its existing
argument contract. This prefix qualification intentionally leaves that integration
requirement open. No `/usr/bin/cc` alternative or wrapper is created, no V5 source
or frozen catalog/authority lane is changed, and compiler outputs from this
invocation cannot be called qualified V5 runtime artifacts. Full header/ELF ABI
qualification, actual NIF loading, helper behavior, all thirty resource rows,
service/rootfs construction and runtime selection remain separate gates.

Thirty-three host controls and shell syntax pass. Commands, tools, source revision,
source hashes, output hashes and limitations are retained in `host-commands.json`
and `receipt.json`. No package acquisition, container start, host payload
extraction, service publication, product release, customer action or GA acceptance
is claimed by this source-preparation packet.
