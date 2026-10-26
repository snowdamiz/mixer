# Absent private state: independent accounting review

Status: preparation frozen; proposal access, accounting acceptance and execution are pending. This lane owns only this document and `verification/swift-envelope-absent-state-accounting-review/**`. It has not inspected the forthcoming absence-correction candidate, source, ledger or tests.

The independent obligations are fixed in [preparation/obligations.json](/Users/andreyyurlov/Documents/dev/mixer/verification/swift-envelope-absent-state-accounting-review/preparation/obligations.json). They derive from the accepted root addendum and selected numeric contract, the frozen source, and the failed accounting and behavioral reviews. Exact source/seal identities are recorded in the preparation receipt; prior packets are referenced directly rather than duplicated.

The accepted absence result is InternalPoisoned with private debit0 and spent0 before the funding threshold, with unchanged prior budget and no arena/candidate mutation. The existing source charges425 first when funded. Its caller also rejects funded poison0 and replaces it with poison425. Reordering the length check alone therefore cannot establish the contract.

The next frozen proposal must assign every precharge guard operation and complete reply transfer to an explicit prepaid owner; prove G dispatch is usable at most once; and provide a caller truth table covering accepted and rejected reply/budget forms. Existing G112 is selected for the underfunded prior-state/Steps guard. Overlap with existing rows does not authorize expanded ownership. Root alone selects any ownership or numeric amendment.

Selected leaf425/W24/B471/G112/T42/finish47/F42 remain the comparison baseline. Each successful main B471 still adds public425 even when the private reply has debit0. The public formula remains `534*S_paid + 47*F_paid + 425*N_B`; no refund, inactive-credit borrowing or use of unassigned memory margin is permitted. Exact groups are bounded by sixteen named scalar operations or one actual fixed copy of at most128 bytes. Complete types, source/destination places and lexical overlap must remain covered.

This is offline preparation only. No candidate or producer script was executed or compiled. No runtime, native, UI, capture, device, process discovery, hosted harness or authority path was accessed. It grants no product, replay, stored-prefix, release, FieldLog or GA acceptance.
