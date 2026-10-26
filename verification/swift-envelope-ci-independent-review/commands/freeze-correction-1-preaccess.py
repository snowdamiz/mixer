#!/usr/bin/env python3
"""Freeze only correction preaccess controls; do not read corrected candidate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

REPO=Path(__file__).resolve().parents[3]
PREFIX='verification/swift-envelope-ci-independent-review/correction-1-preaccess-supplement'
OWNED='verification/swift-envelope-ci-independent-review/'
EXPECTED={
    'verification/swift-envelope-ci-root-review/runner-correction-1-selection.json':'376589fa85f8da663e1f2ae4232ee28471e86cf9603a55ef0bb912381fb9bd7c',
    'verification/swift-envelope-ci-root-review/api-span-correction-targets.json':'24c4d9f7bea9e863a4af917c9ea422005448b39521d14672b3e56349c32a9852',
    OWNED+'review-round-1/seal.json':'4f4d0da6ff694282ba72ba8dea8cd64ef243fc47703e480dd35eeb7af24e6fbc',
    OWNED+'preaccess-seal.json':'07af3bdb40573f9c566987a5c261c6403e9cb61153f4066f1ab35c44e1c1cc3e',
    OWNED+'test-lint-preaccess-supplement/seal.json':'04d74cdd7295bf092a072ac64aac83c93f178e37f24f53c9c4a079b60b07a27b',
    OWNED+'compiler-preaccess-supplement/seal.json':'f6baf7ff5470c07e28582d93a3d149b71638079a75844d9dfff273a313d2dc7f',
}


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(65536),b''):h.update(block)
    return h.hexdigest()


def info(relative):
    path=REPO/relative
    return {'path':relative,'bytes':path.stat().st_size,'sha256':sha(path)}


def write(relative,value):
    with (REPO/relative).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')


def git(*args):return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()


bindings=[]
for relative,digest in EXPECTED.items():
    actual=info(relative)
    if actual['sha256']!=digest:raise RuntimeError('binding changed: '+relative)
    bindings.append(actual)
span_map=json.loads((REPO/'verification/swift-envelope-ci-root-review/api-span-correction-targets.json').read_bytes())
round_seal=json.loads((REPO/OWNED/'review-round-1/seal.json').read_bytes())
audit_path=OWNED+'review-round-1/raw-evidence-audit.json'
audit_record=next(m for m in round_seal['members'] if m['path']==audit_path)
if info(audit_path)!=audit_record:raise RuntimeError('round1 raw audit differs')
observed=json.loads((REPO/audit_path).read_bytes())['clean_actual_primary_API_spans']
span_count=0
for probe in span_map['probes']:
    selected={(s['byte_start'],s['byte_end'],s['source_text_utf8']) for s in probe['selected_primary_spans']}
    real={(s['byte_start'],s['byte_end'],s['source_text']) for s in observed[probe['name']]}
    if selected!=real or not all(s['code']==probe['required_code'] and s['file']==probe['source_path'] for s in observed[probe['name']]):
        raise RuntimeError('selected target differs from independent prior real spans')
    span_count+=len(selected)
if len(span_map['probes'])!=8 or span_count!=23:raise RuntimeError('selected span inventory differs')
plan=json.loads((REPO/PREFIX/'plan.json').read_bytes())
if [x['id'] for x in plan['correction_review_obligations']]!=[f'Q{n:02d}' for n in range(1,9)]:raise RuntimeError('correction obligation inventory differs')
at=datetime.now(timezone.utc).isoformat()
audit={'schema':1,'at':at,'status':'correction-preaccess-preparation-only','command':'python3 -B verification/swift-envelope-ci-independent-review/commands/freeze-correction-1-preaccess.py','python_executable':sys.executable,'python_version':sys.version,'git_version':git('--version'),'revision':git('rev-parse','HEAD'),'committed_tree':git('rev-parse','HEAD^{tree}'),'os':platform.platform(),'machine':platform.machine(),'bindings_verified':bindings,'prior_independent_raw_audit_verified':audit_record,'selected_spans_match_preserved_independent_real_diagnostics':{'probes':8,'primary_spans':23},'original_plan_inventory':52,'correction_review_obligations_planned':8,'corrected_candidate_accessed':False,'corrected_candidate_executed':False,'old_candidate_reexecuted':False,'scope':'Selection/map and preserved reviewer records only; no compiler, candidate, model, collector or native/capture execution.','errors':[]}
write(PREFIX+'/input-audit.json',audit)
log='Verified correction selection, fixed eight-probe/23-span map against preserved independent real diagnostics, and prior freeze bindings; eight correction obligations planned; no corrected candidate access or execution.\n'
with (REPO/PREFIX/'freeze.stdout').open('x') as stream:stream.write(log)
members=[info(relative) for relative in (PREFIX+'/plan.json',PREFIX+'/README.md',OWNED+'commands/freeze-correction-1-preaccess.py',PREFIX+'/input-audit.json',PREFIX+'/freeze.stdout')]
seal={'schema':1,'at':at,'status':'frozen-correction-1-preaccess-plan-awaiting-root-candidate-admission','member_count':len(members),'total_bytes':sum(m['bytes'] for m in members),'members':members,'correction_selection_sha256':EXPECTED['verification/swift-envelope-ci-root-review/runner-correction-1-selection.json'],'span_map_sha256':EXPECTED['verification/swift-envelope-ci-root-review/api-span-correction-targets.json'],'original_frozen_plan_inventory':52,'correction_review_obligations':8,'corrected_candidate_accessed':False,'corrected_candidate_executed':False,'old_candidate_reexecuted':False,'storedPrefixValidated':False,'fullReplayAccepted':False,'semanticMetricsValid':False,'CI_1_98_1_envelope_qualified':False,'GA_qualified':False,'excluded':[PREFIX+'/seal.json',PREFIX+'/seal.sha256']}
write(PREFIX+'/seal.json',seal)
digest=info(PREFIX+'/seal.json')['sha256']
with (REPO/PREFIX/'seal.sha256').open('x') as stream:stream.write(digest+'  '+PREFIX+'/seal.json\n')
print(log,end='')
print(json.dumps({'seal_sha256':digest,'member_count':len(members),'member_bytes':seal['total_bytes'],'original_plan_inventory':52,'correction_obligations_planned':8},sort_keys=True))
