#!/usr/bin/env python3
"""Independent original Go v3 public-API review, isolated copied source only."""
import argparse,hashlib,json,os
from pathlib import Path
import shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2];BASE='aca686bfc72b8f18db727de5307977fb51790e0a'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def head(major,n):
    if n<24:return bytes([major*32+n])
    for size,code in [(1,24),(2,25),(4,26),(8,27)]:
        if n<1<<(size*8):return bytes([major*32+code])+n.to_bytes(size,'big')
    raise ValueError('uint64 bound')
def cbor(value):
    if type(value) is bool:return bytes([245 if value else 244])
    if type(value) is int and value>=0:return head(0,value)
    if type(value) is str:
        raw=value.encode();return head(3,len(raw))+raw
    if type(value) is list:return head(4,len(value))+b''.join(cbor(x) for x in value)
    if type(value) is dict:
        entries=sorted((cbor(k),cbor(v)) for k,v in value.items());return head(5,len(entries))+b''.join(k+v for k,v in entries)
    raise ValueError('outside restricted oracle model')
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
        vector=json.loads(files['services/protocol/testdata/signed-release-v3.json'])
        oracle=[]
        for field,cbor_key,message_key,domain in [('signed_manifest','manifest_cbor_hex','manifest_message_hex',b'mixer.artifact.v3\0'),('signed_assignment','assignment_cbor_hex','assignment_message_hex',b'mixer.assignment.v3\0')]:
            obj=vector[field]['manifest' if field=='signed_manifest' else 'assignment'];raw=cbor(obj)
            if raw.hex()!=vector[cbor_key] or (domain+raw).hex()!=vector[message_key]:raise ValueError('independent Python CBOR/domain mismatch')
            oracle.append({'field':field,'cbor_sha256':sha(raw),'domain_hex':domain.hex()})
        raw=cbor(vector['grant_descriptor'])
        if raw.hex()!=vector['grant_descriptor_cbor_hex'] or sha(raw)!='b394ffd165ef28977de9743b1c1a98c419504787f2912e30d419cfb1582e15e1':raise ValueError('independent grant CBOR mismatch')
        if sha(cbor(vector['signed_manifest']['manifest']))!=vector['artifact_sha256']:raise ValueError('independent artifact identity mismatch')
        receipt['independent_python_cbor_oracle']=oracle;receipt['grant_descriptor_sha256']=sha(raw)
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
        if sha(review.read_bytes())!=receipt['review_test_sha256']:raise ValueError('independent test changed during run')
        receipt['inputs_unchanged']=True;receipt['result']='PASS';receipt['generator_reproduces_exact_fixture_bytes']=True
    except BaseException as e:receipt['result']='FAIL';receipt['error']=str(e);raise
    finally:
        receipt['logs']={p.name:sha(p.read_bytes()) for p in output.glob('*.log')};(output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');print(json.dumps({'result':receipt['result'],'sha256':sha((output/'receipt.json').read_bytes())}))
if __name__=='__main__':main()
