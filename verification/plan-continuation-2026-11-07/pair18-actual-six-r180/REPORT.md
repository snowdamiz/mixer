Pair18 actual local integration: PASS.

Source116: `306221cc4d05bfd448deb5674162d1a79469ded6c047325eaf80df49c237187f`; profile `mixer.android-source-pair.18`.
Fresh local snapshot `983e5f16f6e4c57aa774f6cbcb18cccb8a729583` / tree `5e23c15f4676e05833adaeb0cee28a0d9d6688ec`. This is not remote main.
All 632 selected canonical/snapshot inputs and all 116 owning inputs match before and after.

| Producer | Original | Relocated | Exported |
| --- | --- | --- | --- |
| Debug | PASS | PASS | PASS |
| Release | PASS | PASS | PASS |

Each consumer compiled all 21 Java inputs with Java17 strict warnings, Android SDK37, D8 min-api28, javap member inventory and actual dexdump class checks.
Each producer refused SDK, adapter, descriptor, extra-Java, profile and missing-lock mutations through both real CLI and driver invocations before staging.
Exactly two producer builds, six javac/D8 pipelines, twelve refusal cases, 79 terminal command records. No harness correction used.
Owned integration scratch was removed. Fresh input snapshot is retained for root review/delivery. No device or held-resource operations occurred.
Runtime, native/device, hosted, immutable published-package, API28 linkage and GA qualification remain pending.
