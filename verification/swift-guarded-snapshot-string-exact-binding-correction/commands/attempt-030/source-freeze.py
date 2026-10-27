#!/usr/bin/env python3
"""Freeze only this new candidate after recorded host checks and custody."""
import hashlib,json,sys
from pathlib import Path
D=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(ok,why):
    if not ok:raise ValueError(why)
require(not (D/'seal.json').exists(),'already frozen')
candidate=json.loads((D/'candidate.json').read_text())
require(candidate['counts']['selected_overapprox_bodies']==525 and candidate['counts']['authored_and_callback_edges']==1908,'corrected graph')
custody=json.loads((D/'custody.json').read_text());require(custody['all_pins_match'],'custody required')
require(json.loads((D/'cleanup.json').read_text())['owned_children_waited'],'cleanup required')
scripts=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(D.glob('*.py'))]
required={('test_provenance.py',()),('test_correction.py',()),('prepare_contracts.py',('--check',)),
          ('derive.py',('--check',)),('check.py',()),('custody.py',('--check',)),
          ('prepare_authored.py',('--check',)),('report.py',('--check',)),('audit.py',('--check',)),('test_adverse.py',()),
          *{('test_exact_binding.py',(g,)) for g in ('syntax','identity','receiver','types','callbacks')}}
qualified={}
for path in sorted((D/'commands').glob('attempt-*/receipt.json')):
    receipt=json.loads(path.read_text());argv=receipt['argv'];key=(Path(argv[2]).name,tuple(argv[3:]))
    if key in required and receipt['exit_code']==0 and receipt['script_members']==scripts:
        qualified[key]=str(path.relative_to(D))
require(set(qualified)==required,'all final read-only controls must pass against current scripts')
members=[]
for path in sorted(D.rglob('*')):
    require(not path.is_symlink(),'symlink member')
    if path.is_file():
        raw=path.read_bytes();members.append({'path':str(path.relative_to(D)),'bytes':len(raw),'sha256':sha(raw)})
seal={'schema':2,'status':'frozen-source146-exact-binding-string-correction-candidate-ready-for-root-release-and-fresh-independent-review',
    'source_tree_sha256':candidate['source_tree_sha256'],'host_tree_sha256':candidate['host_tree_sha256'],
    'original_candidate_seal_sha256':'b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f',
    'original_independent_review_seal_sha256':'741e104537fc3ddc57fc499a764cca9fedaa2b42d2fe109eeb590504b01241d9',
    'correction_contract_sha256':candidate['correction_contract_sha256'],
    'first_correction_seal_sha256':'4d2dcab90e7c9cfd7074a67fe8eac0d6807b6ed3704b74afe430ebc624b07994',
    'second_independent_review_seal_sha256':'7c101623fa53d9207c467f196cca729085fff23a195f873a46da7a1369135f65',
    'authored_contracts_sha256':candidate['authored_contracts_sha256'],
    'member_count':len(members),'bytes':sum(x['bytes'] for x in members),'members':members,
    'source_provenance_status':'conditional correction candidate; exact caller contract required; independent review pending',
    'L_str_candidate':5080,'L_str_selected':False,'root_selection_required':True,'fresh_independent_review_required':True,
    'actual_P0_caller_selected':False,'selected_whole_host_bound':False,'operational_grant':False,'runtime_or_OTA_or_GA':False,
    'future_outer_candidate_automatically_covered':False,
    'qualifying_receipts':{' '.join((name,*args)):path for (name,args),path in qualified.items()},
    'freeze_tool':{'argv':[sys.executable,'-B',str(Path(__file__).resolve())],
        'python_version':sys.version,'python_executable_sha256':sha(Path(sys.executable).read_bytes()),
        'scope':'pure host packet freeze only; no compiler/product/native/UI/capture/Git/global inventory'}}
raw=(json.dumps(seal,indent=2,sort_keys=True)+'\n').encode();(D/'seal.json').write_bytes(raw)
print(json.dumps({'members':len(members),'bytes':seal['bytes'],'seal_sha256':sha(raw),'L_str_candidate':5080,'L_str_selected':False,'fresh_independent_review_required':True,'operational_grant':False},sort_keys=True))
