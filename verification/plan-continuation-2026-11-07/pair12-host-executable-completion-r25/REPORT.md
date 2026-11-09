# Pair12 executable host completion R25

**PASS within Java host scope.** Both exact closures compile, both focused entry points execute and pass, and complete ordinary owner-host A/B execute and pass. There is no remaining Java compilation or runtime failure. Product bytes, all test assertions, rosters, callback obligations, and projection metadata remained unchanged. No stub correction was needed.

The tested source is `/Users/andreyyurlov/.t3/userdata/mixer-pair12-r23-9pwvhv7n/source`. The packet is `../pair12-external-frame-source-integration-r23`. `run.py` reproduces the original runner's explicit source ordering and Java commands, imports its unchanged bytecode/matrix validators, and uses its existing pinned command custodian. No new controller was introduced. The prior A-r21 and full-B-r26 recipes are summarized in `runner-patterns.json`.

## Executed members and raw results

| Entry point | Closure | Runtime result |
| --- | --- | --- |
| `ExternalFrameSourceV2HostTests` | A | 24 checks pass |
| `ExternalFrameGateV2HostTests` | B, real renderer | 6 checks pass |
| `NativeOwnerV2HostTests` | full A | 231 cases, 1,253 assertions pass |
| `NativeOwnerV2ConcreteHostTests` | full B | 14,692 checks pass |

Exact stdout, without changing the original member labels:

```text
PASS external-source owner lifecycle checks=24; controlled framework/JNI leaves only
PASS external-gate real renderer checks=6; controlled platform leaves; 189-case matrix unrun
PASS actual owner/core/coordinator/observer closure A cases=231 assertions=1253; renderer leaf only, native runtime pending
PASS concrete actual16 host checks=14692; platform/JNI leaves, native runtime pending
```

The focused Gate output describes that entry point alone. The subsequent complete B execution validated **1,323 cases = 189 distinct callback bindings × seven cases**, with all cases hit, all **15 helper obligations** final, and `missing=[]`. `host-B-1/barrier-cases.json`, `helper-boundaries.jsonl`, and `compile-B-1/barrier-preflight.json` contain actual runtime and compiled binding evidence. Original mutation, cleanup and unknown-state contracts were retained. The historical string `actual16` is unchanged stdout; the exact current B compilation roster contains 18 production Java members.

## Compilation and environment

Homebrew JDK/javac/javap **25.0.4.1**, Java output targeting **`--release 17`**, `-Xlint:all -Werror -proc:none`, heap 256 MiB, and **`ActiveProcessorCount=2`** throughout. Java commands ran sequentially, below the two-job concurrency ceiling. There was one A compile and one B compile; no retry or materially changed compile was needed.

| Closure | Product sources | Explicit substitutes | Test/support sources | Total Java inputs | Compiled classes |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 13 | 76 | 3 | 92 | 279 |
| B | 18 | 86 | 4 | 108 | 356 |

A includes the previously omitted real `NativeEnvironmentPlatformV2.java`. Exact product and substitute ordering matches packet `ROSTERS.json`; test membership matches it, using the original runner's support-before-main compile order. Full members and command arguments are in each `compile-*/roster.json`, `source-map.json`, and `commands.json`. A's support members are `OwnerHostProbe` and `ExternalFrameSourceV2HostTests`; B's are `ConcreteHostProbe`, `NativeAndroidFixtureHostTests`, and `ExternalFrameGateV2HostTests`. Both closures use the real frozen descriptor `verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json`, SHA256 `1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3`.

The two compile input-map SHA256s are:

```text
A 0b4291ca62e6626900b79b07ce17a06ead9f0954795d9ff59fee74cc4bdeda2a
B 87a9973476db89bb023413caa4295d719339c901d25c59ef55ef5c1bd08bfb3f
```

These identify the actual frozen source maps, including non-Java validation inputs. `postflight.json` confirms all 99 A and 115 B frozen entries remained identical, and all 279/356 compiled class bytes remained identical. It records the four product-file hashes and their exact equality to R23 afterimages. `focused-test-identities.json` confirms both focused tests are byte-identical to the delivery packet. No Git query was used to invent a current revision; actual bytes are authoritative for this run.

## Raw evidence and cleanup

Each of `compile-A-1`, `focused-A-1`, `compile-B-1`, `focused-B-1`, `host-A-1`, and `host-B-1` contains `commands.json`, exact `.stdout`/`.stderr`, and a receipt. All **14 Java-tool commands** exited zero and recorded reaped child, both EOFs, owned-group absence and terminal custody. All command scratch directories were removed. There is no new UNKNOWN or held command. Compiled classes are intentionally retained in fresh userdata `/Users/andreyyurlov/.t3/userdata/mixer-pair12-r25-swedn8rj` for reproduction, and frozen inputs/raw results are retained here.

The campaign began at 20:52:28 UTC; all runtime work, cleanup and postflight checks were complete at 21:00:00 UTC, approximately 451.5 seconds into the 600-second active budget. Full B's recorded execution/validation took 267.14 seconds with a 300-second process timeout. No expired deadline was reused. `summary.json` has exact measured receipts. No Swift build/test, device/ADB operation, Git mutation, delegation, publication, canonical file write, or stub change occurred.

An auxiliary metadata comparison initially compared ordered test lists and failed because packet display order is main-before-support while the canonical compile order is support-before-main. The membership check then passed; compilation order and every Java source/assertion stayed unchanged. This was a bookkeeping diagnostic, not a hidden Java test failure.

## Remaining root work and scope

Root reported CI repair `4b0ee35cf`. Its refreshed `adopt_envelope.py`, `caller-inputs.json`, and runtime-seal preimages are separate from this fixed projection. Root still needs to reconcile exactly those three stale packet preimages. This task did not refresh isolated metadata or claim acceptance of changed bytes.

The app teardown/reply race and actual native owner/core/coordinator cleanup remain root-owned. This host evidence does not establish physical-device, native, immutable published-package, release or GA acceptance. No remaining Java-host failure was observed.

Scope deviation: the initial discovery included an unnecessarily broad `rg --files` filename search under `verification/plan-continuation-2026-11-07`, limited in displayed output with `head -60`. No held file contents were opened by that search, but directory enumeration of every held namespace cannot be excluded. No historical held process was probed, signalled, waited on, retried or cleaned. Subsequent reads were confined to the exact supplied packet/patterns, projection and owned output.
