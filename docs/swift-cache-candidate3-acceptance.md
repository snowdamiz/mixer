# Private Swift cache candidate3 acceptance

Root accepts the bounded private cache implementation and its required synthetic
assertions at cache source `43d4d7af4a1959d2afd5b1da39801b0a0e4a875d5b81f05142b4befa5e120614`,
test source `a734428c772f6bcced05e51a452721831e9eb9ebfa6a84c44e02efec16987c00`,
and source union `fd939d26dfe6465af839c5e1a1f71a8ccacc52668591d5d09650eddb024582c3`.
The independent decision is
`verification/swift-function-cache-review/candidate-3-review-receipt.json`.
The root binding audit is
`verification/swift-function-cache-root-review/acceptance.json`.

This is a new exact-source acceptance. The candidate2 whole-slot phase addendum
and its original root acceptance remain historical; neither is silently extended
to changed source. Independent candidate3 source/field/layout checks establish
unchanged early and final phase alternatives and 23 unchanged inventory groups.
The owner allocator helper adds two distinct construction-only counter borrows
(16 bytes, counted three times) and three small complete Result transfer roles
(48 bytes). Construction is therefore 57,224 bytes, an explicit increase of 96.
Operation80,566, cleanup62,096, header62,424 and foundation16,504 remain unchanged.
This helper runs only after ordinary construction enlargement. It cannot borrow
preflight or final-cleanup allowances. No foundation count, padding, remainder,
foreign charge or inferred last-use saving is introduced.

The accounting model covers authored named Rust values and requested payloads,
not physical compiler stack, opaque standard-library internals, allocator overhead
or RSS. A different target must measure its actual type sizes and satisfy every
whole-group fit. Executor caller-held values need their own admitted envelopes.

All 18 required named tests execute independently in Debug and Release. The two
prior gaps are closed: each of 21 explicit terminal latches retains first cause
with no new decode/service/allocation/work across 315 repeated routes per profile;
three real constructor owner-exhaustion failures per profile use an isolated
test counter and drain their actual partial allocations. A separate concurrent
probe verifies that private counter exhaustion neither seeds nor changes global
owner allocation. Latch propagation does not claim natural guest/executor failure
origins. Legacy replays, eight supplementary probes per mode, private compile
outcomes and full producer matrix/reference results remain separately attributed.

This acceptance satisfies the private-cache dependency for a separately assigned
compiling executor type/lifetime/layout prerequisite under the frozen executor
contract. It does not authorize skipping that measured prerequisite, instantiate
or run the full Swift target, add a public execution route, qualify a device or
pass any signing, store, operational, dogfood or GA gate.
