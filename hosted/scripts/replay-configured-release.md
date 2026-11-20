# Replay the L05 release with configured identity

Use the checkout containing this fixture and its parent
`6ba8a10248cc8f6db08faf6e218d9c9cc5d346e4`. Prepare the locked `MIX_ENV=test`
dependencies in `hosted/` before entering the namespace. The run uses Elixir
1.20.4 on OTP 29, PostgreSQL 16 or 17, OpenSSL, and the checked-in signed v3
protocol vector. Put `mix`, `erl`, `initdb`, `pg_ctl`, and `openssl` on the
unprivileged test user's path.

On Linux, install iproute2 with JSON output, util-linux with `unshare` and
`runuser`, and `sysctl`. The launcher needs permission to create network and PID
namespaces, mount their procfs, and configure loopback in the new namespace.
Run the following from `hosted/`.

```sh
sudo unshare --net --pid --fork --kill-child --mount-proc sh -eu -c '
  ip link set lo up
  ip address add 8.8.8.8/32 dev lo label lo:1
  sysctl -qw net.ipv4.ip_unprivileged_port_start=0
  exec runuser -u "$1" -- env PATH="$2" MIXER_RELEASE_PARENT_NETNS="$3" \
    ./scripts/replay-configured-release.sh
' sh "$(id -un)" "$PATH" "$(readlink /proc/self/ns/net)"
```

The test checks the namespace, loopback alias, and IPv4 and IPv6 routes before
starting the issuer. The maintained DNS and TLS helpers serve the synthetic
JWKS locally on ports 53 and 443. PostgreSQL uses port 5432 and Phoenix uses
47301. The runner owns the database, TLS files, and scratch directory. It stops
PostgreSQL before deleting scratch and prints the retained path if shutdown
cannot be confirmed.

Expect one passing test and the message
`Configured release replay completed in linux mode.` The first authenticated
request validates the release and triggers the cold configured DNS and JWKS
fetch. Publication and an identical retry leave one ledger row for the expected
principal, signed assignment, and sequence. The updater returns the exact
assignment and artifact bytes for the registered target.

For a macOS startup control with ports 5432 and 47301 available, run
`./scripts/replay-configured-release.sh --startup-only` from `hosted/`. It
checks signed artifact staging, ordinary runtime startup, PostgreSQL TLS and
role grants, HTTP 401 without a bearer, and empty delivery before publication.
The issuer and authenticated HTTP steps require the Linux run.

The default replay stages the signed artifact before API start using the
existing authorized PostgreSQL storage path.

## Publish and replay from the stock macOS CLI

Use the successor checkout on both machines. It composes the uploader
candidate `e608b6f644e6e06eb08656a9025a7e632f912e37` and the configured
fixture `1c8e25837b9b25755d3ea1ab591d7ec48f043b05` on the base above.

1. On macOS, build the stock binary before starting the guest fixture. Run
   this from the checkout root and keep the shell open during the replay.

   ```sh
   umask 077
   cli_build=$(mktemp -d /tmp/mixer-release-cli-build.XXXXXX)
   trap 'rm -rf -- "$cli_build"' EXIT
   swift build --package-path cli --scratch-path "$cli_build" --product mixer
   mixer_path="$(swift build --package-path cli --scratch-path "$cli_build" --show-bin-path)/mixer"
   shasum -a 256 "$mixer_path"
   ```

   Use Python 3.8 or later and a private SSH config for the owned guest. Set
   `HostName`, `User`, `Port`, and the known-hosts file for its verified host
   key. Use the fixture user as the SSH user, with the guest's existing
   authentication. Keep the config free of additional forwards and
   `RemoteCommand`. The guest SSH server must already permit local
   stream-local forwarding.

