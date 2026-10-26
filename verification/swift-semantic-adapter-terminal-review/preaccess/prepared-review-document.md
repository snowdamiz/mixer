# Independent terminal-contract review preparation

Status: **preaccess preparation sealed; correction review awaits root admission**.
This lane owns only this document and
`verification/swift-semantic-adapter-terminal-review/**`. The new correction,
producer model and producer tests have not been opened.

The original prerequisite seal is
`d145cda8cdde0915493f5c75102ae0dc11adb577891b1b773322b5c4d0f32cba`;
the original independent review-1 seal is
`d44b2edd19961ebeda7e197f549433e7a0d7f0630ce7d501e5465044340c6c02`;
its prior preaccess seal is
`7ae911b982f2bf96f596969c2c282bd5bbdd7302033a6d1404278f1df23d9ae9`.
All 152, 35 and 21 members respectively were independently rehashed unchanged.
Root explicitly admitted the original sealed contract.json and source-only
declaration/custody material as initial evidence.

The reviewer-authored plan and corpus live in the separate `preaccess/` packet.
They contain 114 terminal scenarios, seven numeric 32-word projection fixtures,
64 rejected full-word counterexamples, 24 accepted-child source obligations and
28 source-derived error partitions. A Python 3.14.8 run passes 213 finite corpus
consistency/normalization controls. The terminal scenarios are **not yet run
against the correction**, and these are **zero Rust/product tests**.

The finite projection fixtures distinguish suppressed all-zero extent from live
Idle0/MAX sentinels, preserve actual prepaid semantic debit and flags, and keep
four authority and two reserved words zero. Their boundary/reason values are
projector parameters. Missing original precedence decisions remain explicit
questions for the later source-contract review; no invented answer has been
used as an acceptance oracle.

Accepted child source inspection reveals a material distinction for that review:
the old envelope core catches `observe_inputs` read/footer/drift errors and can
return a framing aggregate if report writing succeeds. Outer setup/output-safety/
arena errors, report failures and post-report budget failure propagate as
`Err`, returning no aggregate or typed observation. The new boundary must define
its own exact partition while preserving both old entry points. Partial physical
report bytes cannot establish a successful returned observation.

The sole original blocker remains R1/C03 until the correction is independently
reviewed: total ordered terminal behavior and explicit projection of all32words.
The combined original C01-C10 design constraints remain in scope. Work budgets,
layouts, caller moves, ownership/lifetimes and actual Rust behavior stay
provisional. No numeric cap, profile, dependency, report or authority changes.

The context HEAD is `0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c`, not a claim
about the actively changing whole worktree or current live VM. Input snapshots,
source/member/tree hashes, exact commands/tool versions and raw outputs are
retained. Source copies are data; no old helper/model/harness or live VM was
imported or executed. Native/device/GA remain false. Computer use, capture,
UI automation, simulator/emulator/phones and process discovery stay paused; no
native or persistent process was started or queried. This lane made no git
index, commit, push, CI or root metadata mutation.
