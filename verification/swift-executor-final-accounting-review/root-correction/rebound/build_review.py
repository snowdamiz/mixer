from pathlib import Path
import json,re,hashlib,difflib
O=Path(__file__).resolve().parent;T=O/'tree/vm';OLD=O.parents[1]
source=T/'src/experimental_swift_reactor/control.rs';s=source.read_text();old=(OLD/'inputs/vm/src/experimental_swift_reactor/control.rs').read_text()
(O/'root-control.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='frozen-old/control.rs',tofile='frozen-corrected/control.rs')))
# Independently match actual corrected production inventory declarations to the
# exact source-role groups from the prior review, without synthesizing fields.
roles=json.loads((OLD/'source-roles.json').read_text())['groups']
mapnames={'FinalOutputBorrows':'FinalOutputBorrows','ClockLeaf':'FinalClockInventory','FaultLeaf':'FinalFaultInventory','CategoryLeaves':'FinalCategoryInventory','RefundParent':'FinalRefundInventory','RecordParent':'FinalRecordInventory','FinishConstFormulaParent':'FinalFinishInventory'}
def norm(x):return re.sub(r'\s+','',x)
matched={}
for previous,new in mapnames.items():
 m=re.search(r'\bstruct '+new+r'\s*\{',s);assert m;start=m.end();end=s.index('}',start);body=s[start:end]
 # A field ends at the comma before the next field, allowing commas within generics.
 starts=list(re.finditer(r'(?m)^    (\w+):',body))
 fields=[(m.group(1),body[m.end():starts[i+1].start() if i+1<len(starts) else len(body)].strip().rstrip(',')) for i,m in enumerate(starts)]
 assert len(fields)==len(roles[previous]),(new,len(fields),len(roles[previous]))
 checked=[]
 for actual,expected in zip(fields,roles[previous]):
  shape=mapnames.get(expected['type'],expected['type']);assert actual[0]==expected['field'];assert norm(actual[1])==norm(shape),(new,actual,shape)
  checked.append({'field':actual[0],'actual_type':actual[1].strip(),'source_role':expected['source']})
 matched[new]=checked
# Original actual engine implementation is byte-identical outside the single
# inventory/formula region; the root correction changes no helper algorithms.
oldstart=old.index('/// Conservative explicit object-transfer/scratch envelope')
oldend=old.index('\nimpl RuntimeControl {',oldstart)
newstart=s.index('// Final cleanup has no cache/WASI/execution owner envelope')
newend=s.index('\nimpl RuntimeControl {',newstart)
assert old[:oldstart]==s[:newstart]
assert old[oldend:]==s[newend:]
# All eight terms are parsed and checked. The former seven counts/types remain literal.
terms=re.search(r'const FOUNDATION_CONSTRUCTION_BYTES: Option<usize> = \{(.*?)\n\};',s,re.S).group(1)
assert '[(usize, usize); 8]' in terms and '.checked_mul(' in terms and '.checked_add(' in terms
assert 'into_iter' not in terms and 'try_fold' not in terms
runtime=re.search(r'pub\(crate\) fn foundation_construction_bytes\(\) -> Option<usize> \{(.*?)\}',s,re.S).group(1).strip()
assert runtime=='FOUNDATION_CONSTRUCTION_BYTES'
expectedterms=['(3, size_of::<ValidatedSwiftReactor>())','(3, size_of::<RuntimeControl>())','(3, size_of::<AdoptedProof>())','(4, size_of::<SwiftRunFailure>())','(4, size_of::<SwiftRunUsage>())','(6, size_of::<ReservationTicket>())','(6, size_of::<Option<WasiUsage>>())','(1, FOUNDATION_FINAL_BOUNDARY_BYTES)']
for term in expectedterms:assert norm(term) in norm(terms)
summary={'actual_inventory_types':matched,'field_count':sum(map(len,matched.values())),'outside_inventory_and_formula_byte_identical':True,'old_seven_literal_terms_unchanged':True,'formula_explicit_const_initializer':True,'runtime_formula_body':runtime}
(O/'source-review.json').write_text(json.dumps(summary,indent=2)+'\n')
probe='\n#[allow(dead_code)]\npub fn independent_root_final_metadata() {\nuse std::mem::{align_of,offset_of};\n'
for n,fs in matched.items():
 probe+='println!("layout '+n+' {} {}",size_of::<'+n+'>(),align_of::<'+n+'>());\n'
 for f in fs:probe+='println!("field '+n+' '+f['field']+' {} {} {}",size_of::<'+f['actual_type']+'>(),align_of::<'+f['actual_type']+'>(),offset_of!('+n+','+f['field']+'));\n'
for n in ['RuntimeControl','SwiftRunFailure','SwiftRunUsage','ReservationTicket','Option<WasiUsage>','crate::experimental_swift_reactor::execution::SwiftExecutionState','crate::experimental_swift_reactor::execution::SwiftReactorInstance']:
 probe+='println!("shape '+n+' {} {}",size_of::<'+n+'>(),align_of::<'+n+'>());\n'
probe+='println!("foundation {} final {}",foundation_construction_bytes().unwrap(),FOUNDATION_FINAL_BOUNDARY_BYTES);\nassert_eq!(foundation_construction_bytes(),Some(17368));\nassert_eq!(FOUNDATION_FINAL_BOUNDARY_BYTES,864);\nassert_eq!(size_of::<RuntimeControl>(),1720);\n}\n#[test]\nfn independent_root_final_metadata_test(){independent_root_final_metadata();}\n'
(O/'metadata-probe.rs').write_text(probe);source.write_text(s+probe)
p=T/'src/experimental_swift_reactor/mod.rs';p.write_text(p.read_text()+'\n#[doc(hidden)]\npub fn independent_root_final_metadata_only() { control::independent_root_final_metadata(); }\n')
p=T/'examples/independent_root_final_metadata.rs';p.parent.mkdir(exist_ok=True);p.write_text('fn main(){mixer_vm::experimental_swift_reactor::independent_root_final_metadata_only();}\n')
print('matched production',len(matched),'types',summary['field_count'],'fields; exact unchanged engine outside additive block')