2. In the owned guest, prepare the locked dependencies and run this from
   `hosted/` as the fixture user. Include `psql` on its path.

   ```sh
   sudo unshare --net --pid --fork --kill-child --mount-proc sh -eu -c '
     ip link set lo up
     ip address add 8.8.8.8/32 dev lo label lo:1
     sysctl -qw net.ipv4.ip_unprivileged_port_start=0
     exec runuser -u "$1" -- env PATH="$2" MIXER_RELEASE_PARENT_NETNS="$3" \
       MIXER_RELEASE_PARENT_PIDNS="$4" ./scripts/replay-configured-release.sh --stock-cli
   ' sh "$(id -un)" "$PATH" "$(readlink /proc/self/ns/net)" "$(readlink /proc/self/ns/pid)"
   ```

3. Within 240 seconds of `Stock CLI ready`, run the client from the macOS
   checkout root. Set `guest_scratch` to the printed path and use an unused
   IPv4 loopback port on the Mac.

   ```sh
   python3 hosted/scripts/replay-configured-release-client.py \
     --mixer "$mixer_path" --ssh-config "$ssh_config" --guest "$guest_alias" \
     --guest-scratch "$guest_scratch" --port 47301
   ```

   The client reads the signed inputs and temporary bearer over SSH. It gives
   the bearer to the two CLI processes in their environments. The client
   reaps SSH and removes its scratch when it exits.

   Phoenix keeps its IPv4 loopback listener inside the guest namespace.
   The existing SSH session forwards the Mac's IPv4 loopback port to
   `cli.sock` in the private guest directory. The fixture closes that socket
   and stops the relay tasks after it receives the two successful receipts.

4. Require both the macOS success line and one passing guest test with
   `Configured release replay completed in stock-cli mode.` The guest checks
   zero initial artifacts, the restricted uploader login over TLS, cold
   configured DNS and JWKS, one artifact and upload audit and idempotency
   row, one validation and publication at the signed digest and sequence, and
   the exact updater offer and artifact bytes. Confirm the guest prints
   `Removed owned PostgreSQL and fixture scratch.` Exit the build shell to
   remove its scratch.

To check empty-store startup, uploader grants, and Unix-socket health on
macOS, run `./scripts/replay-configured-release.sh --startup-only --stock-cli`
from `hosted/` with `psql` and `curl` available. The authenticated stock CLI
replay needs the isolated guest and the macOS client.

## Deliver the signed FieldLog calculation updates to Android

Use the maintained FieldLog calculation test APK and its matching sealed
handoff. Verify all entries in the handoff's `SHA256SUMS` on the Mac. Use
the APK's installed loopback port for the device side of ADB reverse.

```sh
(cd "$handoff" && shasum -a 256 -c SHA256SUMS)
apk_port=$(cat "$handoff/delivery-android/Installed/port.txt")
```

1. Place `delivery-android` and its sibling `materials.sha256.json` in a
   private guest directory owned by the fixture user. Set `guest_delivery`
   to the absolute guest path ending in `/delivery-android`. Start the
   fixture from `hosted/` on the disposable Linux guest after preparing
   the locked dependencies as above.

   ```sh
   sudo unshare --net --pid --fork --kill-child --mount-proc sh -eu -c '
     ip link set lo up
     ip address add 8.8.8.8/32 dev lo label lo:1
     sysctl -qw net.ipv4.ip_unprivileged_port_start=0
     exec runuser -u "$1" -- env PATH="$2" MIXER_RELEASE_PARENT_NETNS="$3" \
       MIXER_RELEASE_PARENT_PIDNS="$4" ./scripts/replay-configured-release.sh --fieldlog "$5"
   ' sh "$(id -un)" "$PATH" "$(readlink /proc/self/ns/net)" "$(readlink /proc/self/ns/pid)" "$guest_delivery"
   ```

