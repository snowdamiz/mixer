#!/usr/bin/env python3
"""Independent input-capture review replay; no production/source mutations."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DEFAULT_REV='c01e8016880dcbf1c15010142ad856327d7ba0f8'
ROOT_RECEIPT=ROOT/'verification/input-capture-2026-10-22-final/receipt.json'
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--name',required=True);p.add_argument('--revision',default=DEFAULT_REV);p.add_argument('--identity-tool');p.add_argument('--expect-clean-diagnostic',action='store_true');a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',a.name):p.error('bounded ASCII name required')
    work=HERE/'.build'/a.name;out=HERE/'evidence'/a.name;work.mkdir(parents=True,exist_ok=False);out.mkdir(parents=True,exist_ok=False)
    env={k:v for k,v in os.environ.items() if k in {'HOME','USER','LOGNAME','PATH','TMPDIR','LANG','TERM'} or k.startswith('LC_')};env['PYTHONDONTWRITEBYTECODE']='1'
    commands=[];record={'schema':1,'reviewer':{'model':'gpt-6.1-sol','reasoning_effort':'xhigh'},'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'status':'running'}
    def run(name,argv,expected=0,extra=None):
        argv=[str(x) for x in argv];began=time.monotonic();result=subprocess.run(argv,cwd=ROOT,env=extra or env,capture_output=True,timeout=180)
        outputs={}
        for label,data in [('stdout',result.stdout),('stderr',result.stderr)]:path=out/(name+'.'+label);path.write_bytes(data);outputs[label]={'path':path.relative_to(ROOT).as_posix(),'sha256':digest(path),'bytes':len(data)}
        commands.append({'name':name,'argv':argv,'exit_code':result.returncode,'host_development_elapsed_seconds':round(time.monotonic()-began,6),'output':outputs});print(name+': '+str(result.returncode),flush=True)
        if result.returncode!=expected:raise RuntimeError('unexpected command result '+name)
        return result.stdout.decode()
    try:
        revision=run('revision',['/usr/bin/git','rev-parse',a.revision+'^{commit}']).strip();record['revision']=revision
        archive=work/'source.tar';run('source-export',['/usr/bin/git','archive','--format=tar','--output='+str(archive),revision,'runtime-identity','updates','activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json']);record['archive_sha256']=digest(archive)
        source=work/'source'
        with tarfile.open(archive) as stream:stream.extractall(source,filter='data')
        source_manifest={p.relative_to(source).as_posix():digest(p) for p in sorted(source.rglob('*')) if p.is_file()};record['source_manifest']=source_manifest;record['source_digest']=hashlib.sha256(json.dumps(source_manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        # Reuse the real CLI built by root from this frozen source; verify both its
        # receipt provenance reference and actual binary hash. No graph attestation.
        root_receipt=json.loads(ROOT_RECEIPT.read_bytes());record['root_qualification_receipt']={'path':ROOT_RECEIPT.relative_to(ROOT).as_posix(),'sha256':digest(ROOT_RECEIPT),'revision':root_receipt['sourceRevision']}
        tool=Path(a.identity_tool).absolute() if a.identity_tool else ROOT/'verification/local/input-capture-2026-10-22-final/source/runtime-identity/.build/out/Products/Debug/mixer-identity'
        tool_sha=digest(tool)
        if not a.identity_tool and (root_receipt['sourceRevision']!=DEFAULT_REV or root_receipt['identityToolSHA256']!=tool_sha):raise ValueError('root frozen CLI source/hash mismatch')
        record['identity_tool']={'path':str(tool),'sha256':tool_sha,'bytes':tool.stat().st_size,'source_provenance':'reused trusted real public Swift CLI; root frozen build receipt referenced; binary consumption is not independently attested'}
        record['python']=run('python-version',[sys.executable,'--version']).strip();record['swift']=run('swift-version',['/usr/bin/xcrun','swift','--version']).strip();record['os']=run('host-os',['/usr/bin/sw_vers']).strip()
        probe_env=dict(env,CAPTURE_REVIEW_MODULE=str(source/'runtime-identity/build-tools/capture.py'),CAPTURE_REVIEW_TOOL=str(tool),CAPTURE_REVIEW_DESCRIPTOR=str(source/'activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json'))
        record['tests_sha256']=digest(HERE/'ReviewTests.py');record['runner_sha256']=digest(Path(__file__));shutil.copyfile(HERE/'ReviewTests.py',out/'ReviewTests.py');shutil.copyfile(Path(__file__),out/'run.py')
        probe_env['CAPTURE_REVIEW_CLEAN_DIAGNOSTIC']='1' if a.expect_clean_diagnostic else '0';record['require_clean_diagnostic']=a.expect_clean_diagnostic
        for mode,flags in [('normal',[]),('optimized',['-O'])]:
            run('independent-'+mode,[sys.executable,*flags,'-B',HERE/'ReviewTests.py'],extra=probe_env)
            text=(out/('independent-'+mode+'.stderr')).read_text();match=re.search(r'Ran (\d+) tests? in ',text)
            if not match or not text.rstrip().endswith('OK'):raise ValueError('missing successful independent test count')
            record[mode+'_test_functions']=int(match[1])
        if any(digest(source/k)!=h for k,h in source_manifest.items()):raise ValueError('immutable review export mutated')
        if digest(tool)!=tool_sha or digest(HERE/'ReviewTests.py')!=record['tests_sha256']:raise ValueError('review tool/tests changed during run')
        record['source_unchanged']=True;record['status']='original host adversarial probes passed; diagnostic finding characterized separately'
    except BaseException as e:record['status']='failed';record['error']=str(e);raise
    finally:
        record['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'revision':record['revision'],'source_digest':record['source_digest'],'normal_test_functions':record['normal_test_functions'],'optimized_test_functions':record['optimized_test_functions'],'receipt':str(out/'receipt.json')},indent=2))
if __name__=='__main__':main()
