#!/usr/bin/env python3
"""Append-only source/build-artifact audit; executes test discovery only."""
from pathlib import Path
import datetime,hashlib,json,re,subprocess,tarfile
out=Path(__file__).resolve().parent;base=out.parent;root=base.parents[1]
producer=root/'verification/swift-executor-construction/candidate-4'
correction=root/'verification/swift-executor-construction/target-isolation-correction'
clean=root/'verification/swift-executor-construction-root-review/candidate4-clean'
logs=out/'logs';logs.mkdir(exist_ok=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
original=json.loads((base/'seal.json').read_text())
assert sha(base/'seal.json')=='81e5c76ec4f169978e9bed534c4b22bc97788dbd585a62d7af3432655a9a5099'
for row in original['files']:assert sha(base/row['path'])==row['sha256'],('original sealed evidence changed',row['path'])
observations=json.loads((correction/'observations.json').read_text());resolution=json.loads((correction/'resolution.json').read_text())
for name,digest in observations['preserved_candidate4_files'].items():assert sha(producer.parent/name)==digest,name
for name,digest in resolution['artifacts'].items():assert sha(producer.parent/name)==digest,name
synthetic=json.loads((correction/'synthetic/receipt.json').read_text())
for command in synthetic['commands']:
 assert sha(Path(command['log']))==command['log_sha256']
 witness=command['test_binary_witness'];assert sha(Path(witness['executable']))==witness['sha256'];assert sha(Path(witness['list_log']))==witness['list_log_sha256']
 assert witness['derived_probe_present']==(witness['snapshot_kind']=='derived_metadata')
 assert Path(witness['executable']).resolve().is_relative_to(Path(witness['target_dir']).resolve())
for profile in ['debug','release']:
 by_name={r['name']:r['test_binary_witness']for r in synthetic['commands']}
 assert by_name['product-before-'+profile]['sha256']==by_name['product-after-'+profile]['sha256']
 assert by_name['product-after-'+profile]['target_dir']!=by_name['metadata-'+profile]['target_dir']
 assert any(row.get('profile')==profile and row.get('metadata_probe_in_product_target_rejected')for row in synthetic['negative_checks'])
assert any(row.get('reused_target_roots_rejected')for row in synthetic['negative_checks'])
qualification=json.loads((clean/'qualification.json').read_text());assert qualification['status']=='passed-uninstrumented-full-host-regression'
collector=root/'verification/swift-executor-construction-root-review/qualify_candidate4.py'
assert sha(collector)==qualification['collectorSHA256']
assert sha(producer/'receipt.json')==qualification['producerReceiptSHA256']
assert sha(producer/'frozen-source.tar.gz')==qualification['archiveSHA256']
assert sha(producer/'source-manifest.json')==qualification['sourceManifestSHA256']
manifest=json.loads((producer/'source-manifest.json').read_text());assert len(manifest)==qualification['sourceFileCount']==425
source=Path(qualification['commands'][0]['cwd']);target=Path(qualification['commands'][0]['cargoTargetDirectory'])
actual={str(path.relative_to(source)):sha(path)for path in source.rglob('*')if path.is_file()};assert actual==manifest
with tarfile.open(producer/'frozen-source.tar.gz')as archive:
 actual_archive={m.name.removeprefix('vm/'):hashlib.sha256(archive.extractfile(m).read()).hexdigest()for m in archive.getmembers()if m.isfile()};assert actual_archive==manifest
for command in qualification['commands']:
 assert command['exit']==0 and command['sourceBeforeAfterVerified']
 assert Path(command['cwd'])==source and Path(command['cargoTargetDirectory'])==target
 assert sha(root/command['log'])==command['sha256']
 if command['argv'][:2]==['cargo','test']:
  assert '--lib' not in command['argv'] and '--all-features' in command['argv']
  assert Path(command['argv'][command['argv'].index('--target-dir')+1])==target
  assert Path(command['argv'][command['argv'].index('--manifest-path')+1]).parent==source
for profile in ['debug','release']:
 text=(clean/('full-'+profile+'.log')).read_text();counts=[tuple(map(int,m))for m in re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',text)]
 assert len(counts)==35 and counts[0]==(151,0,0)
 assert sum(r[0]for r in counts)==366 and sum(r[1]for r in counts)==0 and sum(r[2]for r in counts)==9
 assert 'frozen_construction_metadata' not in text
record=[];lists={}
def direct_list(name,binary,cwd,expected_hash=None):
 before=sha(binary)
 if expected_hash:assert before==expected_hash,(name,before,expected_hash)
 args=[str(binary),'--list'];started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 result=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 assert result.returncode==0;assert sha(binary)==before
 log=logs/(name+'.log');log.write_text(result.stdout)
 tests=[line.removesuffix(': test')for line in result.stdout.splitlines()if line.endswith(': test')]
 record.append({'name':name,'argv':args,'cwd':str(cwd),'exit_code':result.returncode,'started_utc':started,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'executable_sha256_before_after':before,'test_count':len(tests),'output':str(log.relative_to(out)),'output_sha256':sha(log),'executes_tests':False})
 lists[name]=tests
 return set(tests)
probe='experimental_swift_reactor::execution::frozen_construction_metadata'
for profile in ['debug','release']:
 old=next(row for row in observations['observations']if row['profile']==profile)
 contaminated=direct_list('contaminated-candidate4-'+profile,root/old['shared_executable'],root,old['executable_sha256']);assert len(contaminated)==152 and probe in contaminated
 witness=qualification['unitBinaries'][profile]
 product=direct_list('root-clean-product-'+profile,Path(witness['path']),source,witness['sha256']);assert len(product)==151 and probe not in product
 own_command=next(row for row in json.loads((base/'candidate3-final/commands.json').read_text())if row['name']=='all-features-'+profile)
 output=(base/'candidate3-final'/own_command['output']).read_text();assert sha(base/'candidate3-final'/own_command['output'])==own_command['output_sha256']
 binary=Path(re.search(r'Running unittests src/lib.rs \(([^\n)]+)\)',output).group(1))
 own=direct_list('independent-derived-'+profile,binary,Path(own_command['cwd']));assert len(own)==159 and probe not in own
 extras=own-product;assert len(extras)==8 and not(product-own)
 assert sum('independent_construction_review_'in name for name in extras)==7
 assert sum(name.endswith('::independent_positive_accounting_probe')for name in extras)==1
 assert binary.resolve().is_relative_to((base/'candidate3-final/target').resolve())
 assert not target.resolve().is_relative_to((producer/'build/target').resolve())
result={'schema':'mixer-swift-construction-independent-artifact-supplement-v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_SUPERSEDING_SCOPED_RECOMMENDATION_TO_ROOT','supersedes':['Only original review/decision/receipt/producer-evidence-audit statements treating contaminated producer candidate4 full runs (367 passed) as product qualification. Original434derived library/probe executions, 8typed layout configurations, source/accounting review and scope limits remain valid.'],'original_seal_sha256':sha(base/'seal.json'),'original_sealed_entries_verified_unchanged':len(original['files']),'original_producer_receipt_sha256':sha(producer/'receipt.json'),'original_producer_full_runs':'INVALID_PRODUCT_EVIDENCE_SHARED_TARGET_METADATA_EXECUTABLE','not_salvaged_by_test_count_subtraction':True,'independent_contaminated_binary_lists_confirmed':True,'independent_derived_lists':{'test_count':159,'exact_additions_to_product':8,'independent_behavior_tests':7,'intentional_layout_probe':1,'unexpected_metadata_probe':False},'root_product_regression_receipt':str((clean/'qualification.json').relative_to(root)),'root_product_regression_receipt_sha256':sha(clean/'qualification.json'),'root_product_collector_sha256':sha(collector),'source_revision':qualification['sourceRevision'],'tool_versions':{'rustc':(clean/'rustc-version.log').read_text().strip(),'cargo':(clean/'cargo-version.log').read_text().strip()},'source_tree_digest_sha256':qualification['sourceTreeSHA256'],'source_archive_sha256':qualification['archiveSHA256'],'source_file_count':425,'all_actual_source_and_archive_entries_verified':True,'root_product_scope':'Full all-features host library/binary/integration/doc suites on fresh product-only target; library151/full366passed9ignored perprofile','root_product_counts':qualification['counts'],'root_binary_hashes':qualification['unitBinaries'],'future_collector':'Unexecuted candidate5 is future evidence hygiene only, not replacement product qualification. Independent source review confirms disjoint fresh targets, matching manifest/target/env and unit binary hash/runtime-list binding. Six synthetic tool-fixture command logs and positive/negative assertions verified.','future_correction_receipt_sha256':sha(correction/'resolution.json'),'other_source_metadata_findings':'No additional observed source/META switch contaminates the earlier product library matrix/Clippy (which precede metadata), or the independently derived single-source-tree runner. No deeper Cargo cache-cause claim or runtime semantic failure inferred.','commands':record,'root_acceptance':False,'pending':['Root final acceptance','Nine ignored full host tests perprofile','Full Swift target initialize/invoke and public activation','Interpreter operation/growth/active-frame unwind qualification','Physical devices (phones remain disconnected), immutable published FieldLog consumption, signing/store/customer/operational and all GA evidence']}
(out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'original_entries_unchanged':len(original['files']),'read_only_binary_lists':len(record),'correct_product_tests_per_profile':366,'ignored_per_profile':9,'root_receipt_sha256':sha(clean/'qualification.json')}))
