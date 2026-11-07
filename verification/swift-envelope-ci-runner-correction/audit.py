"""Producer custody/reconciliation audit; independent root review remains required."""
from datetime import datetime, timezone
import ast
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

PACKET=Path(__file__).resolve().parent
ROOT=PACKET.parents[1]
def require(ok, message):
    if not ok: raise RuntimeError(message)
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):h.update(block)
    return h.hexdigest()
def inventory(base):
    rows=[]
    for path in sorted(base.rglob('*')):
        require(not path.is_symlink() and (path.is_file() or path.is_dir()),'Nonregular evidence member')
        if path.is_file():rows.append({'path':path.relative_to(base).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)})
    return rows
freeze=json.loads((PACKET/'freeze.json').read_bytes())
require(inventory(PACKET/'source-freeze')==freeze['members'],'Frozen files differ')
for row in freeze['members']:
    require(sha(ROOT/row['path'])==row['sha256'],'Live source differs from pre-run freeze')
runner=ROOT/'scripts/ci/check-analyzer-envelope.py'
spec=importlib.util.spec_from_file_location('correction_runner_audit',runner)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
r.verify_pack(ROOT/r.PACK)
r.verify_pack(PACKET/'source-freeze'/r.PACK)
host=PACKET/'host-run-1'
r.verify_pack(host/'pack')
state=json.loads((PACKET/'full-run-state.json').read_bytes())
require(state['all_retained_bytes_and_paths_verified'] and inventory(host)==state['members'],'Retained path/byte mapping differs')
require(state['temporary_parent_removed'] and not Path(state['temporary_parent']).exists(),'Owned temporary parent remains')
receipt=json.loads((host/'receipt.json').read_bytes())
require(receipt['status']=='passed-host-fixture-check' and not receipt['errors'] and receipt['active_checks_completed'],'Host runner did not complete')
require(receipt['runner']['sha256']==sha(runner)==sha(host/'executed-runner.py'),'Executed runner identity differs')
require(receipt['rustc']['identity']['host']=='aarch64-apple-darwin' and receipt['rustc']['identity']['release']=='1.99.0','Actual host tuple differs')
require(r.rustc_identity(receipt['rustc']['version_verbose'])==receipt['rustc']['identity'],'Compiler identity reconciliation differs')
require(sha(Path(receipt['rustc']['path']))==receipt['rustc']['sha256'],'Compiler executable changed')
require(len(receipt['postflight'])==8 and all(x['passed'] for x in receipt['postflight'].values()),'Postflight incomplete')
require(len(receipt['commands'])==23,'Command count differs')
for command in receipt['commands']:
    require(command['child_returned'] and command['owned_group_gone'] and not command['timed_out'] and not command.get('descendants_outlived_direct_child'),'Unreturned/abnormal owned command')
    require(command['exit']==(1 if command['name'].startswith('api-negative-') else 0),'Unexpected command exit')
    for stream in ('stdout','stderr'):
        record=command[stream];path=host/record['path']
        require(path.stat().st_size==record['bytes'] and sha(path)==record['sha256'],'Raw command stream differs')
methods=json.loads((host/'pack/inventories/expected-methods.json').read_bytes())
for lane,key,count in (('producer','producer',78),('independent','independent_exact_source',14)):
    names=methods[key]['names'];require(len(names)==count,'Expected method count differs')
    require(receipt['test_binaries'][lane]['listed']==sorted(names)==receipt['test_binaries'][lane]['executed'],'Exact method inventory differs')
require(receipt['fresh_candidate_comparisons_against_reused_oracles']==21714 and len(receipt['host_layouts'])==32,'Comparison/layout count differs')
require(receipt['api']['positive'] and len(receipt['api']['negative'])==8,'API inventory differs')
targets=json.loads((ROOT/'verification/swift-envelope-ci-root-review/api-span-correction-targets.json').read_bytes())
for probe in targets['probes']:
    name=probe['name'];fixed=r.API_SOURCE_TARGETS[name]
    require((fixed[0],fixed[1])==(probe['source_bytes'],probe['source_sha256']),'Fixed source binding differs')
    require(list(fixed[2])==[(s['byte_start'],s['byte_end'],s['source_text_utf8']) for s in probe['selected_primary_spans']],'Fixed target map differs')
    matches=receipt['api']['negative'][name]
    require({(m['primary_span']['byte_start'],m['primary_span']['byte_end']) for m in matches}=={(s['byte_start'],s['byte_end']) for s in probe['selected_primary_spans']},'Actual primary span set differs')
    require(all(m['code']==probe['required_code'] for m in matches),'API code differs')
