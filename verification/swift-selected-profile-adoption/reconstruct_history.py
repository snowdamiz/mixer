#!/usr/bin/env python3
"""Retain exact earlier source bytes and correct early current-tree attribution."""
from pathlib import Path
import json,shutil,sys
sys.dont_write_bytecode=True
import evidence as E
R=E.HERE;BASE=R/'source-preimages/pre-comment-final-source'
expected={
 'pre-comment':'6049c2ac18cca2db43068c42a86d1b84f9f7c28dfcec595986603e533078ee69',
 'admission-test-first':'82b577f5d5b064d6f34264e1f68704f1a5a7bc781ec4bff0a65580d3268e9e6f',
 'prior-runtime-matrix':'8d18ee9d36352784f0ed476888385c4335ca57f284b639e9c891c729e6ac0bcc',
 'narrow-failure-current-tree':'70a56603718df8374fe4a76eb0813437e0ecc71855ab3abfb46fb596f6c7a225',
 'first-migrated-layout':'fd969b591b3e42f1744ba1c262bf7848a7733656a60034502c0d5a0b42dfafe2',
 'discovery':'b6dbcb1011c297ed5724815b7f3071cbdde2650fa49c2a97d62406d38b0fcbf3',
}
records=[]
def save(name,source):
 manifest=E.manifest(source);assert manifest['tree_sha256']==expected[name],(name,manifest['tree_sha256'])
 E.write(R/'source-history-manifests'/(name+'.json'),manifest)
 records.append({'stage':name,'path':str(source.relative_to(R)),'tree_sha256':manifest['tree_sha256']})
def main():
 save('pre-comment',BASE);save('discovery',R/'source-preimages/layout-discovery-source')
 scratch=R/'source-preimages/history-work';assert not scratch.exists();shutil.copytree(BASE,scratch)
 test=scratch/'src/experimental_swift_reactor/cache/initial_profile_v1/tests.rs'
 text=test.read_text();chronology=''' let chronology=match case {"selection"=>[0;5],"preparation"=>[1,0,0,0,0],
  "encoded"=>[1,1,1,1,1],_=>[1,1,1,0,0]};
 assert_eq!(COUNTERS.with(Cell::get),chronology);
''';assert text.count(chronology)==1;text=text.replace(chronology,'')
 text=text.replace('let expected_kind=match field {"source"|"metadata"=>SwiftRunFailureKind::Adoption,','let expected_kind=match field {"source"|"metadata"=>SwiftRunFailureKind::CategoryExhausted,');test.write_text(text)
 destination=R/'source-preimages/historical-admission-first';shutil.copytree(scratch,destination);save('admission-test-first',destination)
 start=text.index(' if let Some(field)=case.strip_prefix("admission-") {');end=text.index(' let fault=match case',start);text=text[:start]+text[end:];test.write_text(text)
 destination=R/'source-preimages/historical-prior-runtime';shutil.copytree(scratch,destination);save('prior-runtime-matrix',destination)
 start=text.index(' // The original300000 grant now honestly refuses');end=text.index(' let (mut control,adopted)=adopt(budget);let selection=alternative(budget);let mut cache=None;let mut output=file("prepare-capacity.rows");',start);text=text[:start]+text[end:];test.write_text(text)
 destination=R/'source-preimages/historical-narrow-current';shutil.copytree(scratch,destination);save('narrow-failure-current-tree',destination)
 assert text.count('let expected=95152+slots')==1;text=text.replace('let expected=95152+slots','let expected=92128+slots');test.write_text(text)
 cache=scratch/'src/experimental_swift_reactor/cache_tests.rs';text=cache.read_text();new='''        + super::execution::CONSTRUCTION_BOOTSTRAP_BYTES
        + super::retained_profile_loader_v1::ADOPTION_ENTRY_BYTES_V1
        + super::retained_profile_loader_v1::ADOPTION_MOVE_BYTES_V1
        + ADOPTION_CLEANUP_BYTES_V1
        + super::cache::INITIAL_PROFILE_WRAPPER_SOURCE_PLACES_V1;''';assert text.count(new)==1;cache.write_text(text.replace(new,'        + super::execution::CONSTRUCTION_BOOTSTRAP_BYTES;'))
 destination=R/'source-preimages/historical-first-migrated';shutil.copytree(scratch,destination);save('first-migrated-layout',destination);shutil.rmtree(scratch)
 E.write(R/'historical-source-custody.json',{'schema':1,'exact_tree_digests_checked':records,'early_receipt_correction':{'scope':'early runner recorded current source tree at command completion, before explicit executed-artifact/compiled-context fields were added','affected_runtime_failure':'debug-canonical_ceilings_and_prepare_capacity','receipt_current_tree':expected['narrow-failure-current-tree'],'actual_executed_binary_source_tree':expected['first-migrated-layout'],'evidence':'same already-built unit-debug binary as preceding all64-pair failure; no compile occurred between those two failures','final_matrix_uses_explicit_compiled_context':True},'no_historical_failure_reclassified_as_pass':True})
 print(json.dumps({'exact_historical_source_snapshots':len(records),'all_claimed_tree_digests_matched':True}))
if __name__=='__main__':main()
