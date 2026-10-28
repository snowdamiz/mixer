# Hold controller release: three source blockers

Controller `e7bf73dc8f7816a651c0b987f0efd5b2db59e0e3fff9be92c59a56f469717433`
was reviewed as source only, without import or execution. The accepted model
source does not need another change for these findings.

- **C01 — generated bounds apply after execution** (lines 167–170, 193–199).
  The binary launches before the generated tree is checked against 32 MiB,
  64 members, symlink/type restrictions or bounded inventory. Hashing the binary
  first supplies none of those limits. The later inventory also hashes each file
  before checking its size total, and eagerly sorts the traversal. Inventory the
  owned generated tree within count/size/type bounds before hashing and launching
  the binary; retain a bounded final inventory and preserve ambiguity.
- **C02 — signal snapshot precedes cutoff** (lines 210–218). A blocked signal
  arriving between `sigpending()` and the cutoff timestamp is pre-cutoff but
  absent from `observed`; installing `SIG_IGN` may discard it and permit pass.
  Complete all hashes and observation digest first. Establish the one-way cutoff
  before the protected snapshot, or use the reviewed record-only pre/post-cutoff
  protocol. Pre-cutoff observations reject; later signals have an explicit scope
  outside the completed observation. Only receipt publication follows cutoff.
- **C03 — parsed control bytes lack complete custody** (lines 137–162, 173).
  The plan is parsed before a separate path rehash. The manifest and test roster
  are parsed without sealed digests and omitted from before/after pins. Therefore
  `all_pins_rechecked` does not cover all control data actually used. Anchor the
  exact v2 seal/member roster, bounded-read and hash the same bytes before using
  them, and retain these control-file pins through posthash. Use the verified
  roster for the 24 expected names; refuse duplicate keys/path collisions.

The inspected serial-command, output-cap and WNOWAIT ownership structure does
not add another blocker here. The retained leader precedes custody checks;
group signaling finishes before reaping. Cleanup/posthash failures add errors,
and errors gate pass. None of this is an observed runtime result.

No compiler, test, model, producer replay, native/UI/capture/device action,
process inventory, canonical metadata edit, commit or push occurred. Recommend
a separately frozen controller correction and focused source re-review before
root releases the single accepted compile/test plan.
