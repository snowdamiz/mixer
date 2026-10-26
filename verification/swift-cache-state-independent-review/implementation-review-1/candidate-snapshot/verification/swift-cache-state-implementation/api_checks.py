#!/usr/bin/env python3
import json,pathlib,shutil,sys
from run_host import ROOT,REPO,RUST,run,sha
API=ROOT/'api';API.mkdir(exist_ok=True)
probes={
'positive':'use cache_fixture::*; fn main(){ fn accepts(_:fn(&mut std::fs::File,&mut std::fs::File,&mut std::fs::File,&mut std::fs::File)->Result<FixtureCacheStateOutcomeV1,AnalyzerError>){} accepts(analyze_fixture_cache_state_v1); assert_eq!(std::mem::size_of::<FixtureCacheStateOutcomeV1>(),488);}',
'raw_record':'use cache_fixture::*;fn main(){let _=FixtureDecodedRecordV1{words:&[0;16]};}',
'loan':'use cache_fixture::*;fn main(){let _=Loan{record:(),config:()};}',
'candidate':'use cache_fixture::*;fn main(){let _:Candidate2048=[0;2048];}',
'receipt':'use cache_fixture::*;fn main(){let _=Paid{setup:1,finish:1,records:0};}',
'authority_boolean':'use cache_fixture::*;fn main(){let _=analyze_fixture_cache_state_v1(true,true,true,true);}',
'fd_adoption':'use cache_fixture::*;fn main(){let _=analyze_fixture_cache_state_v1(0,1,2,3);}',
'state_seed':'use cache_fixture::*;fn main(){let _=FixtureCacheStateOutcomeV1::from_state([0u64;32]);}',
'aggregate_fields':'use cache_fixture::*;fn f(x:FixtureCacheStateOutcomeV1){let _=x.cache_state;}fn main(){}',
'observation_fields':'use cache_fixture::*;fn f(x:FixtureCacheStateObservationV1){let _=x.extent;}fn main(){}',
'copy_aggregate':'use cache_fixture::*;fn need<T:Copy>(){}fn main(){need::<FixtureCacheStateOutcomeV1>();}',
'clone_aggregate':'use cache_fixture::*;fn need<T:Clone>(){}fn main(){need::<FixtureCacheStateOutcomeV1>();}',
'copy_observation':'use cache_fixture::*;fn need<T:Copy>(){}fn main(){need::<FixtureCacheStateObservationV1>();}',
'clone_observation':'use cache_fixture::*;fn need<T:Clone>(){}fn main(){need::<FixtureCacheStateObservationV1>();}',
'old_cache_activation':'use cache_fixture::*;fn f(x:FixtureEnvelopeOutcomeV1){let _=x.cache_state();}fn main(){}',
'public_words':'use cache_fixture::*;fn f(x:&FixtureCacheStateObservationV1){let _=x.words();}fn main(){}',
}
lib=ROOT/'evidence/libcache_fixture.rlib'
r=run('api-library',[RUST,'--edition=2021','--crate-type=lib','--crate-name','cache_fixture',ROOT/'source/library/analyzer.rs','-o',lib]);assert r.returncode==0
results=[]
for name,body in probes.items():
 p=API/f'{name}.rs';p.write_text(body+'\n');out=API/f'{name}.binary'
 r=run('api-'+name,[RUST,'--edition=2021','--extern',f'cache_fixture={lib}',p,'-o',out]);expected=name=='positive';assert (r.returncode==0)==expected
 if expected:assert run('api-positive-execute',[out]).returncode==0
 out.unlink(missing_ok=True);results.append({'name':name,'source_sha256':sha(p),'compile_success':r.returncode==0,'expected_success':expected})
(ROOT/'evidence/api-summary.json').write_text(json.dumps({'probes':results,'independent_acceptance':False},indent=2)+'\n')
lib.unlink()
