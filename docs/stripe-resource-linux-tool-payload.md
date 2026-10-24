# Private Linux tool-payload prerequisite: selected image reference unavailable

The selected local prerequisite failed during image preflight. Docker 29.8.2
could not resolve
`hexpm/elixir@sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de`.
The daemon returned exit 1 and `No such image`. No container was created or
started. No Linux tool, BEAM, C compiler, helper or NIF executed. No compiled
artifact, production release or rootfs was produced. This is an observed failed
prerequisite, not Linux compilation or resource acceptance.

The controlling selection is
`verification/stripe-webhook-resource-ingress-root-review/linux-tool-payload-selection.json`,
SHA-256 `975fc923c0294731b8d6fcb03c8fac8964d83d1336ca69b06ac655dced1ba381`.
The prior preparation packet remains unchanged under seal
`e72d9e750aceba69d22ec01d2e41d64897db60de37e48482aae944030fe53f9b`.

## Observation and scope

The earlier read-only preparation inspected the parent OCI index reference
`hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde`
with `--platform linux/arm64`. Docker reported the selected platform manifest
descriptor `sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de`.
That observation did not establish that the repository at the child-digest
reference was independently addressable in the local image store.

The actual command was:

```text
docker image inspect --platform linux/arm64 hexpm/elixir@sha256:c2d3bab1f8a854f5ca3bb220e5463f4fe39036caa2ce22dfd7614a30404279de
```

`attempt-1/02-image-inspect.stdout` contains Docker's empty result array;
`attempt-1/02-image-inspect.stderr` retains the exact daemon error. The receipt
binds those outputs, the command, source revision context, Docker and host Python
identity, selection, input snapshot and runner source. No tag/index fallback,
pull, install, image build or local alias mutation was attempted.

The one selected preflight attempt performed zero container creates and zero
container starts. The new three-file input snapshot contained only the owned
probe shell and the exact sealed V5 helper/NIF C sources. It was removed after
the refusal. Exact-name inspections before and after cleanup both returned
`No such container`. No unrelated container was inspected or modified.

## Retained bounded runner

`verification/stripe-resource-linux-tool-payload/run.py` requires explicit
`--execute`, the exact root selection hash and unchanged preparation seal. It
creates its `attempt-1` evidence directory once; rerunning execution against this
packet refuses because that directory already exists. Do not remove the failed
attempt to rerun it. A later operation needs a separate root-selected packet.
The collector's process exit 0 means its receipt was written; qualification is
the receipt's `status`, which is `failed-prerequisite` here.

The runner contains policy checks for the selected future container only:
UID/GID 65534, network none, read-only image, all capabilities dropped,
no-new-privileges, 128 tasks, 1 GiB memory, 2 CPUs and zero core limit. The sole
bind is a newly owned three-file input snapshot mounted read-only at `/inputs`.
The only explicitly requested writable filesystem is a 128 MiB
noexec/nosuid/nodev tmpfs.
No repository, HOME, Docker socket, credentials or writable host directory is
mounted. A fixed sleeping init would keep the tmpfs available for copying only
the two known compiled outputs before identity-fenced removal. None of this
container policy was exercised against a live container in the failed attempt.

The retained probe would record actual Elixir/OTP/ERTS, compiler, linker, binary
inspection tools, NIF/system headers and library identities. Its two compiler
commands preserve V5's compiler flags, argument order and fixed environment,
using the observed native ERTS header directory as a tool input. They would not
construct a release/rootfs, execute the helper, or load the NIF. Such compilation
would remain distinct from runtime-path reproducibility and artifact acceptance.

The attempt has a 120-second wall bound and at most 512 KiB retained per stream,
with a smaller probe allowance reserving output space for cleanup. Removal
requires matching the exact name, ownership label, selected image and known
container ID. New temporary source inputs are removed on all handled outcomes.
No general container-list, unrelated-container removal or privileged fallback is
present in the runner.

## Host controls and remaining work

Seven finite host controls pass. They cover the accepted policy, changed
container identity/owner/image, privilege/network/user changes, resource-limit
changes, writable/extra/unselected mounts and alternate entrypoint. They execute
no Docker or Linux code. The probe passes host shell syntax validation. The
host controls validate source-side policy methods only; they do not prove Linux
enforcement, actual versions, compiler availability or disposal after a live run.

```text
python3 -B -m unittest discover -s verification/stripe-resource-linux-tool-payload -p test_run.py -v
sh -n verification/stripe-resource-linux-tool-payload/probe.sh
```

Root must separately select any correction to image addressing before another
attempt. Exact tool payload, Linux compilation, ELF/symbol closure, immutable
production release/rootfs, independent artifact review and every resource runtime
prerequisite remain pending. All 30 resource/transport/ingress matrix rows remain
pending; no deployment, provider, trailer, TLS, native, production or GA gate is
closed. Physical phones remain disconnected and deferred. The catalog-inspector
and authority-driver lanes were not entered.
