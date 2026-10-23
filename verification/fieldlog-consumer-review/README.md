# Independent FieldLog consumer review

Run `python3 verification/fieldlog-consumer-review/verify.py` from Mixer. The runner
exports committed FieldLog source into a private temporary directory, resolves its
public revision-pinned Mixer dependency through SwiftPM, runs original tests, adds
only the independent test file and runs debug/release/Thread Sanitizer checks. It
never edits the separate app implementation, runs a device command or publishes.

Reviewed FieldLog `dd68d3dbd61be15860282d79f710a8f58b001e92`, tree
`87ee9c1ef6d56730fd6ea2307e54a3b6fde79af4`. Its implementation is unchanged from
`d51adf50de7e20549e87062e4569609342cdfe25`; later commits contain evidence only.
The exact `git archive --format=tar` SHA256 is
`9767be913de2d0332b08e270e3ea717e8c9508dbd4dbdb1778685a06cd153991`.
The full exported file manifest digest is
`f680dfb63b7e4a69f3cf9cc49d4eccdebbd8117d0a0b8699126f86835c87b8b1`.
All original exported files and the app's production checkout were unchanged during
the review. The receipt includes every source/log hash, exact commands and tools.
Reviewer: `gpt-6.1-sol`, `xhigh`, independent of the consumer implementation.

The isolated package resolves actual Mixer revision
`d8c6965a277ca21e685f3ef9e0f68a7d59b46156`, tree
`76261ef6219ef09713f6a76708d783c48d88a20a`, from the declared public remote Git
dependency. The observed fetch was a SwiftPM cache hit, not a fresh independent
download. Both app locks pin that exact remote revision. `FieldLogFeatures` imports
only public `MixerCore` APIs. Xcode's `../` package reference is the app's own package;
it does not point at a Mixer source checkout.

All scoped checks pass:

| Check | Functions | Cases |
| --- | ---: | ---: |
| Original unchanged host suite | 17 | 17 |
| Original plus independent host suite | 27 | 29 |
| Independent optimized suite | 10 | 12 |
| Independent Thread Sanitizer suite | 10 | 12 |

Independent tests exercise UTF-8 boundaries/NUL validation, exact retained inputs,
actual retry after failure, duplicate submit/edit suppression, saved-owner terminal
behavior, removed observers, old/new owner isolation, deinit cancellation, synchronous
saved-observer cleanup/reentry rejection and Cancel before submission. Repository
tests inject failures before file sync, after rename and after directory sync: no
false success, lost existing project or duplicate task on retry; reopening yields
the previous state or one complete new task/outbox. Another actual repository test
commits a task then closes its editor before delivering the result: the task remains
durable and the late success never reaches the closed owner. System frameworks are
not instrumented by the sanitizer.

The source review confirms the native observer only copies state into the form.
`onChange(saved)` dismisses; `onDisappear` removes the observer then closes the owner.
The actual save closure awaits `WorkspaceModel.addTask`, its serialized `enqueue`
task and `WorkspaceRepository.transact`, including file/directory sync, before
returning success. Failure keeps the input and displays an error. The visible Cancel
button and interactive dismissal remain disabled during saving, matching the native
baseline; post-submit close tests concern lifecycle ownership, not a claimed visible
cancel-during-save control. Closing does not promise undoing an accepted mutation or
preventing a cancellation-ignoring submitted callback from starting.

Existing consumer source/evidence hashes match the reviewed revision. Models,
storage schema/implementation and the original UI test were unchanged across SDK
adoption. The previously recorded simulator workflow has one passed test, zero
failures/skips/runtime warnings. The reviewer inspected its checklist and restored
draft screenshots. This is verification of prior evidence, not new independent UI
execution. Existing Android/WASI receipts remain compilation-only evidence.

No behavioral adoption blocker was confirmed. One P3 documentation issue was sent
to root for a separate scoped correction: README's opening says there is no Mixer
SDK dependency, contradicting its later correct public MixerCore adoption paragraph.
The review makes no app-source fix and does not hide this finding in its pass result.

This is a narrow public MixerCore adoption review. It does not qualify MixerUI,
actual UI cancel/storage-failure automation, Android app behavior, guest/OTA parity,
physical-device lifecycle/performance, account/network/photo/upload workflows,
customer use, signing/store operations, full D1 or any D0-D8/GA gate. No new physical
run was attempted; phones remain disconnected. FieldLog still has no remote app
publication claim and the Mixer dependency has no stable release-tag/API guarantee.
