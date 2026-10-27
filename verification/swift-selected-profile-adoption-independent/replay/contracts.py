#!/usr/bin/env python3
"""Fresh bounded source-only compiler controls against the selected source."""
from pathlib import Path
import json,shutil,sys
sys.dont_write_bytecode=True
import evidence as E
HERE=E.HERE;CASES=HERE/'compile_cases';CASES.mkdir(exist_ok=True)
NEW={
 'adoption_positive':('''use super::retained_profile_loader_v1::{SelectedValidatedProfileV1,LoaderProvenanceV1};use super::control::{RuntimeControl,AdoptedProof,SwiftRunBudget,SwiftRunFailure};use crate::Cancellation;use std::time::Instant;fn consume(p:SelectedValidatedProfileV1)->Result<(RuntimeControl,AdoptedProof),SwiftRunFailure>{p.adopt(SwiftRunBudget::default(),Instant::now(),Cancellation::default())}fn borrow(p:&AdoptedProof)->Option<&LoaderProvenanceV1>{p.selected_provenance()}''',None),
 'body_literal':('''use super::retained_profile_loader_v1::AdoptionBodyV1;use super::ValidatedSwiftReactor;fn forge(proof:ValidatedSwiftReactor){let _=AdoptionBodyV1{proof,selected:None};}''','private'),
 'carrier_clone':('''use super::retained_profile_loader_v1::SelectedValidatedProfileV1;fn f(p:SelectedValidatedProfileV1){let _=p.clone();}''','E0599'),
 'body_parts':('''use super::retained_profile_loader_v1::AdoptionBodyV1;fn f(p:AdoptionBodyV1){let _=p.into_parts();}''','E0599'),
 'carrier_parts':('''use super::retained_profile_loader_v1::SelectedValidatedProfileV1;fn f(p:SelectedValidatedProfileV1){let _=p.into_parts();}''','E0599'),
 'body_proof_extraction':('''use super::retained_profile_loader_v1::AdoptionBodyV1;fn f(p:AdoptionBodyV1){let _=p.into_proof();}''','E0599'),
 'provenance_owned_escape':('''use super::retained_profile_loader_v1::LoaderProvenanceV1;use super::control::AdoptedProof;fn f(p:AdoptedProof)->Option<&'static LoaderProvenanceV1>{p.selected_provenance()}''','E0515'),
 'provenance_mutable_borrow':('''use super::retained_profile_loader_v1::LoaderProvenanceV1;use super::control::AdoptedProof;fn f(p:&mut AdoptedProof){let _:&mut LoaderProvenanceV1=p.selected_provenance().unwrap();}''','E0308'),
 'provenance_private_fields':('''use super::control::AdoptedProof;fn f(p:&AdoptedProof){let q=p.selected_provenance().unwrap();let _=q.source;}''','E0616'),
 'body_private_replacement':('''use super::control::AdoptedProof;use super::retained_profile_loader_v1::AdoptionBodyV1;fn f(p:&mut AdoptedProof,q:AdoptionBodyV1){p.body=q;}''','E0616'),
 'owner_drop_while_provenance_borrowed':('''use super::control::{RuntimeControl,AdoptedProof};use super::retained_profile_loader_v1::LoaderProvenanceV1;fn f(c:&mut RuntimeControl,p:AdoptedProof){let q=p.selected_provenance();let _=c.drop_proof(p);let _:Option<&LoaderProvenanceV1>=q;}''','E0505'),
 'no_boolean_selected_mint':('''use super::retained_profile_loader_v1::AdoptionBodyV1;use super::ValidatedSwiftReactor;fn f(p:ValidatedSwiftReactor){let _=AdoptionBodyV1::selected(p,true);}''','E0599'),
 'no_digest_selected_mint':('''use super::retained_profile_loader_v1::SelectedValidatedProfileV1;use super::ValidatedSwiftReactor;fn f(p:ValidatedSwiftReactor){let _=SelectedValidatedProfileV1::new(p,[0u8;32]);}''','E0599'),
}
def main():
 mode=sys.argv[1];group=int(sys.argv[2]);names=list(NEW)
 if group<2:
  chosen=names[group*7:(group+1)*7]
  cases=[(name,NEW[name][0],NEW[name][1],'sibling')for name in chosen]
 elif group in [2,5]:
  originals=[('positive',None),('clone','E0599'),('private_proof','E0616'),('private_provenance','E0616'),('literal','private'),('source_escape','E0515'),('source_mutation','E0594'),('raw_proof_mint','E0308'),('deserialize','E0599')]
  packet=HERE.parent/'swift-real-profile-loader-binding/compile_cases'
  cases=[('original-'+name,(packet/(name+'.rs')).read_text(),diagnostic,'sibling')for name,diagnostic in (originals[:5]if group==2 else originals[5:])]
 else:
  old=[('positive_contract','descendant',None),('positive_contract','cache-sibling',None),('guard_literal_from_sibling','cache-sibling','E0603'),('external_selection_literal','cache-sibling','E0603'),('guard_escape','descendant','lifetime may not live long enough'),('proof_escape','descendant','lifetime may not live long enough'),('cache_move','descendant','E0505'),('cache_mutation','descendant','E0502'),('control_mutation','descendant','E0502'),('row_foreign_snapshot','descendant','E0061'),('callback_reentry','descendant','E0308')]
  part=old[(group-3)*6:(group-2)*6]
  cases=[('guard-'+placement+'-'+name,(HERE/'host/compile_cases'/(name+'.rs')).read_text(),diag,placement)for name,placement,diag in part]
 records=[]
 for name,text,diagnostic,placement in cases:
  fixture=CASES/(name+'.rs');fixture.write_text(text+'\n')
  variant=E.WORK/(mode+'-contract-'+name);shutil.copytree(E.SOURCE,variant)
  if placement=='sibling':path='src/experimental_swift_reactor/mod.rs'
  elif placement=='cache-sibling':path='src/experimental_swift_reactor/cache.rs'
  else:path='src/experimental_swift_reactor/cache/initial_profile_v1/compile_contracts.rs'
  delta='\n#[cfg(test)] mod selected_adoption_compile_case { include!(env!("MIXER_ADOPTION_COMPILE_CASE")); }\n'if placement!='descendant'else'\ninclude!(env!("MIXER_ADOPTION_COMPILE_CASE"));\n'
  target=variant/path;target.write_text(target.read_text()+delta)
  environment=E.cleanenv()|{'CARGO_MANIFEST_DIR':str(variant),'MIXER_ADOPTION_COMPILE_CASE':str(fixture)}
  record={'name':name,'mode':mode,'fixture':E.ident(fixture),'source':E.manifest(E.SOURCE),'variant':E.manifest(variant),'append_path':path,'append_bytes':delta,'expected_diagnostic':diagnostic}
  E.write(HERE/'compiler-variants'/(mode+'-'+name+'.json'),record)
  try:E.run('contract-'+mode+'-'+name,E.flags(mode)+(['--cfg','mixer_initial_profile_external_contract']if placement=='cache-sibling'else[])+['--test','--emit=metadata',variant/'src/lib.rs','-o',E.WORK/'contract.rmeta'],environment,expected=diagnostic)
  finally:shutil.rmtree(variant)
  records.append(record)
 print(json.dumps({'mode':mode,'group':group,'controls':len(records)}))
if __name__=='__main__':main()
