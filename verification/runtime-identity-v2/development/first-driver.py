#!/usr/bin/env python3
"""Qualify owned identity2 source against explicitly frozen legacy dependencies."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
BASE='aca686bfc72b8f18db727de5307977fb51790e0a'

def digest(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','--no-replace-objects',*args],cwd=ROOT)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);parser.add_argument('--swift',default=shutil.which('swift'));args=parser.parse_args()
    output=args.output.absolute();output.mkdir(parents=True,exist_ok=False);source=output/'source';source.mkdir()
    receipt={'schema':1,'baseline_revision':BASE,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':'gpt-6.1-sol','reasoning_effort':'xhigh','commands':[],'inputs':{},'exported_files':{},'preserved_v1_files':{},'scope':'Host identity2/parser/declared-copy/material-role/source-emission tests only; no release3 verifier, authority, graph completeness, linked SDK/adapter proof, native VM or device qualification.'}
    try:
        baseline_paths=git('ls-tree','-r','--name-only',BASE,'runtime-identity').decode().splitlines()
        current_paths=[p for p in (ROOT/'runtime-identity').rglob('*') if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in ['.build','.swiftpm','__pycache__'])]
        current={str(p.relative_to(ROOT)):p.read_bytes() for p in current_paths}
        exceptions={'runtime-identity/README.md','runtime-identity/build-tools/README.md','runtime-identity/Sources/MixerIdentityTool/main.swift'}
        for name in baseline_paths:
            if name not in exceptions:
                raw=git('show',BASE+':'+name)
                if current.get(name)!=raw:raise ValueError('v1 byte preservation failed '+name)
                receipt['preserved_v1_files'][name]=digest(raw)
        frozen=[]
        for prefix in ['updates/Sources','updates/Tests','updates/Package.swift','updates/Package.resolved','contracts','capabilities/schema','vm/include/mixer_vm.h','vm/include/mixer_vm_capability.h','activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json']:
            frozen.extend(git('ls-tree','-r','--name-only',BASE,prefix).decode().splitlines())
        for name in sorted(set(frozen)):
            raw=git('show',BASE+':'+name);path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);receipt['exported_files'][name]={'sha256':digest(raw),'origin':BASE}
        for name,raw in current.items():
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);receipt['inputs'][name]=digest(raw);receipt['exported_files'][name]={'sha256':digest(raw),'origin':'working-owned-source'}
        receipt['driver_sha256']=digest(Path(__file__).read_bytes());receipt['source_manifest_sha256']=digest(json.dumps(receipt['exported_files'],sort_keys=True,separators=(',',':')).encode())
        swift=str(Path(args.swift).absolute());env=dict(os.environ);env['MIXER_SWIFT']=swift
        def run(label,argv,extra=None):
            began=time.monotonic();command_env=dict(env);command_env.update(extra or {})
            result=subprocess.run([str(x) for x in argv],cwd=source,env=command_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
            path=output/(label+'.log');path.write_bytes(result.stdout)
            receipt['commands'].append({'label':label,'argv':[str(x) for x in argv],'cwd':str(source),'environment_overrides':extra or {},'exit_code':result.returncode,'elapsed_seconds_development_only':round(time.monotonic()-began,3),'log':path.name,'log_sha256':digest(result.stdout)})
            if result.returncode:raise ValueError('command failed: '+label)
            return result.stdout
        run('swift-version',[swift,'--version']);run('python-version',[sys.executable,'--version']);run('git-version',['git','--version'])
        package=source/'runtime-identity'
        run('v1-vectors',[sys.executable,package/'tools/vectors.py','--check']);run('v2-vectors',[sys.executable,package/'tools/vectors_v2.py','--check'])
        run('swift-debug-tests',[swift,'test','--package-path',package]);run('swift-release-tests',[swift,'test','--package-path',package,'-c','release'])
        run('cli-debug-build',[swift,'build','--package-path',package,'--product','mixer-identity'])
        binary_dir=run('cli-path',[swift,'build','--package-path',package,'--show-bin-path']).decode().strip();tool=Path(binary_dir)/'mixer-identity'
        receipt['cli_binary_sha256']=digest(tool.read_bytes())
        for mode,flags in [('normal',[]),('optimized',['-O'])]:
            run('python-'+mode,[sys.executable,*flags,'-B','-m','unittest','discover','-s',package/'build-tools/tests','-v'],{'MIXER_IDENTITY_TOOL':str(tool),'MIXER_IDENTITY_V2_EVIDENCE':str(output/('consumer-'+mode))})
        for name,expected in receipt['inputs'].items():
            if digest((ROOT/name).read_bytes())!=expected:raise ValueError('owned source changed during qualification '+name)
        for name,record in receipt['exported_files'].items():
            if digest((source/name).read_bytes())!=record['sha256']:raise ValueError('export source changed during qualification '+name)
        receipt['inputs_unchanged']=True;receipt['result']='PASS';receipt['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    except BaseException as error:
        receipt['result']='FAIL';receipt['error']=str(error);raise
    finally:
        receipt['artifacts']={str(p.relative_to(output)):digest(p.read_bytes()) for p in output.rglob('*') if p.is_file() and 'source' not in p.relative_to(output).parts and p.name!='receipt.json'}
        (output/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'result':receipt['result'],'receipt':str(output/'receipt.json'),'sha256':digest((output/'receipt.json').read_bytes())}))
if __name__=='__main__':main()
