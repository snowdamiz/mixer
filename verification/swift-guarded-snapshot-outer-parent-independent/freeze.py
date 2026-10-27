#!/usr/bin/env python3
"""Freeze this owned review packet once; reads retained data only."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P=ROOT/'verification/swift-guarded-snapshot-outer-parent-source'
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda obj:json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
assert not (HERE/'seal.json').exists(), 'Frozen packet cannot be replaced'
assert not (HERE/'owned-work').exists()
assert sha((P/'seal.json').read_bytes())=='3936c73a0f3558000834c92c3ade9822465069492740a954765cb775684bcb57'
for member in json.loads((P/'seal.json').read_bytes())['members']:
    data=(P/member['path']).read_bytes()
    assert dict(path=member['path'],bytes=len(data),sha256=sha(data))==member
compiler=json.loads((HERE/'commands/compiler-metadata-mir/receipt.json').read_bytes())
assert compiler['exit_code']==0 and compiler['compile_success'] and not compiler['timed_out']
assert all(compiler[k] for k in ['child_reaped','owned_group_absent','owned_scratch_removed','postprocess_success'])
assert compiler['compiler_invocations']==1 and compiler['retries']==0
assert compiler['runner_sha256']==sha((HERE/'compile_independent_once.py').read_bytes())
for name in ['offline-review-attempt2','offline-review-attempt3','offline-review-attempt4']:
    out=HERE/'commands'/name
    receipt=json.loads((out/'receipt.json').read_bytes())
    assert receipt['runner_sha256']==sha((out/'reviewer.py').read_bytes())
    assert receipt['child_reaped'] and receipt['owned_group_absent']
    assert receipt['stdout_sha256']==sha((out/'stdout').read_bytes())
    assert receipt['stderr_sha256']==sha((out/'stderr').read_bytes())
assert json.loads((HERE/'results.json').read_bytes())['assertions']==917
assert json.loads((HERE/'commands/adversarial-route-controls/stdout').read_bytes())['assertions']==47
members=[]
for path in sorted(HERE.rglob('*')):
    if path.is_file():
        data=path.read_bytes()
        members.append(dict(path=str(path.relative_to(HERE)),bytes=len(data),sha256=sha(data)))
seal=dict(schema=1,status='frozen-independent-source-and-production-compiler-review-pending-root-selection',member_count=len(members),member_bytes=sum(row['bytes'] for row in members),manifest_sha256=sha(canonical(members)),members=members,candidate_seal_sha256=sha((P/'seal.json').read_bytes()),candidate_source_tree_sha256='27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3',query_source_tree_sha256=compiler['query_tree_sha256'],compiler_invocations=1,independent_compile_success=True,producer_terminal_status_still_unknown=True,main_assertions=917,additional_adversarial_assertions=47,total_assertions=964,preserved_reviewer_failures=3,source_findings=0,root_selection=False,new_outer_costs_or_storage_priced=False,all_three_selectors_pending=True,actual_binding_or_fixture_runtime=False,native_capture_UI_runtime=False,whole_host_grant_or_GA=False)
(HERE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),members=seal['member_count'],bytes=seal['member_bytes'],manifest_sha256=seal['manifest_sha256'],assertions=964)))
