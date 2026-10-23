#!/usr/bin/env python3
"""Independent original Go v3 public-API review, isolated copied source only."""
import argparse,hashlib,json,os
from pathlib import Path
import shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2];BASE='aca686bfc72b8f18db727de5307977fb51790e0a'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','--no-replace-objects',*args],cwd=ROOT)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();output=args.output.absolute();output.mkdir(parents=True,exist_ok=False);source=output/'source';source.mkdir()
    paths=list((ROOT/'services/protocol').glob('*.go'))+list((ROOT/'services/protocol/testdata').glob('*'))+[ROOT/'services/go.mod',ROOT/'services/go.sum',ROOT/'contracts/release-v3.json',ROOT/'contracts/release-v2.json',ROOT/'contracts/release-v1.json']
    files={str(p.relative_to(ROOT)):p.read_bytes() for p in paths if p.is_file()}
    receipt={'schema':1,'baseline':BASE,'model':'gpt-6.1-sol','reasoning_effort':'xhigh','commands':[],'inputs':{name:sha(raw) for name,raw in sorted(files.items())},'old_files_preserved':{},'scope':'Independent host Go v3 primitive/header/payload/assignment/public-JSON review only; no service route/storage/Swift/native/device/publication qualification.'}
    try:
        # Protocol's HTTP-shape legacy test imports the existing release package.
        # Export those dependencies from committed baseline, never a mutable lane.
        dependencies={}
        for name in git('ls-tree','-r','--name-only',BASE,'services').decode().splitlines():
            if name.startswith('services/protocol/') or '/verification/' in name or not name.endswith(('.go','.sql','go.mod','go.sum')):continue
            raw=git('show',BASE+':'+name);dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);dependencies[name]=sha(raw)
        receipt['baseline_dependency_files']=dependencies
        for name,raw in files.items():
            dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        for name in git('ls-tree','-r','--name-only',BASE,'services/protocol').decode().splitlines():
            if name in files and name!='services/protocol/json_shape.go':
                old=git('show',BASE+':'+name)
                if files[name]!=old:raise ValueError('old file changed '+name)
                receipt['old_files_preserved'][name]=sha(old)
        oldshape=git('show',BASE+':services/protocol/json_shape.go');newshape=files['services/protocol/json_shape.go'];addition=b'\tcase reflect.TypeFor[ManifestV3](), reflect.TypeFor[AssignmentV3](), reflect.TypeFor[SignedManifestV3](), reflect.TypeFor[SignedAssignmentV3]():\n\t\treturn MaxV3DocumentBytes\n'
        if newshape.replace(addition,b'',1)!=oldshape:raise ValueError('shape diff exceeds v3 type case')
        receipt['json_shape_additive_case_only']=True
        review=ROOT/'verification/release-v3-go-review/review_test.go';receipt['review_test_sha256']=sha(review.read_bytes());receipt['driver_sha256']=sha(Path(__file__).read_bytes())
        def run(label,cmd,cwd=source/'services'):
            began=time.monotonic();r=subprocess.run([str(x) for x in cmd],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
            (output/(label+'.log')).write_bytes(r.stdout);receipt['commands'].append({'label':label,'argv':[str(x) for x in cmd],'cwd':str(cwd),'exit_code':r.returncode,'development_seconds':round(time.monotonic()-began,3),'log_sha256':sha(r.stdout)})
            if r.returncode:raise ValueError('failed '+label)
        run('go-version',['go','version']);run('root-protocol-tests',['go','test','-count=1','-v','./protocol']);run('root-protocol-race',['go','test','-race','-count=1','./protocol']);run('independent-tests',['go','test','-count=1','-v',review]);run('independent-race',['go','test','-race','-count=1','-v',review]);run('vet',['go','vet','./protocol'])
        generated={name:sha(raw) for name,raw in files.items() if name.endswith(('signed-release-v3.json','release-v3-cases.json'))}
        run('generator',['go','run','./protocol/testdata/generate-v3.go','--test-fixtures-only','--repository',source])
        for name,want in generated.items():
            if sha((source/name).read_bytes())!=want:raise ValueError('generator drift '+name)
        for name,want in receipt['inputs'].items():
            if sha((ROOT/name).read_bytes())!=want:raise ValueError('production input changed '+name)
        receipt['inputs_unchanged']=True;receipt['result']='PASS';receipt['generator_reproduces_exact_fixture_bytes']=True
    except BaseException as e:receipt['result']='FAIL';receipt['error']=str(e);raise
    finally:
        receipt['logs']={p.name:sha(p.read_bytes()) for p in output.glob('*.log')};(output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');print(json.dumps({'result':receipt['result'],'sha256':sha((output/'receipt.json').read_bytes())}))
if __name__=='__main__':main()