2. Wait for `FieldLog CLI ready phase=1`. On the Mac, set `guest_scratch`
   to the printed directory. Choose two free local ports, `public_port`
   for the emulator and `cli_port` for stock CLI invocations. Keep this SSH
   command running in its own Mac terminal through phase 3. Use the same
   private SSH configuration and guest alias as the stock CLI replay.

   ```sh
   ssh -F "$ssh_config" -NT -o BatchMode=yes -o StrictHostKeyChecking=yes \
     -o UpdateHostKeys=no -o ExitOnForwardFailure=yes -o ControlMaster=no \
     -o ControlPath=none -o ForkAfterAuthentication=no -o ForwardAgent=no \
     -L "127.0.0.1:$public_port:$guest_scratch/cli.sock" -- "$guest_alias"
   ```

   In the Mac terminal that owns the emulator, use its private ADB server
   port and exact serial. Verify the forward before adding the mapping.

   ```sh
   curl --noproxy '*' --fail --max-time 5 "http://127.0.0.1:$public_port/health/live"
   adb -P "$adb_port" -s "$serial" reverse "tcp:$apk_port" "tcp:$public_port"
   ```

3. For each `phase` (1, 2, then 3), wait for the matching
   `FieldLog CLI ready` line. Run this command from the Mac checkout root
   within 240 seconds. The client runs the same stock CLI command twice per phase.
   The guest stays on the same Phoenix and PostgreSQL boot throughout.

   ```sh
   python3 -B hosted/scripts/replay-configured-release-client.py \
     --mixer "$mixer_path" --ssh-config "$ssh_config" --guest "$guest_alias" \
     --guest-scratch "$guest_scratch" --port "$cli_port" --phase "$phase"
   ```

   Phases 1 and 2 use stock `mixer update publish`, which uploads and
   validates each distinct package. Phase 3 uses stock
   `mixer update rollback` with the signed sequence-3 assignment. Phoenix
   requires the rollback digest to have a validation receipt and a
   previous publication in the same channel and runtime. The baseline
   publication supplies both.

4. Wait for `FieldLog Android ready phase=N` before triggering the app's
   checklist update. The line follows the ledger and byte-exact offer and
   artifact checks. Confirm the presentation and gather live and retired
   recovery readbacks. Expect percentages of 0, 100, and 0 for phases 1
   and 3, and 33, 100, and 0 for phase 2. Use the signed artifact digest
   printed on the ready line and the SHA-256 of `baseline.wasm` for phases
   1 and 3 or `reviewed.wasm` for phase 2.

   ```sh
   python3 -B tests/integration/fieldlog-task-calculation/android-readback.py \
     "$live" --retired "$retired" --runtime "$runtime" --installation "$installation" \
     --sequence "$phase" --artifact "$digest" --payload "$payload_sha"
   ```

   After that phase passes, acknowledge it from a separate shell on the
   guest as the fixture user within 300 seconds. Set `guest_scratch` and
   `phase` there to the values for this run.

   ```sh
   ack="$guest_scratch/phase-$phase/android-ack"
   (umask 077 && printf '%s\n' "$phase" > "$ack.tmp" && mv "$ack.tmp" "$ack")
   ```

5. After phase 3, require a passing guest test and
   `Removed owned PostgreSQL and fixture scratch.` Close the owned Mac
   SSH forward and remove the exact ADB reverse mapping before the cold
   offline reopen. Verify that sequence 3 and the unchanged workspace
   survive the reopen and retire again.

   ```sh
   adb -P "$adb_port" -s "$serial" reverse --remove "tcp:$apk_port"
   ```

### Run the macOS host controls

From `hosted/`, use free ports 5432 and 47301. The first command generates
ephemeral Android-shaped inputs in fixture scratch. The second reads the
operator's sealed handoff in place. Both use the production release handlers
from the verified-identity boundary, restricted PostgreSQL roles, and the
running Phoenix HTTP delivery routes.

```sh
./scripts/replay-configured-release.sh --fieldlog-control
./scripts/replay-configured-release.sh --startup-only --fieldlog "$handoff/delivery-android"
```

Expect one passing test per command. Each starts with an empty store, rejects
rollback of a validated but unpublished baseline, and checks the two
publications and rollback with exact retries. Each checks the stored
assignment, manifest, payload, and anonymous response bytes at every phase.
