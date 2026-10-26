#!/usr/bin/env python3
"""One-shot exact-source selection; no compiler, native runtime or Git mutation."""
from pathlib import Path
import datetime, hashlib, json, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
def need(ok, message):
    if not ok: raise RuntimeError(message)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def packet(relative, expected):
    p = ROOT / relative
    need(sha(p) == expected, 'Seal changed: ' + relative)
    value = json.loads(p.read_text()); rows = value.get('members', value.get('files'))
    if isinstance(rows, dict): rows = [dict(path=k, **v) for k, v in rows.items()]
    names = set(); total = 0
    for row in rows:
        name = Path(row['path'])
        need(not name.is_absolute() and '..' not in name.parts and str(name) not in names, 'Invalid member')
        names.add(str(name)); f = p.parent / name
        need(f.is_file() and not f.is_symlink(), 'Nonregular member')
        need(f.stat().st_size == row['bytes'] and sha(f) == row['sha256'], 'Changed member: ' + str(f))
        total += row['bytes']
    return {'seal': relative, 'sha256': expected, 'members_verified': len(rows), 'bytes_verified': total}

need(not (HERE/'selection.json').exists(), 'Selection already completed')
need(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() == '8ac624160a2cfff10d201d8063f69cf05f005edb', 'Unexpected HEAD')
inputs = [
 packet('verification/swift-cache-state-ci-root-correction-2/source-seal.json','bccbdaefca93a190fc74faa7340a3e32848d3d3a35fc05f078a2e3825543600e'),
 packet('verification/swift-cache-state-ci-independent/corrected-review/seal.json','97b46528fe65c4d9d4fe6c95196f4673c18a6e94b556d45416de916435d6d976'),
 packet('verification/swift-cache-state-ci-workflow-review/seal.json','1ce89299f64c98a69a818cf2e9ea0d1ecfddda9b034fb492c72eaf43720808c5'),
]
decision_path = ROOT/'verification/swift-cache-state-ci-independent/corrected-review/final-decision.json'
need(sha(decision_path) == 'd6c0527d400ff3f289316cd03ef0203c1c09ca1ddbaeaaf5d0d3a73bf507e3d2', 'Decision changed')
decision = json.loads(decision_path.read_text())
need(decision['corrected_host_component_accepted'] and decision['commands'] == 103 and decision['all103commands_owned_TMP'] and decision['normal_and_control_scratch_removed'], 'Independent acceptance absent')
need(json.loads((HERE/'root-tests.json').read_text())['exit'] == 0, 'Workflow controls failed')
workflow = ROOT/'.github/workflows/verify.yml'
proposal = ROOT/'verification/swift-cache-state-ci-workflow-review'
need(workflow.read_bytes() == (proposal/'baseline.verify.yml').read_bytes(), 'Workflow changed')
source = ROOT/'verification/swift-cache-state-ci-root-correction-2'
dest = ROOT/'verification/swift-cache-state-ci'
need(not dest.exists(), 'Canonical directory already exists')
dest.mkdir()
for name in ('check_cache_state.py','test_runner.py'): shutil.copyfile(source/name,dest/name)
shutil.copytree(source/'pack',dest/'pack')
shutil.copyfile(proposal/'proposed.gitignore',dest/'.gitignore')
workflow.write_bytes((proposal/'proposed.verify.yml').read_bytes())
rows = [{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(dest.rglob('*')) if p.is_file()]
receipt = {'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,'inputs':inputs,'canonical_source_members':rows,'canonical_runner_sha256':sha(dest/'check_cache_state.py'),'pack_manifest_sha256':sha(dest/'pack/manifest.json'),'workflow_sha256':sha(workflow),'runner_source_bytes_unchanged':True,'closed_fixture_CI_integration_selected':True,'root_workflow_controls':21,'focused_runner_controls':29,'independent_full_commands':103,'independent_full_seconds':decision['elapsed_seconds'],'scope':'Exact closed host fixture and dedicated CI job; no canonical VM/runtime change','Rust1_98_1_or_actual_Actions_qualified':False,'native_or_public_V2_or_GA_qualified':False,'historical_proposal_28_controls_superseded_by_actual_29':True}
(HERE/'selection.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'canonical_members':len(rows),'runner_sha256':receipt['canonical_runner_sha256'],'workflow_sha256':receipt['workflow_sha256'],'input_members_verified':sum(x['members_verified'] for x in inputs)}))
