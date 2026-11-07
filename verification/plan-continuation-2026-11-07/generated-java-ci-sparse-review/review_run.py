#!/usr/bin/env python3
"""Independent selected-only closure, hash and normal/-O pure control replay."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent
CANDIDATE = BASE / 'generated-java-ci-integration'
FIX = BASE / 'generated-java-ci-sparse-fix'
ORIGINAL = BASE / 'generated-java-ci-integration-review'
EXPECTED = '53ad5501dcaa0168ec8196c8816d07a246e6b04bcd0160edadd22ecafd4ff815'
PATTERNS = ['/cli/', '/sdk/', '/updates/', '/native/android/', '/scripts/ci/', '/verification/plan-continuation-2026-11-07/generated-java-ci-integration/']
COMMANDS = []

def require(ok, message):
    if not ok: raise RuntimeError(message)

def save(name, value):
    (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def identity(path):
    data=path.read_bytes(); return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def run(label,argv,input=None,tests=None):
    result=subprocess.run(list(map(str,argv)),input=input,cwd=ROOT,capture_output=True,timeout=45)
    (HERE/(label+'.stdout')).write_bytes(result.stdout); (HERE/(label+'.stderr')).write_bytes(result.stderr)
    COMMANDS.append({'label':label,'argv':list(map(str,argv)),'cwd':str(ROOT),'timeout_seconds':45,'exit_code':result.returncode,'stdout':identity(HERE/(label+'.stdout')),'stderr':identity(HERE/(label+'.stderr')),'tests_expected':tests})
    save('commands.json',COMMANDS)
    require(result.returncode==0, 'Failed '+label)
    if tests: require(('Ran '+str(tests)+' tests') in result.stderr.decode() and result.stderr.decode().rstrip().endswith('OK'),'Unexpected tests '+label)
    return result.stdout

def check_pins():
    pins=json.loads((HERE/'initial-pins.json').read_text())
    require(identity(FIX/'receipt.json')==pins['fix_receipt'],'Producer receipt drift')
    for group,folder in [('candidate_artifacts',CANDIDATE),('evidence_artifacts',FIX),('sealed_review_artifacts',ORIGINAL)]:
        for path,want in pins[group].items(): require(identity(folder/path)==want,'Pinned artifact drift '+str(folder/path))
    return pins

def main():
    pins=check_pins()
    b=load('review_bootstrap_pinned',CANDIDATE/'bootstrap.py'); a=b.canonical()
    inputs=b.admit_source_inputs(a,a.load_profile())
    require(len(inputs)==101 and a.source_digest(inputs)==EXPECTED,'Source input digest drift')
    require(inputs==json.loads((FIX/'canonical-owning-inputs.json').read_text()),'Producer input inventory mismatch')
    records=run('selected-tree',['git','ls-tree','-rl','-z','HEAD','--',*[p.strip('/') for p in PATTERNS]])
    tracked={}
    for entry in records.rstrip(b'\0').split(b'\0'):
        meta,path=entry.split(b'\t',1); mode,kind,oid,size=meta.split()
        require(mode in (b'100644',b'100755') and kind==b'blob','Non-regular tracked input')
        tracked[path.decode()]={'bytes':int(size),'git_blob':oid.decode()}
    require(len(tracked)==471 and sum(v['bytes'] for v in tracked.values())==4984927,'Selection changed')
    selected=set(tracked)|{str(p.relative_to(ROOT)) for p in CANDIDATE.rglob('*') if p.is_file()}
    rules=HERE/'rules'; rules.write_text('\n'.join(PATTERNS)+'\n')
    excluded=['STATUS.md','.github/workflows/verify.yml','verification/old/receipt.json','cli-other/file','native/android-other/file','scripts/ci-other/file',str(ORIGINAL.relative_to(ROOT))+'/REVIEW.md']
    matched=run('git-rules',['git','-C',ROOT,'sparse-checkout','check-rules','--no-cone','--rules-file',rules,'-z'],('\0'.join(sorted(selected)+excluded)+'\0').encode())
    require(set(matched.decode().rstrip('\0').split('\0'))==selected,'Real Git selection mismatch')
    require(set(inputs)<=selected,'Missing owning inputs')
    unchanged=run('owning-baseline-diff',['git','diff','--name-only','f6ac52da8','HEAD','--',*sorted(inputs)])
    require(not unchanged,'Canonical owning sources changed from pair8')
    filemap={p:identity(ROOT/p) for p in sorted(selected)}
    for p,info in tracked.items():
        data=(ROOT/p).read_bytes()
        oid=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        require(oid==info['git_blob'],'Working tree drift '+p)
    save('selected-hashes.json',filemap); save('owning-hashes.json',inputs)
    projection_receipt={}
    with tempfile.TemporaryDirectory(prefix='selected-only-',dir=HERE) as td:
        projection=Path(td)
        for p in selected:
            target=projection/p; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/p,target)
        pb=load('review_projected_bootstrap',projection/CANDIDATE.relative_to(ROOT)/'bootstrap.py'); pa=pb.canonical()
        require(pa.ROOT==projection and pb.ROOT==projection,'Relocation used original root')
        require(pb.RUNNER==projection/'scripts/ci/check-android-generated-java.py','Relocated runner path wrong')
        pi=pb.admit_source_inputs(pa,pa.load_profile())
        require(pi==inputs,'Projected owning closure differs')
        for rel in ('cli/Package.swift','scripts/ci/check-android-binding.py'):
            p=projection/rel; data=p.read_bytes(); p.unlink()
            try:
                try: pb.admit_source_inputs(pa,pa.load_profile())
                except (RuntimeError,FileNotFoundError): pass
                else: raise RuntimeError('Missing input accepted '+rel)
            finally: p.write_bytes(data)
        p=projection/'sdk/Package.swift'; data=p.read_bytes(); p.write_bytes(data+b'\n// review negative control\n')
        try:
            try: pb.admit_source_inputs(pa,pa.load_profile())
            except RuntimeError: pass
            else: raise RuntimeError('Changed input accepted')
        finally: p.write_bytes(data)
        for mode,options in [('normal',[]),('optimized',['-O'])]:
            for name,count in [('test_bootstrap.py',22),('test_sparse_checkout.py',12)]:
                run(name[:-3]+'-'+mode,[sys.executable,'-I','-B','-S',*options,HERE/'replay_controls.py',projection/CANDIDATE.relative_to(ROOT)/name],tests=count)
            run('failure-'+mode,[sys.executable,'-I','-B','-S',*options,HERE/'replay_controls.py',HERE/'test_failure_paths.py'],tests=2)
        require(pb.admit_source_inputs(pa,pa.load_profile())==inputs,'Projection postflight drift')
        projection_receipt={'root':str(projection),'owning_count':len(pi),'owning_digest':pa.source_digest(pi),'relocated_canonical_runner':str(pb.RUNNER),'omission_controls':2,'tamper_controls':1}
    require(not Path(projection_receipt['root']).exists(),'Projection not cleaned')
    disk={}; b.disk_admission(HERE,disk)
    save('actual-local-disk.json',dict(scope='Actual review filesystem only, not hosted capacity',**disk))
    check_pins()
    save('result.json',{'verdict':'ACCEPT','scope':'Sparse fix proposal adoption only; hosted execution pending','observed_utc':datetime.now(timezone.utc).isoformat(),'revision':pins['revision'],'tree':pins['tree'],'source_pair':'mixer.android-source-pair.8','owning_digest':EXPECTED,'owning_inputs':101,'tracked_selected_files':len(tracked),'tracked_selected_bytes':sum(v['bytes'] for v in tracked.values()),'selected_files_including_candidate':len(selected),'selected_bytes_including_candidate':sum(v['bytes'] for v in filemap.values()),'selected_digest':a.source_digest(filemap),'controls_per_mode':36,'modes':['normal','-O'],'projection':projection_receipt,'projection_removed':True,'all_pins_unchanged':True,'owning_sources_unchanged_from':'f6ac52da8','minimum_free_bytes':b.MINIMUM_FREE_BYTES,'tools':pins['tools'],'not_performed':['compiler','tool download/install/extraction','native','process/device probing','hosted execution','dispatch','cloud','delegation','commit','push','canonical edits']})
    print((HERE/'result.json').read_text())
if __name__=='__main__': main()
