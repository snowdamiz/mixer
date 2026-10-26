"""Reviewer-only fixture/API protocol support; never opens producer source."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PRE=HERE.parent/'preaccess'
ROOT_RECEIPTS={
 'implementation-selection.json':'012ef007459aa8561da2f3542902b6f4193c8ac06c5c325944502042103acad3',
 'public-getter-selection.json':'80b8b39365e137f5f4db13f8a8348ca79aa17eb5abadf58ac929e3d25aec92e1'}
def sha(b): return hashlib.sha256(b).hexdigest()
def put(name,v):
 p=HERE/name; p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')

def main():
 selected=[]
 for name,expected in ROOT_RECEIPTS.items():
  path=ROOT/'verification/swift-semantic-adapter-root-review'/name
  raw=path.read_bytes()
  if sha(raw)!=expected: raise ValueError('root receipt changed')
  target=HERE/'inputs'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
  selected.append({'path':str(path.relative_to(ROOT)),'snapshot':str(target.relative_to(HERE)),
   'bytes':len(raw),'sha256':expected})
 seal=PRE/'seal.json'
 if sha(seal.read_bytes())!='1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c': raise ValueError('preaccess seal')
 upstream=json.loads(seal.read_text())
 for member in upstream['members']:
  raw=(ROOT/member['path']).read_bytes()
  if len(raw)!=member['bytes'] or sha(raw)!=member['sha256']: raise ValueError('preaccess member drift')
 api=json.loads((HERE/'inputs/public-getter-selection.json').read_text())
 schema=json.loads((PRE/'fixtures/schema.json').read_text())
 words=schema['observation_words']
 expected=set(api['observation_u64_getters'])|set(api['observation_literal_false_getters'])|{'boundary','reason'}
 if set(words)!=expected or len(words)!=32: raise ValueError('coordinated getter closure')
 for name,expected in [('13-analyzer.rs','1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b'),
  ('14-envelope.rs','2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef')]:
  p=PRE/'inputs/verification/swift-semantic-adapter-prerequisite/inputs'/name; raw=p.read_bytes()
  if sha(raw)!=expected: raise ValueError('old API reference')
  target=HERE/'inputs'/name; target.write_bytes(raw)
  selected.append({'path':str(p.relative_to(ROOT)),'snapshot':str(target.relative_to(HERE)),
   'bytes':len(raw),'sha256':expected,'scope':'immutable API reference only; not compiled/imported/executed'})
 put('inputs/custody.json',{'root_receipts_and_API_references':selected,
  'preaccess_seal_sha256':sha(seal.read_bytes()),'preaccess_members':len(upstream['members']),
  'preaccess_bytes':upstream['member_bytes'],'producer_source_accessed':False})

 # Completely self-owned protocol stub: it intentionally does not parse the
 # fixture format, check semantics, reproduce an old model, or claim ABI sizes.
 # Its byte inputs are five-byte protocol controls, never MIXFIX01 fixtures.
 lines=['//! Self-owned driver protocol stub. ZERO product/cache semantics.',
  '#![forbid(unsafe_code)]','#![allow(dead_code)]',
  'use std::fs::File; use std::io::{Read,Write};',
  'pub struct AnalyzerError { pub code:u32,pub stage:u32,pub offset:u64,pub record:u64,pub reserved:u64 }',
  'pub enum Decision { Invalid, AnalysisLimited, Unavailable }',
  'pub struct ReplayOutcome { pub decision:Decision,pub framed_records:u64,pub physical_records:u64,pub report_bytes:u64,pub steps_used:u64,pub input_bytes_read:u64,pub input_attempts:u64,pub output_attempts:u64,pub observation:AnalyzerError }',
  'impl ReplayOutcome { pub fn fixture_framing_observed(&self)->bool{true} pub fn stored_prefix_validated(&self)->bool{false} pub fn full_replay_accepted(&self)->bool{false} }',
  'pub enum FixtureEnvelopeBoundaryV1 { Unavailable,ClosedEnvelopeObserved,CapCutUnknownTail,Refused,AnalysisLimited,InternalPoisoned }',
  'pub enum FixtureEnvelopeReasonV1 { Observed,Steps,Shape,Coordinate,TerminalPhase,Phase,ReleaseOpen,TerminalFailure,PinFailure,ForbiddenResume,Acquire,Identity,Stage,PublicationForm,CheckedAccess,InternalPoisoned,FramingUnavailable,FramingInvalid,FramingLimited,EnvelopeUnavailable,UnavailableState,IncompleteBoundary }',
  'pub struct FixtureEnvelopeObservationV1 { b:FixtureEnvelopeBoundaryV1,r:FixtureEnvelopeReasonV1,w:[u64;16] }',
  'pub struct FixtureEnvelopeOutcomeV1 { f:ReplayOutcome,e:FixtureEnvelopeObservationV1 }',
  'impl FixtureEnvelopeObservationV1 { pub fn boundary(&self)->&FixtureEnvelopeBoundaryV1{&self.b} pub fn reason(&self)->&FixtureEnvelopeReasonV1{&self.r}']
 env_names=['observed_records','state','phase','mask','last_operation','active_operation',
  'requested_function','pin_failure','terminal_failure','last_work','last_instructions','envelope_debit']
 lines += [f'pub fn {name}(&self)->u64{{self.w[{i+2}]}}' for i,name in enumerate(env_names)]
 lines += ['pub fn stored_prefix_validated(&self)->bool{false} pub fn full_replay_accepted(&self)->bool{false} pub fn semantic_metrics_valid(&self)->bool{false} }']
 for type_name,key in [('FixtureCacheStateBoundaryV1','boundary_ids'),('FixtureCacheStateReasonV1','reason_ids')]:
  variants=sorted(api[key],key=api[key].get)
  lines += [f'pub enum {type_name} {{'+','.join(variants)+'}',
   f'fn make_{key}(n:u8)->{type_name}{{match n{{'+','.join(f'{api[key][v]}=>{type_name}::{v}' for v in variants)+',_=>panic!("protocol control out of range")}}']
 lines += ['pub struct FixtureCacheStateObservationV1 { b:FixtureCacheStateBoundaryV1,r:FixtureCacheStateReasonV1,w:[u64;32] }',
  'impl FixtureCacheStateObservationV1 { pub fn boundary(&self)->&FixtureCacheStateBoundaryV1{&self.b} pub fn reason(&self)->&FixtureCacheStateReasonV1{&self.r}']
 lines += [f'pub fn {name}(&self)->u64{{self.w[{words.index(name)}]}}' for name in api['observation_u64_getters']]
 lines += [f'pub fn {name}(&self)->bool{{self.w[{words.index(name)}]!=0}}' for name in api['observation_literal_false_getters']]
 lines += ['}',
  'pub struct FixtureCacheStateOutcomeV1 { f:ReplayOutcome,e:FixtureEnvelopeObservationV1,c:FixtureCacheStateObservationV1,a:bool }',
  'impl FixtureCacheStateOutcomeV1 { pub fn framing(&self)->&ReplayOutcome{&self.f} pub fn envelope(&self)->&FixtureEnvelopeObservationV1{&self.e} pub fn cache_state(&self)->&FixtureCacheStateObservationV1{&self.c}']
 lines += [f'pub fn {name}(&self)->bool{{self.a}}' for name in api['aggregate_literal_false_getters']]
 lines += ['}',
  'pub fn analyze_fixture_cache_state_v1(_s:&mut File,_p:&mut File,c:&mut File,o:&mut File)->Result<FixtureCacheStateOutcomeV1,AnalyzerError>{',
  'let mut control=[0u8;5]; c.read_exact(&mut control).expect("protocol five bytes");',
  'if control[0]==0 { o.write_all(b"partial").expect("protocol output"); return Err(AnalyzerError{code:6,stage:8,offset:23,record:17,reserved:0}); }',
  'let a=control[3]!=0; let mut w=[0u64;32]; for i in 2..26 {w[i]=1000+i as u64;} for i in 26..30 {w[i]=u64::from(a);}',
  'if control[0]==2 {o.write_all(b"short").expect("protocol output");}else{o.write_all(&vec![0x3bu8;49152]).expect("protocol output");}',
  'Ok(FixtureCacheStateOutcomeV1{f:ReplayOutcome{decision:Decision::Unavailable,framed_records:71,physical_records:72,report_bytes:49152,steps_used:73,input_bytes_read:74,input_attempts:75,output_attempts:76,observation:AnalyzerError{code:15,stage:3,offset:77,record:78,reserved:0}},',
  'e:FixtureEnvelopeObservationV1{b:FixtureEnvelopeBoundaryV1::CapCutUnknownTail,r:FixtureEnvelopeReasonV1::Observed,w:[0,0,202,203,204,205,206,207,208,209,210,211,212,213,0,0]},',
  'c:FixtureCacheStateObservationV1{b:make_boundary_ids(control[1]),r:make_reason_ids(control[2]),w},a})}']
 (HERE/'protocol_stub.rs').write_text('\n'.join(lines)+'\n')
 probes=[
  ('copy-aggregate','fn demand<T:Copy>(){} fn main(){demand::<api::FixtureCacheStateOutcomeV1>();}',False),
  ('clone-aggregate','fn demand<T:Clone>(){} fn main(){demand::<api::FixtureCacheStateOutcomeV1>();}',False),
  ('copy-observation','fn demand<T:Copy>(){} fn main(){demand::<api::FixtureCacheStateObservationV1>();}',False),
  ('clone-observation','fn demand<T:Clone>(){} fn main(){demand::<api::FixtureCacheStateObservationV1>();}',False),
  ('no-words-accessor','fn probe(v:&api::FixtureCacheStateObservationV1){let _=v.words();} fn main(){}',False),
  ('no-public-constructor','fn main(){let _=api::FixtureCacheStateObservationV1{};}',False),
  ('no-public-record','use api::FixtureDecodedRecordV1; fn main(){}',False),
  ('no-public-candidate','use api::Candidate2048; fn main(){}',False),
  ('no-public-budget','use api::StepBudget; fn main(){}',False),
  ('no-public-progress','use api::FixtureCacheStateProgressV1; fn main(){}',False),
  ('no-public-receipt','use api::FixtureCacheStateReceiptV1; fn main(){}',False),
  ('no-raw-fd','fn probe(a:i32,b:i32,c:i32,d:i32){let _=api::analyze_fixture_cache_state_v1(a,b,c,d);} fn main(){}',False),
  ('no-acceptance-boolean','fn probe(a:&mut std::fs::File,b:&mut std::fs::File,c:&mut std::fs::File,d:&mut std::fs::File){let _=api::analyze_fixture_cache_state_v1(a,b,c,d,true);} fn main(){}',False),
  ('no-old-semantic-accessor','fn probe(v:&api::ReplayOutcome){let _=v.cache_state();} fn main(){}',False),
  ('borrowed-positive','fn probe(v:&api::FixtureCacheStateOutcomeV1){let _: &api::ReplayOutcome=v.framing();let _: &api::FixtureEnvelopeObservationV1=v.envelope();let _: &api::FixtureCacheStateObservationV1=v.cache_state();} fn main(){}',True),
 ]
 manifests=[]
 for name,body,success in probes:
  p=HERE/'api-probes'/(name+'.rs'); p.parent.mkdir(exist_ok=True)
  p.write_text('#![forbid(unsafe_code)]\nextern crate mixer_fixture_cache_state as api;\n'+body+'\n')
  manifests.append({'id':name,'path':str(p.relative_to(HERE)),'compile_success_expected':success,'sha256':sha(p.read_bytes()),
   'product_meaning':'pending actual candidate compilation; stub result only tests tooling protocol'})
 put('api-probes/manifest.json',manifests)
 put('driver-schema.json',{'protocol':1,'cache_state_words':words,
  'framing_words':['decision','framed_records','physical_records','report_bytes','steps_used','input_bytes_read',
   'input_attempts','output_attempts','error_code','error_stage','error_offset','error_record','error_reserved',
   'fixture_framing_observed','stored_prefix_validated','full_replay_accepted'],
  'envelope_words':['boundary','reason','observed_records','state','phase','mask','last_operation','active_operation',
   'requested_function','pin_failure','terminal_failure','last_work','last_instructions','envelope_debit','full_replay_accepted','stored_prefix_validated'],
  'error_words':['code','stage','offset','record','reserved'],
  'layouts':['ReplayOutcome','FixtureEnvelopeObservationV1','FixtureEnvelopeOutcomeV1',
   'FixtureCacheStateObservationV1','FixtureCacheStateOutcomeV1','Result<FixtureCacheStateOutcomeV1,AnalyzerError>'],
  'outer_Err':'no framing/envelope/aggregate/cache observation; retain exact five error words and partial report bytes',
  'stub_scope':'five-byte controls, arbitrary counters/report pattern, no MIXFIX01 parsing or cache semantics; no ABI/product qualification'})
 print(json.dumps({'preaccess_members_verified':173,'getter_words':len(words),'API_probe_sources':len(probes),
  'candidate_source_accessed':False,'candidate_Rust_semantic_executions':0}))

if __name__=='__main__': main()
