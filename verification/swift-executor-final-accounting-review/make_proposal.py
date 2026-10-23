from pathlib import Path
import json
O=Path(__file__).resolve().parent
G=json.loads((O/'source-roles.json').read_text())['groups']
selected=['FinalOutputBorrows','ClockLeaf','FaultLeaf','CategoryLeaves','RefundParent','RecordParent','FinishConstFormulaParent']
names={n:'FoundationFinal'+n for n in selected}
s='''// Candidate proposal only, for root adaptation and separate source acceptance.
// These inventory types are never instantiated. Each field is an explicit
// source role in source-roles.json; whole group max changes only between ended
// refund, record and finish helper calls. This changes no stored owner type.
'''
for n in selected:
 s+='#[allow(dead_code)]\nstruct '+names[n]+' {\n'
 for x in G[n]:s+='    '+x['field']+': '+names.get(x['type'],x['type'])+',\n'
 s+='}\n'
s+='''
const FOUNDATION_FINAL_BOUNDARY_BYTES: usize = {
    let refund = size_of::<FoundationFinalRefundParent>();
    let record = size_of::<FoundationFinalRecordParent>();
    let finish = size_of::<FoundationFinalFinishConstFormulaParent>();
    let first = if refund > record { refund } else { record };
    if first > finish { first } else { finish }
};

// All array/loop/closure metadata computation occurs in this const initializer.
// The public spelling remains a function that copies the precomputed Option.
// No runtime temporary array, IntoIter or try_fold exists in this proposal.
const FOUNDATION_CONSTRUCTION_BYTES: Option<usize> = {
    let terms: [(usize, usize); 8] = [
        (3, size_of::<ValidatedSwiftReactor>()),
        (3, size_of::<RuntimeControl>()),
        (3, size_of::<AdoptedProof>()),
        (4, size_of::<SwiftRunFailure>()),
        (4, size_of::<SwiftRunUsage>()),
        (6, size_of::<ReservationTicket>()),
        (6, size_of::<Option<WasiUsage>>()),
        (1, FOUNDATION_FINAL_BOUNDARY_BYTES),
    ];
    let mut sum = Some(0usize);
    let mut index = 0usize;
    while index < terms.len() {
        sum = match (sum, terms[index].0.checked_mul(terms[index].1)) {
            (Some(accumulated), Some(term)) => accumulated.checked_add(term),
            _ => None,
        };
        index += 1;
    }
    sum
};

// Root replaces the original function with this spelling when adapting.
pub(crate) fn proposed_foundation_construction_bytes() -> Option<usize> {
    FOUNDATION_CONSTRUCTION_BYTES
}
'''
(O/'foundation-proposal.rs').write_text(s)
p=O/'tree/vm/src/experimental_swift_reactor/foundation_const_proposal.rs'
p.write_text('use super::*;\n'+s+'''
#[test]
fn independent_proposed_final_foundation_const_formula() {
    assert_eq!(foundation_construction_bytes(), Some(16504));
    assert_eq!(FOUNDATION_FINAL_BOUNDARY_BYTES, 864);
    assert_eq!(proposed_foundation_construction_bytes(), Some(17368));
}
''')
p=O/'tree/vm/src/experimental_swift_reactor/control.rs';s=p.read_text();suffix='\n#[cfg(test)]\n#[path = "foundation_const_proposal.rs"]\nmod foundation_const_proposal;\n'
if suffix not in s:p.write_text(s+suffix)
p=O/'review.md';s=p.read_text().replace('d81405559cc6bb50803a674f556eb61e75507940',json.loads((O/'input-manifest.json').read_text())['revision']);p.write_text(s)
