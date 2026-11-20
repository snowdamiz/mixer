# Pair25 managed runner integration

Provision a fresh, operator-owned root with mode `0700` and keep its inputs
immutable for the runner lifetime. Create `outputs` with mode `0700`.

## Approve a Noble toolchain projection

Use the exact Pair25 Starter export with its original Mac lock at
`readonly/Export`. Verify the export against its renderer inventory and the two
bare Git mirrors against the export's locked revisions. Use the five archive
pins in `toolSources.archives` from the packaging receipt at
`1e81569c47842c07094f95b5d04009540b9365da`. Stage the Android build tools and
platform at `android-sdk/build-tools/37.0.0` and `android-sdk/platforms/android-37.0`.

Verify the pinned image manifest, platform, and config digest on the dedicated
daemon before copying files or starting a container. The following pins match
the observed Docker Desktop run.

| Use | Platform | Reference | Config digest |
| --- | --- | --- | --- |
| Swift Noble | `linux/arm64` | `docker.io/library/swift@sha256:a7ec691ec569f1ff646952ffad348aebf5d829718e91ad56ae05cae6e57016f8` | `sha256:c3fd097562c903a6bf029409205d84f59f71cd229f0f0dbfa63cab8210fe98ef` |
| x86-64 compatibility libraries | `linux/amd64` | `docker.io/library/ubuntu@sha256:77eb101c607d6e3d4f5ad0c8a02c2136c689b98aba1f359e6502ba517e5c57ec` | `sha256:7da97f743f397971f35dd21cd2d19a7da070a150e0cfa3eda559e71891ec7533` |
| Python 3.12 | `linux/arm64` | `docker.io/library/python@sha256:3dc01f342e31ad8de39338d14ab12de0090c9102b34f75ca9774ff1f4f5e904e` | `sha256:68a5583e8fc0d51a88558fb29ca20e02056e1267e0a58fd0408bd044e39dec7b` |

1. Copy `/usr/lib/x86_64-linux-gnu/.` from an unstarted compatibility container
   into `glibc`. Copy `/usr/local/.` from an unstarted Python container into
   `python`. Link `lib64/ld-linux-x86-64.so.2` to
   `/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2`.
2. Copy `prepare-toolchain.sh` into `recipe` and copy `managed_worker.py` to
   `recipe/worker.py`.
   Run `/bin/sh /recipe/prepare-toolchain.sh` offline in the pinned Swift image
   with the recipe, compatibility libraries, and verified archives mounted
   read-only. Mount a fresh case-sensitive local volume at `/toolchain`.
3. Run the lock phase offline in the same image with UID and GID `65534`, the
   `TMPFS` and `ENV` settings from `linux_android_pair25_layout.py`, and
   `PAIR25_VERIFIED_SWIFT_MANIFEST` set to `NOBLE_MANIFEST`. Use the layout's
   read-only input binds except the Linux lock overlay. Mount the populated
   volume read-only at `/toolchain` and a fresh, guest-writable `lock` directory
   at `/deliver`. Use `ENTRYPOINT` and `LOCK_ARGUMENTS` from the layout module.
4. After a successful lock phase, review `lock/linux-mixer.lock` and
   `lock/projection.json` against the verified export and toolchain. Keep the
   Linux lock at `lock/linux-mixer.lock`. Install the projection at the root
   as the operator to approve it.

   ```sh
   install -m 0600 "$stage/lock/projection.json" "$stage/projection.json"
   ```

5. Load `Pair25Layout.read(stage)` to get the exact `volume_name` and
   `volume_labels`. Create a fresh local volume with that name and those labels.
   Populate it offline from the same verified archives with `prepare-toolchain.sh`.
   Keep it immutable after provisioning.

The root-level approval pins both locks, the rendered driver, the package
locks, and the source tree fingerprint with the Linux lock overlaid. Admission
checks that the Linux lock changes only `android.toolchain`. It checks the
fixed worker and Python digests and binds the lock to the Noble image. The
volume labels include the SHA-256 of the approval bytes. The rendered driver
probes the installed toolchain again before compilation.

## Reopen a legacy receipt-based stage

For the three-product replay at `1e81569c47842c07094f95b5d04009540b9365da`,
leave `projection.json` absent and use the original worker, image and receipts.

| Path under the root | Input |
| --- | --- |
| `readonly/Export` | Exact standalone export with the original Mac lock. |
| `lock/linux-mixer.lock` | Exact Linux projection from the offline lock phase, SHA-256 `5c019d97c6635ea0cc91478247da1af2e9ea5d636640be091b079df82bfbd039`. |
| `recipe/worker.py` | Unmodified three-product worker from the pinned revision. |
| `recipe/receipt.json` | `verification/receipts/managed-android-local-linux-pair25-20261120.json` from the pinned revision. |
| `recipe/retained-products.json` | `verification/receipts/managed-android-linux-retained-products-20261120.json` from the pinned revision. |
| `android-sdk`, `mirrors` | Same SDK and bare Git mirrors as the standalone replay. Verify both mirror commits during provisioning. |
| `python`, `glibc`, `lib64` | Same arm64 Python, x86-64 compatibility libraries and compatibility loader link as the standalone replay. |
| `outputs` | Operator-owned directory with mode `0700`. The adapter creates each operation's output under this directory. |

