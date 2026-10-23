#!/usr/bin/env python3
"""Independent probes against the implementation owner's explicitly frozen capture."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
owner = root/'verification/swift-reactor-validation/2026-10-23-final-v2/local/source'
if not owner.is_dir():
    raise SystemExit('explicit frozen owner capture is required')
private = Path(tempfile.mkdtemp(prefix='mixer-swift-validation-review-'))
reviewed = private/'reviewed'
baseline = private/'baseline'
reviewed.mkdir(); baseline.mkdir()
def manifest(directory):
    return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.rglob('*')) if p.is_file()}
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
owner_before = manifest(owner/'vm')
shutil.copytree(owner/'vm',reviewed/'vm')
if owner_before != manifest(owner/'vm') or owner_before != manifest(reviewed/'vm'):
    raise SystemExit('owner capture changed during review copy')
base_revision = subprocess.check_output(['git','rev-parse','e299f1a'],cwd=root,text=True).strip()
export = subprocess.check_output(['git','archive','--format=tar',base_revision,'vm'],cwd=root)
with tarfile.open(fileobj=io.BytesIO(export)) as archive:
    archive.extractall(baseline,filter='data')
probe_dir = private/'probes';probe_dir.mkdir()
for file in ['probe.rs','legacy_probe.rs']:
    shutil.copyfile(out/file,probe_dir/file)
shutil.copyfile(reviewed/'vm/tests/common/allocation_observer.rs',probe_dir/'allocation_observer.rs')
shutil.copytree(out/'authority',probe_dir/'authority')
for name,path in [('reviewed',reviewed),('baseline',baseline),('probes',probe_dir)]:
    with tarfile.open(out/(name+'-source.tar.gz'),'w:gz') as archive:
        for item in sorted(path.iterdir()): archive.add(item,arcname=item.name)
    for item in path.rglob('*'): item.chmod(0o555 if item.is_dir() else 0o444)
    path.chmod(0o555)
env = dict(os.environ)
env['PATH'] = '/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin:' + env['PATH']
env['RUSTUP_AUTO_INSTALL']='0'
env.pop('MIXER_ALLOCATOR_NOISE',None)
(out/'logs').mkdir(exist_ok=True)
records=[]
def run(name,cmd,cwd=root,expected=0):
    result=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,capture_output=True)
    stdout=out/'logs'/f'{name}.stdout';stderr=out/'logs'/f'{name}.stderr'
    stdout.write_bytes(result.stdout);stderr.write_bytes(result.stderr)
    records.append({'name':name,'command':list(map(str,cmd)),'cwd':str(cwd),'exit':result.returncode,'expected':expected,'stdout':str(stdout.relative_to(root)),'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),'stderr':str(stderr.relative_to(root)),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()})
    if expected==0 and result.returncode!=0:
        raise RuntimeError(f'{name} exited {result.returncode}: {result.stderr[-2000:].decode(errors="replace")}')
    if expected!=0 and result.returncode==0: raise RuntimeError(f'{name} unexpectedly compiled')
    return result
receipt={'observed_utc':datetime.now(timezone.utc).isoformat(),'owner_freeze':'Direct owner message: post-refactor engine/tests FROZEN; final/local/source capture selected for review.','owner_capture':str(owner),'baseline_revision':base_revision,'reviewed_source':owner_before,'reviewed_source_sha256':digest(owner_before),'baseline_source':manifest(baseline/'vm'),'probe_source':manifest(probe_dir),'commands':records,'scope':'Host validation and negative compile probes only. No Wasm execution, publication, devices or GA qualification.'}
try:
    receipt['tools']={tool:run('tool-'+tool,cmd).stdout.decode().strip() for tool,cmd in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V']),('git',['git','--version'])]}
    libraries={}
    configs=[('baseline-stream',baseline,'experimental-stream-validation','release'),('reviewed-stream',reviewed,'experimental-stream-validation','release'),('reviewed-swift',reviewed,'experimental-swift-reactor','release'),('reviewed-all',reviewed,'ALL','release'),('reviewed-swift-debug',reviewed,'experimental-swift-reactor','debug')]
    legacy={}
    for name,src,features,profile in configs:
        target=private/name
        cmd=['cargo','build','--locked','--manifest-path',src/'vm/Cargo.toml','--target-dir',target,'--lib']
        if profile=='release':cmd+=['--release']
        cmd+=['--all-features'] if features=='ALL' else ['--features',features]
        run(name+'-build',cmd)
        library=target/profile/'libmixer_vm.rlib';libraries[name]=library
        binary=private/(name+'-legacy')
        run(name+'-legacy-build',['rustc','--edition=2021','-O','--extern',f'mixer_vm={library}',probe_dir/'legacy_probe.rs','-o',binary])
        result=run(name+'-legacy',[binary])
        legacy[name]=[json.loads(line) for line in result.stdout.splitlines()]
        if name.startswith('reviewed-') and features!='experimental-stream-validation':
            binary=private/(name+'-probe')
            compile=['rustc','--edition=2021','--extern',f'mixer_vm={library}',probe_dir/'probe.rs','-o',binary]
            if profile=='release':compile+=['-O']
            run(name+'-probe-build',compile)
            result=run(name+'-probe',[binary])
            print(name+': '+result.stdout.decode().strip(),flush=True)
            abi=run(name+'-abi',[binary,'--abi'])
            actual=[json.loads(line) for line in abi.stdout.splitlines()]
            descriptors=json.loads((root/'compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json').read_text())
            types={'i32':127,'i64':126,'f32':125,'f64':124}
            expected=[{'name':entry['name'],'parameters':[types[x] for x in entry['signature']['parameters']],'results':[types[x] for x in entry['signature']['results']]} for entry in descriptors['imports']]
            assert actual==expected,'independent hardcoded fixture disagrees with retained ABI'
    golden=legacy['baseline-stream']
    for name,observed in legacy.items():assert observed==golden, f'legacy observations differ: {name}'
    boundaries=[]
    for entry in golden:
        if not entry['ok']:continue
        exact=[entry['metadata_peak'],entry['scratch_peak'],entry['work']]
        for mode in range(4):
            values=exact.copy()
            if mode>0:values[mode-1]-=1
            expected=None
            for name in [x[0] for x in configs]:
                binary=private/(name+'-legacy')
                result=run(f'{name}-{entry["case"]}-boundary-{mode}',[binary,entry['case'],*map(str,values)])
                observed=json.loads(result.stdout)
                if expected is None:expected=observed
                assert observed==expected,f'legacy exact budget admission differs: {name}/{entry["case"]}/{mode}'
            boundaries.append({'case':entry['case'],'mode':'exact' if mode==0 else ['metadata-minus-one','scratch-minus-one','work-minus-one'][mode-1],'budget':values,'result':expected})
    receipt['legacy_observations']=legacy
    receipt['legacy_boundaries']=boundaries
    authority={ 'fabricate':'private', 'clone':'clone', 'mutate':'cannot assign', 'legacy':'mismatched types', 'eager':'mismatched types', 'cache':'mismatched types', 'borrow':'borrow', 'policy':'private' }
    for name,marker in authority.items():
        result=run('authority-'+name,['rustc','--edition=2021','--extern',f'mixer_vm={libraries["reviewed-all"]}',probe_dir/'authority'/(name+'.rs'),'-o',private/('authority-'+name)],expected=1)
        assert marker in result.stderr.decode(),f'authority probe failed for an unrelated reason: {name}'
    receipt['owner_source_unchanged']=owner_before==manifest(owner/'vm')
    receipt['reviewed_source_unchanged']=owner_before==manifest(reviewed/'vm')
    assert receipt['owner_source_unchanged'] and receipt['reviewed_source_unchanged']
    receipt['passed']=True
finally:
    receipt.setdefault('passed',False)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('legacy equivalence and all original probes passed',flush=True)
