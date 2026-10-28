"""Hand-reviewed crosswalk and future evidence requirements; no product prices."""

# IDs are one-based in the exact accepted query roster. The first list names
# directly observed representation families. The second names work contexts,
# never a price or an extra dynamic invocation.
SHAPES = [
 (['S01'],['W01','W02','W07'], 'Correspondence contains owner provenance, association and original-root reference; no root backing is included.'),
 (['S01'],['W01','W02','W07'], 'Attempt contains owner/live/association/original-root fields; borrowed expected input is a separate view.'),
 (['S02'],['W02','W03','W09'], 'Complete success RootBound<File carrier>; raw carrier alone is not separately observed here.'),
 (['S02'],['W02','W03','W09'], 'Complete refusal tuple envelope; its fields are included, not extra simultaneous allocations.'),
 (['S02'],['W02','W03','W09'], 'Whole bound Result before the private into_result transition.'),
 (['S02'],['W02','W03','W09'], 'Whole Result after the private into_result transition; alternatives are not additive live arms.'),
 (['S03'],['W03','W04','W05'], 'Complete selected/files/usage payload; selected proof/source and File backing remain separate.'),
 (['S02','S03'],['W03','W04','W05'], 'Root-bound selected payload; contains the entire RawSelectedBundle representation.'),
 (['S03'],['W03','W04','W05'], 'Correlated selected newtype; contains the root-bound bundle.'),
 (['S03'],['W03','W04','W05'], 'Selected newtype after conversion; equal size does not prove transfer work is zero.'),
 (['S03'],['W03','W05','W09'], 'Complete raw correlated/refused enum; internal alternatives and returned Files are not added again.'),
 (['S02','S03'],['W03','W05','W09'], 'Bound raw correlation enum; moving root does not retire original error/proof backing.'),
 (['S03'],['W02','W03','W04','W05','W09'], 'Opaque complete correlation outcome; all nested payload representation already included.'),
 (['S04'],['W05','W07','W08'], 'Whole rows/snapshot/cancellation/claims/budget/Instant argument package; later moves do not imply fresh backing.'),
 (['S04'],['W04','W05','W09'], 'Whole raw primary enum includes original failure or complete leaf result representation.'),
 (['S04'],['W04','W05','W09'], 'Complete raw final fixture result; includes primary/files/usage/rows/snapshot/cancellation/claims.'),
 (['S02','S04'],['W04','W05','W09'], 'Whole root-bound raw result; backing remains separate from this inline extent.'),
 (['S04'],['W04','W05','W07','W09'], 'Opaque final fixture newtype; same nested root-bound raw result is not another value allocation.'),
 (['S07'],['W06'], 'Short primary view enum; its pointer representations do not own the referenced original payload.'),
 (['S01'],['W01'], 'Complete correspondence/attempt pair; the observed pair includes both member representations.'),
 (['S01'],['W01','W11'], 'Scope Result envelope; same size as the pair is not zero branch or transfer work.'),
 (['S04'],['W04','W05'], 'Whole branch join tuple; Files/usage/root component representations are included.'),
 (['S05'],['W07','W08','W09','W10','W11'], 'Complete admitted outcome with outer root; Loaded already includes an inner bound root.'),
 (['S05'],['W07','W08','W09'], 'Complete setup-refused/loaded payload enum; no independent setup allocation/capacity bound follows.'),
 (['S05','S12'],['W07','W09','W10','W11'], 'Complete child owner containing Option<payload> and Option<reservation>; parent token/frame remains separate.'),
 (['S05','S12'],['W07','W10','W11'], 'Complete entry Result; its success child representation is included.'),
 (['S05'],['W09','W10'], 'Actual Option<admitted> instantiation used by child payload take/drop; generic MIR T is not silently substituted.'),
 (['S07'],['W06','W10'], 'Actual short Option<&admitted> view only; this is not a general reference-layout or backing quote.'),
]

MISSING = {
 'S01':'Listed association and pair/Result shapes are numeric. Standalone root/other local/argument representations, their coexistence, and original acquisition backing are not closed.',
 'S02':'Only listed concrete production RootBound/Result specializations are numeric. Generic T/E/A/B/R, test-only pair partition specializations, other locals and simultaneous source/destination storage remain unresolved.',
 'S03':'Listed complete selected/correlation shapes are numeric. File/array/Option reconstruction locals, unchanged payload contexts, selected/error/proof backing capacity and lifetime/cleanup remain unresolved.',
 'S04':'Arguments, raw primary/result, bound result and branch tuple shapes are numeric. Scope/run/finish callee places, call/return overlap, retained backing and complete physical frame peak remain unresolved.',
 'S05':'All selected admitted/child Result/Option shapes are numeric. Setup partial-prefix and loaded backing, transient take/drop storage, return/cleanup coexistence and the independently charged parent frame remain unresolved.',
 'S06':'The exact actual-closure representation subquestion is answered:48 bytes/alignment8. A complete incremental storage charge still needs its actual lifetime/physical-slot/caller-callee overlap and backing partition; no charge is selected.',
 'S07':'Primary view16 and Option<&admitted>8 are numeric. LoaderUsage/discriminant/scalar copies and parent token/return representations and their live intervals are not closed; borrowed pointees remain separately owned.',
 'S08':'No new dynamic capacity/backing bound is established. Proof/source buffers, SelectedValidatedProfile/LoaderFailure/io-error backing, required Files and optional executable require complete retained-capacity/lifetime evidence.',
 'S09':'No new setup/fixture backing bound is established. Partial File prefix/io-error, rows/snapshot, Cancellation shared allocation/clone, claims and scope/finish originals require capacities and last-destruction evidence.',
 'S10':'No root funding or retirement obligation closes.8-byte aggregate wrapper uplifts are representations, not acquisition charge, durable custody, useful joint retirement or shutdown proof; forgetting remains pending.',
 'S11':'No simultaneous-storage bound closes. Partial moves, call/return buffers, drop flags, normal/cleanup paths and monomorphized drop dependencies need complete live-region and backing intervals.',
 'S12':'Child owner inline wrapper uplift is16 bytes for this concrete shape only. Independent DestroyedStorage/Reservation/Option token and P0 parent frame storage remain unobserved/unpriced; child release cannot refund acquisition.',
}

