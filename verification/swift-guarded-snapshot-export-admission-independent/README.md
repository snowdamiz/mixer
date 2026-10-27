# Independent guarded snapshot admission review

This directory is owned by the independent admission reviewer. The producer's
active admission design and the separate active wire correction are unread until
root releases exact frozen inputs. This is requirements and control preparation,
not acceptance of either producer or an executable exporter.

The authority baseline is the 144-member accepted source at
`../swift-guarded-snapshot-export-preparation/inputs/accepted-source/vm`, tree
`9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb`.
The preparation packet is historical proposal only (639 members, seal file
SHA-256 `7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe`).
The selected adoption acceptance has SHA-256
`635696d0f95e7adf231095ca05a223d47f0353c563b63f60ab242e9cf7bc2697`.

`requirements.md` is the independently specified review checklist.
`admission_model.py` and `test_controls.py` are a small pure semantic model and
bounded host File controls. Their success does not validate production Rust,
measure its layouts, authorize an OTA release, or prove output custody.
`run_controls.py` records fresh commands, versions, input digests and output.

Only host Python controls and offline source/evidence review are authorized here.
No full compiler invocation, original one-shot wrapper, native/device runtime,
simulator, emulator, UI, capture, process inventory, publication, canonical edit,
commit or push is performed. No additional agent is used. Generated temporary
regular files are scoped to Python TemporaryDirectory and removed on exit.
