Prepared and frozen: 21 exact application paths for mixer.android-source-pair.13.

- source115: `f318d5d91fd9381939a8a193c007f7b3fcc2b4f0be781adb0ff3f951e7f2fb54` (predecessor source114 `5814b0dab60dfe3fdbce2791644499fc0362072a99bf9034c7f28ea266577608`).
- SDK24 unchanged: `dd67ffdb0458b2a546dcac8660e039364668f15c3a270ab417db7e7c2181ce47`.
- adapter27: `abbffb821c9d7b5acc8123b7bbd452d07afa7dbfff2693bb316ad73cc3249473`; official copied Java roster21 includes AndroidUINativeSurface.java.
- Application map SHA256: `661d414feff2d8b8dad003a3b933544e08494f1ecf768906a62ed58757f56371`.
- Patch SHA256: `1ff17cbdd5f3b37eab0470acbf9de60dbae17470bd023714faa87357b4bed5e8`.

Normal and actual `python -O` controls: 114 tests per mode passed, plus both installed-entry guards. Actual unittest discovery executed all16 combined controls in both modes. Commands/results and the preserved initial policy projection omission and explicit rebind-roster failure are in test-results.json and the named raw logs. One changed-source roster expectation was corrected; SDK/default/wire, historical Pair11/12 transitions and caller strictness remain intact. Active test time 65.573s (240s limit), one control subprocess at a time. Own userdata projection removed in 0.037s (30s limit).

Root independently confirmed all21 preimages and afterimages and has announced application plus actual-six. This lane made no canonical writes. Root-owned native test sources, runner, and workflow were untouched. The current live workflow snapshot passed installed Swift-job admission; adding the separate android-owner-host step needs no copied job/transition/seal refresh while the extracted ordinary Swift job remains byte-identical to source113-inspection-caller-r3/swift-job.yml (`948c97e43e170197a3de4db16d239c5a99b513ae27d8dd317e56da372d7e0223`).

Source115 compiler, native, actual-six, runtime and GA qualification remain false/pending; root's R49 native and R50 source-review passes are separate evidence. No Swift package/full-host/189-matrix/actual-six/native build or device work ran here. No commits/pushes or hold access.

Application reference (root already owns the announced one-use application; do not repeat it):

```sh
python3 -B verification/plan-continuation-2026-11-07/public-surface-profile13-compose-r51/application.py --root /Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4 before
python3 -B verification/plan-continuation-2026-11-07/public-surface-profile13-compose-r51/application.py --root /Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4 apply
python3 -B verification/plan-continuation-2026-11-07/public-surface-profile13-compose-r51/application.py --root /Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4 after
python3 -B verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/adopt_envelope.py verify --workflow-installed
python3 -B -O verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/adopt_envelope.py verify --workflow-installed
```
