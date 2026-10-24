#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,tarfile
base=Path(__file__).resolve().parent;root=base.parents[1];producer=root/'verification/swift-executor-construction/candidate-4'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
d=json.loads((producer/'receipt.json').read_text())
assert sha(producer/'receipt.json')=='bcf3d924edb227078ada37c8843824e4eb36ad1c3e739dbfb674378ec25d8a80'
for name,digest in d['artifact_hashes'].items():assert sha(producer/name)==digest,name
for command in d['commands']:
 assert command['cwd_asserted'] and command['source_unchanged'] and command['cwd_unchanged'],command['name']
 assert command['source_tree_digest']==d['source_tree_digest']
 assert Path(command['cwd']).resolve().is_relative_to((producer/'build').resolve())
 assert sha(root/command['log'])==command['sha256'],command['name']
 if command['expected']==0:assert command['exit_code']==0,command['name']
 else:
  assert command['exit_code']!=0 and 'private-constructor' in command['name']
  text=(root/command['log']).read_text();assert 'error[E0603]' in text and 'error[E0624]' in text
 if command['argv'][0]=='cargo' and command['argv'][1] in ['test','check','clippy','run']:
  pos=command['argv'].index('--manifest-path');assert Path(command['argv'][pos+1]).parent==Path(command['cwd'])
manifest=json.loads((producer/'source-manifest.json').read_text());shared=0
for row in json.loads((base/'candidate4-final/input-manifest.json').read_text())['files']:
 if row['path'].startswith('vm/'):
  name=row['path'][3:];assert manifest[name]==row['sha256'],name;shared+=1
with tarfile.open(producer/'frozen-source.tar.gz')as archive:
 rows=[member for member in archive.getmembers() if member.isfile()];assert len(rows)==len(manifest)==425
 for member in rows:
  name=member.name.removeprefix('vm/');assert hashlib.sha256(archive.extractfile(member).read()).hexdigest()==manifest[name],member.name
full=[]
for command in d['commands']:
 if not command['name'].startswith('all-features-full-'):continue
 text=(root/command['log']).read_text();counts=[tuple(map(int,match))for match in re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',text)]
 assert sum(row[0]for row in counts)==367 and sum(row[1]for row in counts)==0 and sum(row[2]for row in counts)==9
 full.append({'command':command['name'],'passed':367,'failed':0,'ignored':9,'suite_counts':counts})
assert len(full)==2
result={'schema':'mixer-swift-construction-independent-producer-evidence-audit-v1','status':'PASS','receipt':str((producer/'receipt.json').relative_to(root)),'receipt_sha256':sha(producer/'receipt.json'),'archive_sha256':sha(producer/'frozen-source.tar.gz'),'producer_tree_digest':d['source_tree_digest'],'command_count':len(d['commands']),'every_command_absolute_cwd_and_manifest_bound':True,'every_command_log_hash_verified':True,'all_artifact_hashes_verified':True,'archive_actual_contents_match425file_manifest':True,'shared_vm_inputs_matching_independent_final_freeze':shared,'full_host_test_results':full,'ignored_is_not_pass':True,'own_independent_test_scope':'434 total library/probe function executions, not producer integration/bin/doc evidence','candidate2_behavior_evidence':'rejected for stale cwd','candidate3_producer_status':'real Clippy failure preserved, corrected with annotation-only final source'}
(base/'candidate4-final/producer-evidence-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'PASS','commands':len(d['commands']),'shared_vm_inputs':shared,'full_host_per_profile':{'passed':367,'failed':0,'ignored':9}}))
