# FieldLog ordinary signed Android display witness

This patch applies to the FieldLog tree behind the installed
`ac30526259ae8b7a23891c2ddbb98ba5acda1061ff520456ccba52035a816729` APK.
It changes only `PublicActivity.java`. The ordinary Entry Commit and checklist
use the same `GuestFrame` and JNI display-witness route.

The host registers a one-shot frame commit callback at pre-draw and records
the F10 two-color marker in the hardware draw. It calls the existing display
witness after PixelCopy samples both exact colors from the dialog window and
the frame, attachment, owner, and marker bounds still match. Refresh, Done,
detach, pause, and focus loss invalidate pending evidence. A bounded retry
may schedule a new drawing attempt. The signed witness runs on hardware
renderers from API 29 and the Pair25 fixture keeps its API 36 minimum.

## Replay

From this Mixer checkout, run:

```sh
bash tests/integration/fieldlog-ordinary-frame-commit/replay.sh
```

Set `MIXER_JDK` or `ANDROID_HOME` to override the script's toolchain paths.
The replay decodes and verifies the exact patch before application. It needs the pinned Mixer Git objects, access to the public FieldLog
Git repository, and the installed API 36 platform jar. It reconstructs the
installed tree with the maintained recipe from `2fbba61cb168` and the pinned
Settings patches from `73717993d6ee`. The public Android patch uses
zero-context hunks and produces the same installed tree as the context-bearing
patch in the Settings build receipt. Both variants were replayed.

| Source | Identity |
| --- | --- |
| Pair25 SDK commit | `857e4b4aa7a32cda368257b2be1a63e77106bed8` |
| Installed FieldLog tree | `9c2d665c31a6f3f2bfabc42bdfffaf72c6661731` |
| Successor FieldLog tree | `807c198cfe800e1b3be7c94795240b29bdd9e3d5` |
| Installed `PublicActivity.java` SHA-256 | `15fc9d70092411954f98c69a670f7c6aa7c88b2e5feb0e58eb08b546a18713ad` |
| Corrected `PublicActivity.java` SHA-256 | `0df1d83604d8738749e7aae93e469446ad2985dd644094771dcdeed6ef396ef1` |
| Patch SHA-256 | `75f5559e1ad1b91dc669860fb1edc21a8e24bd430d3f1e1ce119f8b246a62161` |
| Decoded tracked F10 navigation patch SHA-256 | `47626cacfdff19297baf4d891a0f46918d6050c1783cf94ab26c6794a6efbc99` |

The replay executes the production Java methods against deterministic Android
callback doubles. The baseline calls the display witness after drawing and
receiving two animation callbacks without committing a buffer. The successor
waits for exact readback, refuses failed, old, moved, paused, and retired
samples, keeps the existing Commit and Done routes, and clears markers and
callbacks. It also checks API 28 refusal, API 29 hardware acceptance, and
software-renderer refusal. The replay compiles the full production Java with
javac 25.0.4.1 against the API 36 jar using `--release 17` and strict lint,
then reverses the patch to the exact original tree.

The signed API 36 replay reached durable `first_screen` before Commit.
Commit wrote one outbox event and retained seven JPEGs. Done retired the
same owner, and an offline new process read the same journal and workspace
bytes. The checklist shares this Java path. The installed replay exercised
Entry Commit. [Installed replay receipt](../../../verification/receipts/l07-fieldlog-ordinary-frame-commit-api36-807c198c.json)
