# Identity production-network next scope

The next useful source slice is a **targeted remote Linux collector for the two existing network cases**. Ordinary Phoenix CI cannot qualify them as currently configured: both modules require Linux **and** `MIXER_ISOLATED_NETNS=1`, and the committed workflow never creates that namespace or supplies the flag. This is a deliberate skip, not a newly observed product failure.

This packet is source-only assessment. It changes no product source, workflow, tracker or credential and runs no compiler, test, listener, namespace helper, process probe, native runtime or CI dispatch. The main result is [assessment.json](assessment.json); [the input manifest](inputs/input-manifest.json) binds its source and retained evidence.

## Bound source and existing result

The product basis is commit `9e860ea12074ca31bef4087ce34177a03f295dd8`, tree `89ece6e95e4b12978a9c33c85e07ec448fd717b4`. The committed hosted subtree has 177 ordinary files; its bound manifest is separate from the two shared fixtures in the ordinary collector's 179-input receipt. This assessment's hosted manifest digest is `023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e` under the definition stored in the input manifest.

The retained owner-drain terminal receipt reports six Engine jobs/64 steps, Phoenix 697 passing tests and two existing skips, nine lifecycle methods and five HTTP/2 methods/seven wire cases. The assessment reads that post-delivery receipt offline; it does not refresh remote state. The two skipped methods are:

- `KeyOwnerLinuxNetworkTest`: production resolver/classifier and real public-peer pinning under rebinding, with a zero-connection loopback sink.
- `StartupLinuxNetworkTest`: actual configured Application/Endpoint/Repo and public adapter cold DNS/TLS signed-token admission, empty restart/old-lease rejection and active-flight shutdown.

The ordinary K03 mixed/special-address DNS matrix and ordinary disabled/startup-supervision tests are already separate checks. Their passes and the recent KOL08/KOL09 passes do not eliminate these two network skips.

The workflow snapshot is **`git show HEAD:.github/workflows/hosted.yml`**. The live workflow contains protected UnitA additions and differs; it was preserved and never treated as the committed CI contract. Live W14/G22/plan projections are explicitly labelled live input, while selected product/test/fixture source comes from Git. A first snapshot-authoring command incorrectly requested an uncommitted post-delivery receipt from the delivery commit; its harmless failure is preserved in `inputs/authoring-failure-1.json`, and those receipt bytes are now explicitly classified as retained offline evidence.

## Historical evidence and exact limitation

The October24 corrected producer isolated-Linux run reports 95 passing tests and no skips. The earlier independent isolated-Linux review reports 87 passing normal tests. Their namespace used `--network none`, scoped `NET_ADMIN`, an owned `lo:1` address of `8.8.8.8`, synthetic DNS/CA/TLS and a PostgreSQL companion sharing only that namespace. The retained records include the public peer, exactly two initial DNS queries, zero forbidden-sink connections, cold startup admission and closure of all three startup connections.

The actual image-inspect file identifies **Linux ARM64, Elixir1.20.4/OTP29.1.1 and PostgreSQL15.19**, with OpenSSL3.0.13 in the tool output. It is not an AMD64/PostgreSQL16 receipt. Those historical image references and broad scripts must not be transplanted blindly: the runner also depends on a deleted scratch path from `state.json`, local Home Hex/rebar inputs and old dependencies. Current pins and the supervisor-death repair require current-source evidence.

## Smallest concrete proposal

Freeze a four-file source candidate, then independently review it before root selects any execution:

| New file | Bounded purpose |
| --- | --- |
| `docs/hosted-identity-production-network-ci-contract.md` | Exact source/tool/image roots, two-case semantics, isolation, bounds, evidence and cleanup contract. |
| `hosted/scripts/test-identity-network.py` | Remote-only narrow orchestration. A fixed audited Elixir expression configures the owned namespace; no reusable namespace helper or held custom custody wrapper. |
| `hosted/scripts/test_identity_network_collector.py` | Meaningful orchestration controls for absent isolation, wrong source/image identity, skipped/missing methods or artifacts and failed cleanup. These are not proof of real namespace behavior. |
| `.github/workflows/identity-network.yml` | One standalone job, preserving the protected dirty hosted workflow and existing ordinary collector. |

The exact future test roots are only:

```text
mix test --warnings-as-errors --seed 0 --trace \
  test/mixer_hosted/identity/key_owner_linux_network_test.exs \
  test/mixer_hosted/identity/startup_linux_network_test.exs
```

Retain the current `mix test --no-start` alias and existing tests, support fixtures, production DNS classifier, destination port443, CA/hostname verification and assertions. The startup fixture needs only a synthetic `mixer_startup_test` database; it applies all ten current migrations. There is no reason to call the broad collector, create customer authorization fixtures or run UnitA/browser storage. Whole source compilation remains bound to the exact delivered commit; dirty local source must never be substituted.

The unfilled prerequisite is the target runtime closure: freeze official matching **AMD64 immutable image digests** for Elixir1.20.4/OTP29.1.1 and PostgreSQL16 (or explicitly choose a different actual scope), plus the resolved current lock and loaded module/tool identities. No image resolution, capability probe, download or run occurred here. Setup may fetch locked dependencies before runtime isolation; the tests must run in an owned network-none namespace without published ports or external downloads. The flag is set only inside that verified namespace. No host routing change, localhost policy bypass or network fallback is acceptable.

Actual acceptance must include both methods passing with zero skips, raw logs and the two expected JSON observations, exact source/dependency/image/tool bindings, semantic sink/startup/lifecycle assertions, and successful owned-container/PostgreSQL/scratch/key cleanup. Preserve failed or partial evidence on all terminal paths. A same-commit ordinary Phoenix packaged-release exclusion receipt remains a separate companion requirement; compiling test support in the namespace does not establish production export exclusion.

## Boundaries

The seven unresolved local groups `20745`, `20770`, `20780`, `20817`, `20842`, `20851`, `20866` remain held after `EPERM`; no probe, signal, retry, actor/API substitution or delegated attempt is proposed. The failed local custody protocol remains failed. Callback UnitA, broad PostgreSQL16 replay, hosted catalog inspector, authority driver, Worker transportV2 and broad local hosted harness remain held. Native UI/capture/device/simulator/emulator runtime use remains paused.

A new targeted remote product lane can qualify the narrow current network cases independently of those local holds. It cannot accept the held local protocol, nor certify a real identity provider, provider rotation behavior, Neon TLS/Cloudflare operation, HTTP/browser login, published FieldLog, devices or GA. W14 remains `in_progress`; G22 remains `planned` with no reviewer. Their public end-to-end commercial/authentication acceptance remains unchanged.

Source-contract and collector/control authoring can proceed in that bounded lane. Runtime qualification requires the exact reviewed source contract, image closure and root selection; unchanged ordinary CI and historical receipts are insufficient. This packet requests no user permission and performs no activation.