retention=json.loads((host/'retention.json').read_bytes())
require(retention['test_files']==receipt['cleanup']['test_files'] and retention['compiler_products']==receipt['cleanup']['compiler_products'],'Retention manifests disagree')
require(len(retention['test_files'])==92 and len(retention['compiler_products'])==4,'Retention count differs')
for name,record in retention['test_files'].items():
    path=host/record['path']
    require(path.stat().st_size==record['bytes'] and sha(path)==record['sha256'],'Retained representation differs')
    opener=gzip.open if record['encoding']=='gzip' else open
    digest=hashlib.sha256();size=0
    with opener(path,'rb') as f:
        for block in iter(lambda:f.read(65536),b''):digest.update(block);size+=len(block)
    require(size==record['original_bytes'] and digest.hexdigest()==record['original_sha256'],'Original retained bytes differ')
require({x['path'] for x in inventory(host/'retained')}=={str(Path(v['path']).relative_to('retained')) for v in retention['test_files'].values()},'Unreconciled retained member')
require(receipt['cleanup']['removed'] and receipt['cleanup']['children_and_owned_groups_returned'],'Scratch cleanup incomplete')
for name in ('final-controls-normal','final-controls-optimized'):
    command=json.loads((PACKET/name/'command.json').read_bytes())
    require(command['exit']==0 and re.search(r'Ran 32 tests.*\n\nOK\n$',(PACKET/name/'stderr').read_text(),re.S),'Final controls incomplete')
    require(command['source_files']['scripts/ci/check-analyzer-envelope.py']['sha256']==sha(runner),'Controlled runner differs')
    require(command['source_files']['scripts/ci/tests/test_analyzer_envelope_runner.py']['sha256']==sha(ROOT/'scripts/ci/tests/test_analyzer_envelope_runner.py'),'Controlled tests differ')
def test_names(path):return {node.name for node in ast.walk(ast.parse(path.read_bytes())) if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')}
old=test_names(ROOT/'verification/swift-envelope-ci-implementation/final-tests.py.txt')
current=test_names(ROOT/'scripts/ci/tests/test_analyzer_envelope_runner.py')
require(len(old)==25 and len(current)==32 and old.issubset(current),'Prior control methods were removed')
flags=('storedPrefixValidated','fullReplayAccepted','semanticMetricsValid','GA_qualified','model_imported_or_evaluated')
require(all(receipt[key] is False for key in flags),'Qualification boundary changed')
result={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'command':'python3 -B verification/swift-envelope-ci-runner-correction/audit.py',
    'python':{'path':sys.executable,'resolved_path':str(Path(sys.executable).resolve()),'sha256':sha(Path(sys.executable).resolve()),'version':sys.version},
    'git_version':subprocess.check_output(['git','--version'],text=True).strip(),'platform':platform.platform(),
    'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'source_git_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
    'status':'passed-producer-custody-audit-independent-review-pending','freeze_sha256':sha(PACKET/'freeze.json'),
    'host_receipt_sha256':sha(host/'receipt.json'),'retained_mapping_sha256':sha(PACKET/'full-run-state.json'),
    'host_members':len(state['members']),'host_bytes':sum(x['bytes'] for x in state['members']),
    'control_methods':32,'prior_methods_preserved':25,'normal_and_optimized_control_exits':[0,0],
    'producer_methods':78,'independent_methods':14,'positive_api':1,'negative_api':8,'primary_targets':23,
    'fresh_comparisons_against_reused_oracles':21714,'host_layouts':32,'commands':23,'postflight_scopes':8,
    'retained_test_files':92,'retained_original_bytes':sum(x['original_bytes'] for x in retention['test_files'].values()),
    'retained_independent_actual_file_files':sum(name.startswith('independent-files/') for name in retention['test_files']),
    'retained_compiler_product_identities':4,'temporary_parent_removed':True,'scratch_removed':True,
    'old_producer_archive_written':False,'old_independent_review_archive_written':False,
    'toolchain_installed_or_network_used':False,'native_runtime_or_capture_started':False,
    'rust_1_98_1_qualified':False,'GA_qualified':False}
(PACKET/'audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True))