Use a fresh case-sensitive Docker local volume created under the exact
`layout.volume_name` with `layout.volume_labels`. Populate it offline with the
pinned archive setup from `prepare-toolchain.sh`. The deployment of the layout
uses a pre-provisioned volume and a pre-staged pinned Swift image on the same
dedicated daemon. Keep the volume immutable after provisioning. The labels
bind the stage, Linux lock and receipts. Inside the container the pinned driver
probes and hashes the toolchain and compares it with the projected lock before
compiling. The local admission checks selected Python and Android SDK files.

## Configure the private runner

Use the same host account for the runner and native artifact worker. The v1
Unix socket checks the connecting UID. Keep the runner directory and the
bundle's private parent outside the operator root, each with mode `0700`.
Keep the bundle destination absent before the build. The Pair25 guest runs as
`65534:65534`. The adapter creates a fresh `0777` output directory under the
private `outputs` root. For a live run, verify that the daemon's bind-mount
mapping lets the sealing account read the guest's `0600` files and remove the
owned output.

Create a recipe JSON manifest with `image`, `image_id`, `platform`,
`entrypoint`, and `arguments`. Use `Pair25Layout.read(stage).image` for `image`.
Use `PLATFORM`, `ENTRYPOINT`, and `list(ARGUMENTS)` from
`hosted/priv/development/linux_android_pair25_layout.py`.
Use the SHA-256 of the exact JSON bytes for both the runner's `recipe_sha256`
and the worker's `build_definition_sha256`.

Set `image_id` to the exact local `image inspect` ID on the selected daemon.
The runner requires both image and container inspect to report that same ID
and the pinned manifest descriptor. `layout.image_ids` lists the two admitted
IDs for the layout because Docker can report either the manifest or config digest.
The legacy `linux/arm64` manifest is
`sha256:3ad77b443f5f41d8c6c693659d9c951538dfeb79403e67cd40abca2501d4f191`.
Its config digest is
`sha256:3af9ff4bbeb3912a60bee99a537e4bd44e9010a8f933eefe29161e0f472464e9`.

Write an operator JSON config with mode `0600`. Set the following fields.

| Field | Value |
| --- | --- |
| `directory` | Absolute path to the private runner journal directory. |
| `pair25_root` | Absolute canonical path to the prepared operator root. Omit `inputs` and `outputs` for this layout. |
| `manifest`, `recipe_sha256` | Recipe JSON path and exact byte digest. |
| `store_id` | The store's 64-character lowercase hex ID, shared with the v1 client. |
| `docker`, `daemon_socket`, `daemon_id` | Absolute Docker CLI and Unix socket paths, and the selected daemon's ID. |
| `completions` | Map from each operation ID to its exact `identity`, absolute `bundle` path, and `inputs`. Use the same grant in the worker's `linux_artifact_imports`. |
| `command_timeout` | Optional Docker CLI deadline in seconds. The default is `0.2` and the maximum is `1`. |

Use `Pair25Layout.read(pair25_root).verified_inputs` for the grant's
`source_tree_sha256`, `linux_lock_sha256`, and `rendered_driver_sha256`. A
Pair25 start requires a matching registered operation identity. Use the
projected Linux lock digest in the operation specification.

## Initialize and serve

From the checkout, set `config` to the absolute path of the operator JSON.
Compute its byte digest and initialize the journals once.

```sh
config_sha256=$(python3 -B -c 'import hashlib, pathlib, sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' "$config")
python3 -B hosted/priv/development/linux_android_runner_cli.py initialize "$config" "$config_sha256"
python3 -B hosted/priv/development/linux_android_runner_cli.py serve "$config" "$config_sha256"
```

Connect the worker's v1 client to `directory/runner.sock`. On restart, use
`serve` with the original config, stage, daemon, volume, and journals.
The adapter compares the stage directory and file pins, volume identity, and
image environment with the stored configuration. It checks the stage and
volume again before creation and before an exact prepared start.

The fixed shell overlays the projected lock at `/project/mixer.lock` and
copies it into the fresh `/deliver` directory. After a successful exit, the
adapter checks the lock and the current readback, seals the three indexed
artifacts, and removes the exact container and output directory before
publishing the private bundle. The terminal result carries the current
readback digest. The recorded artifact digests from the standalone run are
historical observations.

## Run the fixture checks

Run the commands serially with `-B` and again with `-OB`. The CLI test uses the
real private runner and worker sockets with a fixture Docker executable. The
layout test exercises the projection fingerprint and runs the fixed build shell
with a stand-in worker. Live qualification of the maintained path requires the
separate integrated run.

```sh
python3 -B tests/integration/managed-android-local-linux-pair25/test_managed_layout.py -v
python3 -B hosted/scripts/test_linux_android_runner_cli.py -v
python3 -B hosted/scripts/test_linux_android_docker_adapter.py -v
```
