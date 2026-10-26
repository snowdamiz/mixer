"""Prepare, do not compile/execute, seven root-reviewable private guard witnesses."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/'private-guard-proposal'
PRE=ROOT/'verification/swift-cache-state-independent-review/preaccess'
STAGED=Path(__file__).resolve().parent/'work/source/verification/swift-cache-state-implementation/source/library'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(name,v):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def main():
 OUT.mkdir(exist_ok=True)
 table=PRE/'inputs/verification/swift-semantic-adapter-terminal-correction/terminal-contract.json'
 raw=table.read_bytes();t=json.loads(raw)
 fixture=PRE/'fixtures/terminal-full32.json';fr=fixture.read_bytes();frozen={c['id']:c for c in json.loads(fr)}
 source_hashes={n:sha((STAGED/n).read_bytes()) for n in ['analyzer.rs','envelope.rs','cache_state.rs']}
 if source_hashes['cache_state.rs']!='d0e2ec2998f70958e10a7dbf33742917ced66cd4559bafb88bcabe8b221a54db':raise ValueError('baseline')
 (OUT/'accepted-terminal-contract.json').write_bytes(raw)
 definitions=[('idle-baseline',0,2,0,0,1,'stage-word-00'),
  ('idle-inactive-selected-outside',0,8,0,0,1,'stage-word-00'),
  ('idle-inactive-taken-not-subset',0,0,4,0,1,'stage-word-00'),
  ('pending7-baseline',7,2,0,0,1,'stage-word-07'),
  ('pending7-feasible-false',7,2,0,0,0,'T09'),
  ('pending8-baseline',8,2,2,0,1,'stage-word-08'),
  ('pending8-feasible-false',8,2,2,0,0,'T09')]
 cases=[]
 for name,stage,selected,taken,committed,feasible,expected_id in definitions:
  q=[4,20,30,stage,2,513,2,6,1,4,selected,taken,committed,1,1,feasible]
  cases.append({'id':name,'q':q,'calls':4,'latch':0,'N':4,'NC':4,'SS':1,'SF':1,
   'child':'actual private envelope projection object CapCutUnknownTail/Observed with coherent Ok(true)/CAP framing',
   'expected_words':frozen[expected_id]['expected_words'],'expected_shape':feasible!=0,
   'sealed_expected_origin':expected_id,'reason':'Q10 inactive guards' if name.startswith('idle-inactive') else 'Q9 requires feasible=true at stage7/8' if feasible==0 else 'unchanged baseline',
   'coverage':'deliberately seeded private projection/guard only; no public from-empty reachability claim'})
 put('expected-cases.json',{'cases':cases,'full32_fixture_path':str(fixture.relative_to(ROOT)),
  'full32_fixture_sha256':sha(fr),'machine_table_path':str(table.relative_to(ROOT)),
  'machine_table_sha256':sha(raw),'machine_guards':{k:t['exact_snapshot_guard_expressions'][k] for k in ['Q9_pending','Q10_inactive']},
  'emitted_test_credit_before_root_admission':0})
 body=['//! Independent private guard witnesses. No product edits or cfg(test) harness.',
  'use super::*;',
  'fn words(v:&FixtureCacheStateObservationV1)->[u64;32]{',
  'let b=match v.boundary(){FixtureCacheStateBoundaryV1::Unavailable=>0,FixtureCacheStateBoundaryV1::ClosedFixtureObserved=>1,FixtureCacheStateBoundaryV1::CapCutUnknownTail=>2,FixtureCacheStateBoundaryV1::Refused=>3,FixtureCacheStateBoundaryV1::AnalysisLimited=>4,FixtureCacheStateBoundaryV1::InternalPoisoned=>5,FixtureCacheStateBoundaryV1::ApplicabilityUnavailable=>6};',
  'let r=match v.reason(){FixtureCacheStateReasonV1::Observed=>0,FixtureCacheStateReasonV1::Steps=>1,FixtureCacheStateReasonV1::FramingUnavailable=>2,FixtureCacheStateReasonV1::FramingInvalid=>3,FixtureCacheStateReasonV1::EnvelopeRefused=>4,FixtureCacheStateReasonV1::EnvelopeUnavailable=>5,FixtureCacheStateReasonV1::Identity=>6,FixtureCacheStateReasonV1::Resident=>7,FixtureCacheStateReasonV1::Plan=>8,FixtureCacheStateReasonV1::Victim=>9,FixtureCacheStateReasonV1::Bytes=>10,FixtureCacheStateReasonV1::Token=>11,FixtureCacheStateReasonV1::Nonce=>12,FixtureCacheStateReasonV1::Invariant=>13,FixtureCacheStateReasonV1::FailureApplicability=>14,FixtureCacheStateReasonV1::IncompleteBoundary=>15,FixtureCacheStateReasonV1::InternalPoison=>16,FixtureCacheStateReasonV1::OutputUnavailable=>17};',
  '[b,r,v.observed_records(),v.cache_state_records(),v.stop_record(),v.last_sequence(),v.last_work(),v.last_instructions(),v.active_operation(),v.requested_function(),v.resident_count(),v.resident_bytes(),v.held_pins(),v.next_nonce(),v.active_plan_cell(),v.selected_mask(),v.taken_mask(),v.committed_mask(),v.pending_victim(),v.destination(),v.failure_coordinate(),v.semantic_debit(),v.semantic_setup_paid(),v.semantic_finish_paid(),v.fixture_state_observed(),v.tail_unknown(),u64::from(v.stored_prefix_validated()),u64::from(v.full_replay_accepted()),u64::from(v.semantic_metrics_valid()),u64::from(v.real_binding_verified()),v.reserved0(),v.reserved1()]}',
  'pub(crate) fn run(){',
  'let f=Fixture{cap:4,mask:33,extent:4096,types:2,slots:3,pins:3,base:0,capacity:10,entry:10};',
  'let paid=Paid{setup:1,finish:1,records:4};',
  'let mut s=Framing::new(4);s.framed=4;s.last_work=20;s.last_instructions=30;s.last_operation=2;s.flags=1;s.complete=true;',
  'let input:Result<bool,AnalyzerError>=Ok(true);']
 for c in cases:
  q=c['q'];stage=q[3]
  body+=['{',f'let q:[u64;16]={q!r};',
   'let p=Progress{calls:4,latch:0,q};',
   f'let env=FixtureEnvelopeObservationV1{{boundary:FixtureEnvelopeBoundaryV1::CapCutUnknownTail,reason:FixtureEnvelopeReasonV1::Observed,observed_records:4,state:{stage},phase:0,mask:1,last_operation:2,active_operation:2,requested_function:513,pin_failure:0,terminal_failure:0,last_work:20,last_instructions:30,envelope_debit:2281,full_replay_accepted:0,stored_prefix_validated:0}};',
   'let valid=shape_q(&p.q,p.calls,p.terminal(),s.framed,&f);',
   'let observed=projection(&p,&paid,&s,&input,&env,Some(&f));',
   'println!("{{\\"id\\":\\"'+c['id']+'\\",\\"shape_guard\\":{},\\"words\\":{:?}}}",valid,words(&observed));','}']
 body+=['}'];(OUT/'reviewer_private.rs').write_text('\n'.join(body)+'\n')
 deltas={
  'analyzer.rs':'\nfn main(){fixture_envelope::independent_review_run();}\n',
  'envelope.rs':'\npub(crate) fn independent_review_run(){cache_state::independent_review::run();}\n',
  'cache_state.rs':'\n#[path="reviewer_private.rs"]\npub(super) mod independent_review;\n'}
 put('delta.json',{'baseline_sha256':source_hashes,'append_only_utf8':deltas,
  'additional_file':'reviewer_private.rs','additional_file_sha256':sha((OUT/'reviewer_private.rs').read_bytes()),
  'compile_plan':'Direct rustc --edition=2021 analyzer.rs -o owned-private-guard-binary; default bin crate; no --test and no --cfg test. Existing producer/old test modules remain disabled.',
  'product_originals_changed':False,'public_library_API_added':False,
  'visibility':'Only crate/super-visible entrypoints in the separately instrumented binary overlay; product library source/exports untouched.',
  'execution_authorized':False})
 qnames=['M','work','instructions','stage','operation','function','resident_count','resident_bytes','held_pins','next_nonce','selected','taken','committed','pending','destination','feasible']
 arena={6:21,7:22,8:23,9:17,10:128,11:130,12:131,13:137,14:84,15:141}
 put('source-index-mapping.json',{'source_sha256':source_hashes['cache_state.rs'],'Progress_q':[
  {'index':i,'name':n,'arena_scalar_index_if_mirrored':arena.get(i)} for i,n in enumerate(qnames)],
  'actual_source_spans':{'q_layout':'cache_state.rs8-13,105-109','guard':'cache_state.rs195-231',
   'unconditional_masks':'cache_state.rs210-214','pending_guard':'cache_state.rs216-218',
   'projection':'cache_state.rs896-1066','committed_q_capture':'cache_state.rs1170-1193'},
  'machine_table_sha256':sha(raw),'machine_guard_Q9':t['exact_snapshot_guard_expressions']['Q9_pending'],
  'machine_guard_Q10':t['exact_snapshot_guard_expressions']['Q10_inactive'],
  'scope':'No arena or Candidate state is injected; only exact private Progress/child/config finalizer inputs are deliberately constructed.'})
 files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in ['proposal-seal.json','proposal-seal.sha256'])
 members=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in files]
 seal={'schema':1,'scope':'seven proposed private seeded finalizer/shape witnesses; no execution authorization',
  'members':members,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members)}
 put('proposal-seal.json',seal);digest=sha((OUT/'proposal-seal.json').read_bytes());(OUT/'proposal-seal.sha256').write_text(digest+'  proposal-seal.json\n')
 print(json.dumps({'proposal_seal':digest,'members':len(members),'bytes':seal['member_bytes'],'cases':len(cases),'machine_table_sha256':sha(raw),'executions':0}))
if __name__=='__main__':main()