EXTRA_RELATED = {
 'S08':list(range(3,14))+list(range(15,19))+list(range(22,28)),
 'S09':list(range(14,19))+list(range(22,28)),
 'S10':[1,2,3,4,5,6,8,9,10,12,13,17,18,20,21,22,23,24,25,26,27,29],
 'S11':list(range(3,19))+list(range(22,28))+[29],
 'S12':[25,26,29],
}

# Each row is a subtraction between separately observed whole shapes. It is not
# an accepted incremental price, field offset, prior-version delta or backing.
DIFFERENCES = [
 ('D01',8,7,'root-bound selected aggregate uplift'),
 ('D02',12,11,'root-bound raw correlation aggregate uplift'),
 ('D03',17,16,'inner root-bound final raw-result aggregate uplift'),
 ('D04',23,24,'outer admitted root-bearing aggregate uplift'),
 ('D05',25,23,'complete child-owner wrapper aggregate uplift'),
 ('D06',23,16,'selected inner+outer admitted wrapping chain'),
 ('D07',25,16,'selected inner+outer+child wrapping chain'),
 ('D08',26,25,'entry Result same-size observation'),
 ('D09',27,23,'Option<admitted> same-size observation'),
 ('D10',9,8,'correlated selected newtype same-size observation'),
 ('D11',10,8,'selected newtype same-size observation'),
 ('D12',13,12,'owned correlation newtype same-size observation'),
 ('D13',18,17,'fixture newtype same-size observation'),
 ('D14',6,5,'into_result envelope same-size observation'),
]

PROSPECTIVE = [
 ('P01','Reject source/compiler/target/cfg drift or a type outside the accepted finite roster; no suffix-only type match.'),
 ('P02','Refuse borrowing the24/32-byte value layout for a reference to that value; do not substitute File for generic R or concrete payload for T/E/A/B without exact instantiation evidence.'),
 ('P03','Distinguish the dispatch closure from the separate1187-line identity/preimage closure; never use captured-field sums as the actual closure observation.'),
 ('P04','Count a complete13640-byte child owner once; do not add its nested13624-byte admitted outcome or13616-byte payload as distinct backing.'),
 ('P05','Count the56-byte scope pair once if quoting that aggregate; do not also charge24+32 for its own contained fields.'),
 ('P06','Reject a peak inferred by summing645 places or2873 MIR rows; preserve all alternative branches and CTFE/shim duplication without inventing calls.'),
 ('P07','Require proven live physical regions/call-return buffers before overlap deduplication; a semantic move alone proves neither fresh allocation nor physical aliasing.'),
 ('P08','Use checked arithmetic in bytes for unioned live extents, all required alignment/padding and separate backing capacities; missing capacities refuse instead of defaulting to zero.'),
 ('P09','Same-size Result/Option/newtype observations may have0-byte representation uplift but cannot select zero work, zero storage charge or zero dynamic cost.'),
 ('P10','Do not infer standalone root-reference size/field offset, Reservation/DestroyedStorage size or root charge from8/16-byte aggregate differences.'),
 ('P11','Rebind the existing fixed leaf sequence once; do not charge both old helper and relocated frame as two invocations.'),
 ('P12','Exercise setup refusal after every owned prefix, correlation arms, scope refusal/finish, unwind and ordinary Drop with complete retained originals and no premature release.'),
 ('P13','Keep child-only token storage provisioned in P0 after destruction; reject any child token that releases acquisition funding.'),
 ('P14','StorageDead or inaccessible/forgotten handles do not prove backing destruction, durable root custody or a refund; require explicit destruction/release intervals.'),
 ('P15','Bind actual capacities for proof/source/io-error/Vec/Arc/Cancellation/File/OS resources and keep shared backing charged once through its final owner, distinct from borrowed views.'),
 ('P16','Keep W01-W12 positive and unpriced until complete action/drop/stdlib/callee work bases are reviewed; type sizes and static row counts are not runtime work prices.'),
]
