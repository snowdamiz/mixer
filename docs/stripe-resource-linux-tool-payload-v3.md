# Private Linux tool-payload V3: versions observed, compiler prerequisite unavailable

The selected isolated Linux tool probe executed and confirmed Elixir 1.20.4,
OTP 29.1.1 and ERTS 17.1 on aarch64. It exited 78 because the image has no C
compiler/linker, ELF inspection tools or required system development headers.
No compiler invocation or compiled artifact followed. This is actual Linux
version/hash evidence and an observed failed build prerequisite; it is not
Linux artifact or resource-runtime acceptance.

Root selection is
`verification/stripe-webhook-resource-ingress-root-review/linux-tool-payload-v3-selection.json`,
SHA-256 `b064f9923fde0f0d4534c22eda8973c7d7ea71ec272a66b66a73cb1b8e6adce0`.
V2 was sealed first at
`06e3a6e1306820f7fb9678687f33b4da9ed9e04915941b19bb375d55ffb14c58`.
The preparation, failed V1 and failed V2 packets remain unchanged. No Git was used.

## Actual tool observations

One container was created, started and probed. Before start the runner verified
the selected parent repository reference, parent `Image`, Linux arm64 child
`ImageManifestDescriptor`, container `Platform`, exact ownership and complete
selected configured isolation. The image-inspect `Id` and descriptor separately
matched the same child digest.

| Item | Actual result |
| --- | --- |
| Parent index | `sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde` |
| Required Linux arm64 child | `sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de` |
| Linux kernel | `7.0.14-linuxkit`, aarch64 |
| Process identity | UID/GID 65534 (`nobody` / `nogroup`) |
| Observed core limit | `0` |
| Elixir | `1.20.4`, version command exit 0 |
| Full OTP version file | `29.1.1` |
| ERTS | `17.1`, Erlang version probe exit 0 |
| Erlang architecture | `aarch64-unknown-linux-gnu` |
| Erlang root | `/usr/local/lib/erlang` |
| libc version | `glibc 2.39` |
| OpenSSL | `3.0.13` |

The two selected BEAM invocations are version/identity queries only. They do not
load the private NIF, execute its helper, start MixerHosted, open its listener or
run a resource role. The probe shell is byte-identical to the previous packets.

Observed content identities include:

| Linux file | SHA-256 |
| --- | --- |
| `usr/local/lib/elixir/bin/elixir` | `5cb23d89a78f75589b06fade3097e217b77e63416d61c1800f674579748c4307` |
| `usr/local/lib/erlang/bin/erl` | `439030cd68a264215add9feb4d896a3737cd451fded2070606829839419730f4` |
| `usr/local/lib/erlang/erts-17.1/bin/beam.smp` | `dca0882738dfd8bac0a4f07b464ffe2d5f9e1092fbd6a739e9f3a3a7db5f99d4` |
| `usr/local/lib/erlang/erts-17.1/bin/erlexec` | `6f7df7f519846397b266b095ce70d809fff8ca954bfdedc21ad2a714168a7a36` |
| `usr/local/lib/erlang/usr/include/erl_nif.h` | `6cb96c37d306a173ef71946e823829fc21e47cb4a19288b221129eac2f13b689` |
| `usr/local/lib/erlang/usr/include/erl_drv_nif.h` | `e9d4280779e8fd4ac463144f310b4da2346dd3a18e73d445bf1f88ae3c1f1312` |
| `usr/local/lib/erlang/usr/include/erl_int_sizes_config.h` | `b8aa9cc9cb9f2fd427dd22c4a8354b9e99f28138ff78088cb6286fda6c4e3846` |
| `usr/lib/aarch64-linux-gnu/libc.so.6` | `0f1905dc27dbc6715875c70527bc8da846a10084c9c483e9d8ff76dce8d69d0e` |
| `usr/lib/aarch64-linux-gnu/libcrypto.so.3` | `60076983c2ea0d6b73cc64fb39cafa0a0f90f220ef000f6effb4aaac47500949` |
| `usr/lib/aarch64-linux-gnu/libssl.so.3` | `4ba43e4182c8fe8813fef851e43b3cc09cd90d418760c0a94b13d1bf5d91cc09` |
| `usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1` | `390027e5f45f236bd1838bc54bf464c5ff01d260ab9f8b415ea8276641bce505` |

`observed-tools.json` contains these and the existing timeout/hash/path tools.
These are observed image-file hashes, not an assembled release manifest or proof
of full dynamic-library/symbol closure. No ELF inspector was available.

## Explicit missing prerequisites

The probe found no `cc`, `gcc`, `ld`, `as`, `readelf`, `objdump` or `file` on its
selected tool path. It also confirmed absent `/usr/bin/cc`, `/usr/bin/ld`,
`/usr/bin/as`, `/usr/bin/readelf` and `/usr/bin/objdump`.

Required system headers were absent at the checked paths:

```text
/usr/include/stdio.h
/usr/include/stdlib.h
/usr/include/unistd.h
/usr/include/linux/capability.h
/usr/include/aarch64-linux-gnu/sys/prctl.h
/usr/include/aarch64-linux-gnu/sys/resource.h
/usr/include/aarch64-linux-gnu/sys/socket.h
```

The exact three ERTS NIF headers are present, but they cannot replace those
Linux/libc development inputs. The probe emitted
`MIXER_COMPILE_UNAVAILABLE=required_tool_or_version_prerequisite` and exit 78.
No packages were installed or downloaded. No alternate image, compiler wrapper,
source edit or flag change was attempted. Root must separately select exact
compiler/linker/system-header/ELF-tool provenance before a fresh compilation
qualification. This packet does not propose a mutable package installation.

## Bounds, cleanup and verification

The actual container used network none, user 65534, read-only root, cap-drop ALL,
no-new-privileges, 128 tasks, 1 GiB memory, 2 CPUs and core limit zero. Its only
explicit writable filesystem was the private 128 MiB noexec/nosuid/nodev tmpfs;
the sole bind was the newly owned three-file input snapshot, read-only. There
was no repository, HOME, credentials, Docker socket or writable host mount.
Configured options were checked before start. These are prerequisite isolation
observations, not proof of the separate resource profile's kernel enforcement.

The attempt stayed within its 120-second bound and 512 KiB per-stream retained
limits. Raw commands/output record actual timing and byte counts. Cleanup
rechecked exact container ID, name, ownership label and configured image, removed
only that owned container, and proved its absence. The temporary snapshot was
removed. No unrelated container was inspected or modified.

Twelve host controls pass, including missing/changed parent, child, platform and
container-descriptor fields, ownership, privilege, network, limits and mounts.
The probe also passes shell syntax validation. Compilation, artifact-copy and
ELF-inspection branches remain unexecuted because their prerequisites were absent.

```text
python3 -B -m unittest discover -s verification/stripe-resource-linux-tool-payload-v3 -p test_run.py -v
sh -n verification/stripe-resource-linux-tool-payload-v3/probe.sh
```

Independent review remains pending. No release/rootfs, helper execution, NIF
loading, application/provider/native test, namespace/cgroup/core-policy change,
catalog-inspector or authority-driver operation occurred. All 30 runtime matrix
rows and every production/GA gate remain pending. Physical phones remain
disconnected and deferred. The failed attempt is retained and cannot be rerun
in place; any next operation requires a new root selection and evidence packet.
