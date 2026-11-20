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

The fixture stages the signed artifact before API start using the existing
authorized PostgreSQL storage path. The stock CLI upload still depends on
normal runtime configuration for the CustomerArtifacts uploader.
