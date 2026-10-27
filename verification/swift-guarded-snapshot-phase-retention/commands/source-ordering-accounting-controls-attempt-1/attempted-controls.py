"""Exact differential and compiler reconciliation; never release authority."""
from pathlib import Path
import json,re,sys
sys.dont_write_bytecode=True
from prepare import HERE,BASE,CONTROL,PROFILE,sha,canonical,members,write,custody
from verify import selected,roles,norm_type

def body(text,start,end):
 first=text.index(start);return text[first:text.index(end,first)]
def normalized(b):
 b='\n'.join(line.split('//',1)[0].rstrip() for line in b.splitlines())
 b=norm_type(b);return b.replace('retained','previous')
def main():
 binding=custody();checks=[]
 def check(label,ok):
  assert ok,label
  checks.append(dict(name=label,passed=True))
 old=BASE/'source/vm';new=HERE/'source/vm';prep=json.loads((HERE/'preparation.json').read_text())
 changed=[r['path'] for r in members(old) if (old/r['path']).read_bytes()!=(new/r['path']).read_bytes()]
 check('exact two product source members changed',changed==[PROFILE,CONTROL])
 inverse={n:(new/n).read_text() for n in changed}
 for n,row in enumerate(reversed(prep['exact_replacements'])):
  check('unique declared inverse '+str(n),inverse[row['path']].count(row['new'])==1)
  inverse[row['path']]=inverse[row['path']].replace(row['new'],row['old'])
 for n in changed:check('entire file inverse restored '+n,inverse[n]==(old/n).read_text())
 oc=(old/CONTROL).read_text();nc=(new/CONTROL).read_text();op=(old/PROFILE).read_text();np=(new/PROFILE).read_text()
 check('one product call and one definition of commit',sum(p.read_text().count('snapshot_commit_storage_v1(') for p in new.rglob('*.rs'))==2)
 check('sole caller binds committed retained target',np.count('let retained=control.snapshot_commit_storage_v1(additional)?;')==1)
 check('complete forwards unchanged retained target and WASI',np.count('Self::Admitted{control,retained,wasi}=>control.end_construction_phase_with_wasi(storage,retained,wasi),')==1)
 check('old target field removed', 'previous:usize' not in body(np,'enum SnapshotAccessV1','\nstruct SnapshotShapeV1'))
 ranges=[
  (CONTROL,'    pub(crate) fn end_construction_phase_with_wasi<T>','\n    /// Caller passes the actual storage'),
  (CONTROL,'    pub(crate) fn finish_owned_cleanup','\n// Isolated source preparation.'),
  (CONTROL,'impl SnapshotRunV1 {','\n#[derive(Clone,Copy,Debug,PartialEq,Eq)]'),
  (CONTROL,'    pub(super) fn snapshot_storage_preflight_v1','\n    pub(super) fn snapshot_commit_storage_v1'),
  (PROFILE,'impl ClosedBranchV1 for OriginalBranchV1','\nimpl ClosedBranchV1 for SnapshotBranchV1'),
  (PROFILE,'fn proposed_emission_work_v1','\nfn begin_snapshot_access_v1'),
  (PROFILE,'struct SnapshotWriterV1','\nstruct SnapshotFoundationPlacesV1'),
 ]
 preserved=[]
 for file,start,end in ranges:
  oldtext=(old/file).read_text();newtext=(new/file).read_text()
  # The exact writer tail is bounded by the existing following inventory marker.
  a=body(oldtext,start,end);b=body(newtext,start,end);check('preserved '+start,a==b)
  preserved.append(dict(path=file,start=start,end=end,bytes=len(a.encode()),sha256=sha(a.encode())))
 check('exact constant funding input unchanged', (HERE/'funding-constants.inc.rs').read_bytes()==(BASE/'funding-constants.inc.rs').read_bytes())
 check('unchanged fixed memory and work policies','combined_bytes: 256 * MIB,' in nc and 'execution_work: 1_000_000_000,' in nc)
 check('WorkAuditPending remains', 'Err(AError::WorkAuditPending)' in body(np,'fn proposed_emission_work_v1','\nfn begin_snapshot_access_v1'))
 check('refused body unchanged', 'Self::Refused{control:_,error:_}=>{drop(storage);Ok(())},' in np)
 check('retained target field type unchanged', 'retained:usize,wasi:Option<crate::experimental_wasi::WasiUsage>' in np)
 old_commit=body(oc,'    pub(super) fn snapshot_commit_storage_v1','\n// Conservative candidate source roles.')
 new_commit=body(nc,'    pub(super) fn snapshot_commit_storage_v1','\n// Conservative candidate source roles.')
 check('commit full difference is bound operand only',new_commit==old_commit.replace('Ok(previous)','Ok(construction)'))
 check('no arithmetic/call/work source delta',new_commit.count('checked_add(')==old_commit.count('checked_add(')==2)
 # Both output/move slots remain fully funded. No local lifetime reuse inference.
 contexts=[]
 for mode in ['production','unit']:
  br=json.loads((HERE/'commands'/('baseline-'+mode)/'receipt.json').read_text());cr=json.loads((HERE/'commands'/('candidate-'+mode)/'receipt.json').read_text())
  check('baseline exact metadata/MIR success '+mode,br['exit_code']==0 and br['expectation_met'])
  check('candidate exact metadata/MIR success '+mode,cr['exit_code']==0 and cr['expectation_met'])
  check('same exact compiler '+mode,br['compiler_sha256']==cr['compiler_sha256'])
  bs=selected((HERE/'commands'/('baseline-'+mode)/'focused-functions.mir').read_text());cs=selected((HERE/'commands'/('candidate-'+mode)/'focused-functions.mir').read_text())
  details=[]
  for key in sorted(bs):
   check('exact role name/type equality '+mode+' '+key,roles(bs[key])==roles(cs[key]))
   bn=normalized(bs[key]);cn=normalized(cs[key])
   if key=='commit':
    oldlocal=re.search(r'debug previous => (_\d+);',bn).group(1);newlocal=re.search(r'debug construction => (_\d+);',cn).group(1)
    oldreturn='_0 = Result::<usize, SnapshotAdmissionErrorV1>::Ok(copy '+oldlocal+');'
    newreturn='_0 = Result::<usize, SnapshotAdmissionErrorV1>::Ok(copy '+newlocal+');'
    check('commit uses prior bound local in baseline '+mode,bn.count(oldreturn)==1)
    check('commit uses already computed committed bound local '+mode,cn.count(newreturn)==1)
    cn=cn.replace(newreturn,oldreturn)
   check('MIR work/body unchanged except declared return/rename '+mode+' '+key,bn==cn)
   details.append(dict(function=key,baseline_mir_sha256=sha(bs[key].encode()),candidate_mir_sha256=sha(cs[key].encode()),declared_roles=roles(cs[key]),role_delta=0,work_delta=0))
  contexts.append(dict(mode=mode,compiler_sha256=cr['compiler_sha256'],functions=details))
 write('source-delta-accounting.json',dict(schema=1,source_binding=binding,changed_source_members=2,declared_replacements=len(prep['exact_replacements']),fresh_compiler_contexts=contexts,new_runtime_locals=0,new_runtime_roles=0,new_runtime_calls=0,new_runtime_arithmetic=0,new_type_or_field_layouts=0,new_work_actions=0,all_old_source_role_charges_retained=True,retained_old_selected_floor_charge_bytes=200,optional_or_removed_role_credits_selected=False,no_hidden_storage_reuse_assumption=True,type_rule='Only existing bound usize return operand and same-length binding/field identifier names change. All field types, signatures and focused MIR role types are identical in each exact compiler context.',source_role_rule='No existing role removed or credited; separate producer return/move/receiving roles all remain charged at accepted C/S/A/H amounts.',work_rule='Fresh unoptimized MIR instruction/control-flow bodies match after only the declared operand/binding normalization; no call, arithmetic, traversal, debit or validation action is added.',accepted_recipe=dict(C=78240,S=941467,A=430175,H=81327),preserved_boundaries=preserved,limitations=['A remains charged through completion and conservative final retirement; no healthy cleanup claim','H pre-ingress/external-harness ownership, complete writer funding/work and writer release remain pending','No physical stack/RSS or other target qualification']))
 write('ordering-controls.json',dict(schema=1,source_binding=binding,passed=len(checks),controls=checks,syntax_authorizes_release=False,VM_writer_executed=False))
 print(json.dumps(dict(passed=len(checks),role_delta=0,work_delta=0),sort_keys=True))
if __name__=='__main__':main()
