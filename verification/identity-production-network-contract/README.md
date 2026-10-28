# Identity production-network CI source contract

This packet prepares one concrete remote-only lane for independent root review. **It authorizes neither implementation nor execution.** The selected platform is Linux AMD64, HexPM Elixir1.20.4/OTP29.1.1 on Ubuntu Noble, and official PostgreSQL16.15 Bookworm. The main contract is [contract.json](contract.json); frozen public registry records and source/checksum metadata are under [inputs](inputs/).

The exact product basis is `9e860ea12074ca31bef4087ce34177a03f295dd8`, tree `89ece6e95e4b12978a9c33c85e07ec448fd717b4`, with all177 committed hosted files and the unchanged current lock. The proposed collector must match each product path against this frozen manifest and materialize delivered Git blobs only. Dirty UnitA/workflow files, user Home caches and untracked code are excluded. A product change requires a new root-reviewed freeze.

## Verified image and tool roots

| Selected image | AMD64 immutable manifest |
| --- | --- |
| HexPM `1.20.4-erlang-29.1.1-ubuntu-noble-20260911` | `sha256:3571d320ec0656c38c76b4c362a8e0c0fd6f9b58cec6448a08e43a82940d4e43` |
| Official PostgreSQL `16.15-bookworm` | `sha256:cf5d353f55240ecc2f811827a15c7d1f2d562f08019b49dca12b5a59f4ab5962` |

