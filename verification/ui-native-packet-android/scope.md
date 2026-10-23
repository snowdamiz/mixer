# Ordinary Android packet adoption

The reusable `AndroidDocumentSession` and checklist example now call the reviewed
SDK `encodeNativePacketV1()` operation. Their existing error enums and transaction
boundaries remain: a failed encoded candidate does not commit state, revision or
reconciliation. The public `RenderPacket` value remains available.

Candidate2 freezes 45 exact inputs. Nine engine/runtime tests pass per Debug and
Release, including initial oversized escaped output and an oversized update that
preserves the prior packet/state/generation before a valid Unicode update succeeds.
Two separate public consumers emit actual checklist and reusable-session packets;
the existing production Java decoder accepts them. Its existing 34 wire-contract
checks also pass. The official Swift 6.3.3 Android SDK builds an actual API28
AArch64 shared library, whose ELF header/dependencies are retained in the log.

Candidate1 preserves a verification-harness link failure: one executable attempted
to link the dynamic checklist product together with the static reusable runtime
and SDK, which SwiftPM rejects as duplicate library code. Candidate2 uses separate
public consumers for the example and reusable runtime. It changes no manifests or
library product linkage to conceal that limitation.

These results qualify the data encoder adoption only. They execute no Android
JNI, widgets, device lifecycle, signed presentation or UI styling. App packaging,
physical design parity and published FieldLog remain separate qualification.
