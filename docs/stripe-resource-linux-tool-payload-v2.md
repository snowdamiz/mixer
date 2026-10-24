# Private Linux tool-payload V2: pre-start image-field mismatch

V2 resolved the selected parent image reference and its exact Linux arm64 child
manifest. It created one owned container, then refused to start it because the
selected container `Image == child` predicate did not match Docker's observed
representation. The owned container was removed and verified absent; temporary
inputs were removed. Zero Linux tools, BEAM versions, compiler commands, helper
executions, NIF loads or resource rows ran. Linux tool availability and compilation
remain unverified.

Root selection:
`verification/stripe-webhook-resource-ingress-root-review/linux-tool-payload-v2-selection.json`,
SHA-256 `ac0d22b65171950bb448ae2b777243c1c2908165b654aa8a4a4d390d1bac9caf`.
The preparation seal and closed failed V1 packet remain unchanged. No Git,
download, pull, tag, install, image build, rootfs construction, native/provider or
resource execution was performed.

## Actual image observation

The read-only image inspect, selected by parent reference and explicit platform,
passed all parent/child checks:

| Field | Observed value |
| --- | --- |
| Parent address | `hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde` |
| Image inspect `Id` | `sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de` |
| Image inspect `Descriptor.digest` | Same required child digest |
| Platform | `linux/arm64` |

After create, the actual container inspect reported:

| Container field | Observed value |
| --- | --- |
| `Config.Image` | Selected parent reference above |
| `Image` | Parent index `sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde` |
| `ImageManifestDescriptor.digest` | Required child `sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de` |
| `ImageManifestDescriptor.platform` | `{architecture: arm64, os: linux}` |

The selection's explicit additional check required the container `Image` field
to equal the child digest. The runner therefore refused before `docker start`.
It did not substitute `ImageManifestDescriptor.digest` or create a second
container. Raw evidence is `attempt-1/04-policy-before.stdout`; the failed
predicate is retained in `attempt-1/receipt.json`.

This observation identifies the actual Docker API fields. It does not establish
Linux executable versions or authorize replacing a selected predicate. Root must
separately select any use of the actual descriptor field before another attempt.

## Controls, limits and cleanup

The V2 probe shell is byte-identical to V1. The runner changes addressing and
selection bindings only, adds exact parent-index/child-manifest checks, checks the
required container field before start, and omits Git entirely. The read-only
input snapshot again contains exactly three files: probe shell and sealed V5
helper/NIF C sources. Only that new snapshot would be mounted read-only.

Create used the selected nonroot UID/GID 65534, network none, read-only root,
cap-drop ALL, no-new-privileges, 128 tasks, 1 GiB memory, 2 CPUs, core limit zero,
private 128 MiB noexec/nosuid/nodev tmpfs and no writable host mount. Raw inspect
retains the configured options. They were not exercised by a running container.
No policy, privilege, runtime or source fallback was attempted.

Cleanup first re-inspected the exact container ID, name, ownership token and
selected configured parent image. It removed only that matched owned container
and re-inspected the same ID to prove absence. The temporary input snapshot was
removed. No unrelated container was inspected or modified.

Ten finite host controls pass. The new controls accept the correct parent/child
image observation and refuse changed or missing parent/child/platform identities,
including a container child-field mismatch. Inherited controls cover owner/ID,
image, user, privilege, network, limits, mounts and command. These test the host
policy methods with fixtures; they are not Linux enforcement evidence.

```text
python3 -B -m unittest discover -s verification/stripe-resource-linux-tool-payload-v2 -p test_run.py -v
sh -n verification/stripe-resource-linux-tool-payload-v2/probe.sh
```

The retained failed attempt must not be removed to rerun the packet. The
collector's exit 0 means its receipt was written; qualification is the receipt's
failed status. Independent review of this packet remains pending. Actual Linux
tools, helper/NIF compilation, production release/rootfs, ABI/symbol closure,
all 30 runtime matrix rows, provider/deployment/native/customer and GA evidence
remain pending. Physical phones remain disconnected and deferred. No catalog
inspector or authority-driver operation occurred.