Direct official registry requests retrieved each index, AMD64 child manifest and JSON image configuration. Their content hashes and declared `linux/amd64` identity were verified without image layers or execution. PostgreSQL config records `PG_MAJOR=16`, `PG_VERSION=16.15-1.pgdg12+2`. The [HexPM image page](https://hub.docker.com/layers/hexpm/elixir/1.20.4-erlang-29.1.1-ubuntu-noble-20260911/images/sha256-3571d320ec0656c38c76b4c362a8e0c0fd6f9b58cec6448a08e43a82940d4e43) and [live official PostgreSQL repo-info](https://raw.githubusercontent.com/docker-library/repo-info/master/repos/postgres/remote/16.15-bookworm.md) support these roots; exact retrieved bytes are retained locally because tags/pages can move.

The earlier assessment overgeneralized historical ARM64 execution into an architecture restriction on the HexPM digest. **Correction:** `52ec0f...` is the multi-platform index containing the selected AMD64 child. Historical runtime evidence still covers ARM64 only. Cached web PostgreSQL metadata showed older child `e92e17...`; direct live registry and direct repo-info agree on selected `cf5d353...`. The contract pins the child, never a tag or cached digest. The predecessor packet remains unchanged.

Official Hex/Rebar checksum CSVs and pinned Elixir1.20.4 task source provide exact bootstrap URLs/checksums for Hex2.5.1 (Elixir1.20.0/OTP29 archive) and Rebar3.28.0 (Elixir1.18.4/OTP29 distribution). See [bootstrap-selection.json](inputs/primary/bootstrap-selection.json). Artifact bytes were not downloaded. Future preparation must verify SHA512 and execute version/compatibility checks inside the selected image. These distribution labels do not change product Elixir1.20.4 and do not prove binary compatibility in advance.

No Dockerfile is proposed: both matching prebuilt AMD64 images exist. Current committed Ubuntu24/setup-beam pins and the retained9e860ea Elixir/PG16.15 logs provide comparison evidence; the new lane obtains BEAM from its exact container image, so no host/ARM compiled dependency, NIF or toolchain is copied.

## Bounded source proposal

The next implementation candidate has four new canonical files:

- `docs/hosted-identity-production-network-ci-contract.md`
- `hosted/scripts/test-identity-network.py`
- `hosted/scripts/test_identity_network_collector.py`
- `.github/workflows/identity-network.yml`

A coordinated inventory-only `THIRD_PARTY.yml` addition must preserve historical ARM64 entries and record the selected AMD64 images and exact bootstrap verification tools. It changes no package requirement or lock. Existing hosted workflow, broad collector, tests/support fixtures and production source remain byte-identical. Root owns canonical coordination, integration, pushes and ensuing CI selection.

The workflow is one standalone Ubuntu24 job with read-only repository permission, pinned checkout/upload actions, no secrets, no schedule/dispatch/deployment, no console/UnitA steps and `cancel-in-progress:false`. Sparse checkout retains hosted source, its new workflow and contract. The collector uses the exact177path product manifest, not broad checkout copying. All command/image/action/source identities and outputs enter its receipt.

## Isolation and execution

The networked **prepare** container uses the selected Elixir child, fresh tmpfs workspace and empty owned bootstrap homes. It installs only the checksum-bound bootstrap tools, runs `mix deps.get --check-locked`, and exports a bounded safe archive of exact dependency/tool sources. It compiles no dependencies or product code. Remove it before creating the test container.

The **test** container uses the same child with a read-only root, bounded tmpfs workspaces, `--network none`, dropped capabilities and only `NET_ADMIN`/`NET_BIND_SERVICE`. Docker documents that [none networking creates only loopback](https://docs.docker.com/engine/network/drivers/none/). The future collector must observe that exact mode, no external interface/default route and a namespace distinct from the host before enabling the fixture flag. A fixed OTP socket ioctl assigns `8.8.8.8` to owned `lo:1`; it changes no host network.

The **PostgreSQL** companion joins only the exact test container namespace, uses the immutable PG16.15 image, tmpfs data/socket/temp paths and loopback5432/UTC. It creates only application database `mixer_startup_test` in addition to built-in administrative/template databases. The existing StartupFixture applies all ten current migrations there. No customer fixture databases, broad PostgreSQL16 replay, browser callback storage or UnitA runner is involved.

Inside network-none, compile dependency sources and product code with the current lock and warnings-as-errors. Then run only these existing roots, with current `test --no-start` alias, seed0, detailed CLI trace and a fixed collector-owned evidence formatter:

```text
test/mixer_hosted/identity/key_owner_linux_network_test.exs
test/mixer_hosted/identity/startup_linux_network_test.exs
```

The formatter is materialized from a reviewed collector literal outside product source. It adds no ExUnit.Case, override, constructor call, tag/filter or mock. It records exactly two method completions and actual loaded module/application/VM identities through the public ExUnit formatter interface, alongside the unchanged CLI output. No skips, filters, dry-run, partitions, repetitions, alternate exit status or implicit retry are accepted. Mix documents that [`--trace` disables its per-test timeout](https://mix.hexdocs.pm/Mix.Tasks.Test.html); the contract therefore fixes a separate hard180second compile/test-phase bound.

The two final semantic files must match passed method events: production public-peer pinning, exactly two initial DNS queries, one public connection, zero forbidden-sink connections and private-answer denial; then actual configured startup, DNS53/TLS443 with synthetic CA/hostname verification, cold signed-token admission, empty restart/old-lease rejection and three closed connections after active-fetch shutdown. Evidence paths start empty and cannot reuse earlier JSON. The K03 DNS stub intentionally uses an ephemeral loopback port; the startup DNS stub uses53.

Production constructors, classifier and TLS policy remain unchanged. The startup fixture supplies synthetic roots to the existing pure configuration constructor; it does not select a production environment CA/module or loopback bypass. A separate accepted ordinary remote production-release exclusion receipt remains required, with explicit root-approved source reuse if the9e860ea product bytes are unchanged. These two tests alone cannot prove packaged production fixture exclusion.

## Bounds, cleanup and acceptance

The structured contract fixes a15minute workflow,660second aggregate collector deadline including30seconds for cleanup, bounded120second image pulls,60second bootstrap,120second dependency fetch and180second offline compile/two-test phase. Prepare/test each have2GiB memory,2CPUs and256PIDs; PG has1GiB/1CPU/128PIDs. At most two containers coexist and only three may be created per attempt. Tmpfs, raw logs, archive and artifact sizes have explicit caps. Overflow, timeout, OOM, tool absence or identity mismatch fails without raising caps or choosing another image.

Persist exact container IDs, images and run labels before further operations. Teardown operates only on those retained identities: stop PG then test with a2second grace, record terminal state, remove those exact containers/volumes and verify their absence. No global enumeration, prune, PID query, killpg or denied-identity retry is permitted. A timed-out create without a retained CID remains unresolved; runner disposal is not an absence receipt. Synthetic keys are deleted rather than uploaded.

SIGINT/SIGTERM stops new work and initiates bounded owned cleanup. Explicit always cleanup/upload steps attempt finalization, but [GitHub can forcibly terminate cancelled steps](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-cancellation). Hard cancellation or host loss can prevent cleanup/artifact completion. Such a run remains unqualified. Forced container teardown is recorded separately from the successful test's graceful lifecycle assertions.

Retain complete below-cap command outputs, source/lock/dependency/tool/image manifests, safe archives, namespace/resource records, actual test events, both semantic JSONs and cleanup/failure evidence in one14day artifact. Overflow is explicitly incomplete. Root must download and independently bind accepted/failed evidence before expiration. An upload or green job is not itself acceptance. Unchanged TLSFixture discards successful OpenSSL child stdout: this scope records executable hash/version and parent test outputs; it does not claim nine individually observed child-command outputs, a syscall trace or the held custom custody protocol.

## Pending and held boundaries

This packet performs read-only official metadata/source research and offline source binding only. No Docker/native/compiler/test/version/process probe, image layer, bootstrap binary, installation, pull, CI dispatch, canonical edit or credential change occurred. Actual AMD64 CLI/tool compatibility, Docker permissions/capabilities and the two current test results remain unobserved. Missing OpenSSL or bootstrap compatibility must fail; no install/fallback is preauthorized.

The seven local groups20745/20770/20780/20817/20842/20851/20866 remain held and untouched. Local custody/controller/runtime, callback UnitA, broad PG16 replay, hosted catalog inspector, authority driver, Worker transportV2 and broad local hosted harness stay held. Native UI/capture/device/simulator/emulator runtime remains paused. No remote result can accept those lanes or infer real-provider, Neon/Cloudflare, browser/customer, published FieldLog, W14/G22 or GA completion.

Root independent review and explicit source selection are required before implementation; a separate root execution selection is required before any CI activation. This packet asks no user permission and does not open either step.
