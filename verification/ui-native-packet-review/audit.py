#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=ROOT/'verification/ui-native-packet-v1/candidate-3'
sha=lambda b:hashlib.sha256(b).hexdigest()
r=json.loads((P/'receipt.json').read_text());lock=json.loads((P/'input-lock.json').read_text())
assert r['status']=='passed' and len(r['commands'])==17 and len(lock['files'])==48
assert sha(json.dumps(lock['files'],sort_keys=True,separators=(',',':')).encode())==lock['tree_sha256']==r['source_tree_sha256']=='c59e8d12612e2d2bb6138b40756ceefd8ed2a562861546305ee5005199ce720e'
for name,digest in lock['files'].items():
 assert sha((ROOT/name).read_bytes())==digest,name
 assert sha((P/'.build/source'/name).read_bytes())==digest,name
for c in r['commands']:
 assert c['exit_code']==0 and sha((ROOT/c['log']).read_bytes())==c['log_sha256'],c['name']
for name,row in r['artifacts'].items():
 data=(ROOT/name).read_bytes();assert sha(data)==row['sha256'] and len(data)==row['bytes'],name
for mode in ['debug','release']:
 log=(P/f'sdk-{mode}.log').read_text();assert sum(map(int,re.findall(r'Test run with (\d+) tests.*passed',log)))==51,mode
 own=(HERE/'candidate3'/f'tests-{mode}.log').read_text();assert re.search(r'Test run with 2 tests.*passed',own)
 assert 'ui_review_pending_max=3997' in own
 old=(HERE/'candidate2'/f'tests-{mode}.log').read_text();assert re.search(r'Test run with 2 tests.*passed',old)
 assert old.count('ui_review_pending_max=8992')==2
for variant in ['candidate2','candidate3']:
 own=json.loads((HERE/variant/'receipt.json').read_text());assert len(own['commands'])==3 and all(c['exit_code']==0 for c in own['commands'])
 assert own['probe_sha256']==sha((HERE/variant/'ReviewPacketTests.swift').read_bytes())
 for c in own['commands']:assert sha((HERE/variant/c['output']).read_bytes())==c['output_sha256']
 assert all(sha((HERE/variant/'.build/source'/name).read_bytes())==digest for name,digest in own['input_manifest'].items() if name!='sdk/Sources/MixerUI/Validation.swift')
 assert sha((HERE/variant/'.build/source/sdk/Sources/MixerUI/Validation.swift').read_bytes())==own['validator_derived_sha256']
result={'scope':'independent data-only SDK review and hash/output audit; producer module/interoperation executions remain attributed','producer_receipt_sha256':sha((P/'receipt.json').read_bytes()),'input_lock_sha256':sha((P/'input-lock.json').read_bytes()),'scope_clarification_sha256':sha((ROOT/'verification/ui-native-packet-v1/scope.md').read_bytes()),'source_digest':lock['tree_sha256'],'sources_verified_current_and_archive':96,'producer_commands_audited':17,'producer_artifacts_verified':len(r['artifacts']),'sdk_tests_per_mode':51,'independent_tests_per_mode_per_candidate':2,'old_standard_comb_pending_peak':8992,'repaired_standard_comb_pending_peak':3997,'custom_input_nodes':9001,'encoder_source_sha256':lock['files']['sdk/Sources/MixerUI/NativePacketV1.swift'],'validator_source_sha256':lock['files']['sdk/Sources/MixerUI/Validation.swift'],'tests_source_sha256':lock['files']['sdk/Tests/MixerUITests/NativePacketV1Tests.swift'],'result':'pass_repaired_data_encoder_and_validation_frontier_scope_only'}
(HERE/'audit-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
