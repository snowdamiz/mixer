# Licensing

Mixer's core engine and OTA update system are open source under the MIT
License. Mixer's hosted services are proprietary. This file says which
directories are which. The
[licensing and revenue model](mixer-product-plan.md#267-licensing-and-revenue-model-november-23-2026)
explains why.

## MIT License

The MIT License in [`LICENSE`](LICENSE) covers every file outside the
proprietary directories below. It includes these directories:

| Path | Contents |
| --- | --- |
| `sdk/` | The Swift SDK, including `MixerCore`, `MixerUI`, `MixerSwiftUI`, `MixerApple`, `MixerAndroid`, `MixerGuest`, and `MixerCapabilities` |
| `native/` | The iOS and Android renderers and bridges |
| `vm/` and `runtime/` | The owned WebAssembly VM and its Swift runtime |
| `compiler/` and `cli/` | The guest compiler pipeline and the `mixer` CLI, including local builds and export |
| `updates/`, `runtime-identity/`, `activation/`, `capability-activation/`, `capabilities/`, `experimental-capability-runtime/`, and `native-sdk/` | The device updater, verification, recovery, activation, and capability system |
| `services/`, `contracts/`, and `release/` | The update and release protocol, its contracts, and the reference update server that you can self-host |
| The root build files, `docs/`, `scripts/`, `tests/`, `gates/`, `dogfood/`, and `verification/` | Build manifests, documentation, tooling, tests, and project records |

## Proprietary hosted services

These directories are not covered by the MIT License. Each one has its own
`LICENSE` file, and no license is granted for its contents.

| Path | Contents |
| --- | --- |
| `hosted/` | The hosted control plane for builds and releases |
| `hosted-worker-controller/` | Managed build worker control |
| `console/` | The hosted web console |
| `release-delivery-origin/` | Hosted update and artifact delivery |
| `website/` | The Mixer website and its brand assets |

You can build apps and ship updates without these directories. Local builds,
export, and self-hosted update delivery use only MIT code.

## Third-party components

Third-party components keep their own licenses, as listed in
[`THIRD_PARTY.yml`](THIRD_PARTY.yml). Build, test, and verification tools
such as OpenJDK, dpkg, GnuPG, and sharp are not linked into or shipped with
the MIT code.

## Trademarks

The Mixer name, the Flick fox, and the Mixer logos and wordmarks are
trademarks. The MIT License does not grant rights to use them.

## Open decisions

The owner has not yet set the contribution terms, such as a DCO or a CLA, or
the trademark policy. Until the contribution terms exist, outside
contributions are accepted only with the owner's approval.
