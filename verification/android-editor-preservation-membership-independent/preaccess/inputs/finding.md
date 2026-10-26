# PC-C16: duplicated owned journal state consumes another represented hold

The mandatory preaccess PC-S05 fixed journal-membership mutation control fails on released product tree cb5c2b813b9cb375f2907bafcb066ba9c556a2713ffd04c9d74777d9595d01e4, candidate seal8f355ae83ec4d734e8d28451fc64a45200967a718eecb7c1987fa0fcc69d9920.

This is a labelled hostile private state-invariant control, not an ordinary reachable path, public exploit, or recovery claim. At the unchanged host bridge commit beforeReturn boundary, after normal preparation validates both actual A/C holds and real B lease, it replaces only C's existing journal.states array slot with the exact existing owned A NativeState. No flags, count, scope, candidate, stateCount, previous list, original/token, Record or registration is otherwise changed. No new production callback is introduced.

Actual real coordinator edit returns true, terminal=false, SUCCESS_DONE, shared0/preservation0/candidateHeld0, A released/not-counted, while C remains counted/not-released with its original callback registration. editorDisposalBusyV2 is false. Complete product/host source is compiled independently; raw failing output and bounded cleanup are retained.

Cause: preservationCohortV2 sums counted slots, not distinct exact owned holds. fieldPreservationIdentityV2 accepts the repeated A state each visit. Success preflight therefore accepts two identical A references as a cohort of2. The direct scalar tail decrements A twice and never visits C. Prior PC-S05 explicitly requires fixed journal membership/size mutation coverage, and the selected protocol requires each represented exact counted hold to release once.

Root should classify this invariant relative to the selected fixed-membership contract. It requires no public/native reachability inference. A correction, if selected, must establish exact immutable journal membership before success effects without adding any callable or throwing step to the healthy scalar tail, and must preserve C custody on refusal.
