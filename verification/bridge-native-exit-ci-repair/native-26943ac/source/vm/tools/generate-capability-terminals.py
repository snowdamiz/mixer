#!/usr/bin/env python3
"""Original offline generator for fixed guest terminals; never runs during Cargo builds."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
CONTRACT_SHA = '052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439'
def outputs():
    path=ROOT/'contracts/guest-capability-transport-v1.json';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=CONTRACT_SHA:raise ValueError('coordinated transport contract changed')
    contract=json.loads(raw);hashes=json.loads((ROOT/'capabilities/schema/hashes.json').read_bytes())['capabilities']
    result={};arms=[];variants={1:'HttpRequest',2:'Get',3:'Put',4:'Delete'}
    failures=[('Unavailable','unavailable'),('Cancelled','cancelled'),('DeadlineExceeded','deadlineExceeded')]
    operations=contract['operations']
    if [x['tag'] for x in operations]!=[1,2,3,4]:raise ValueError('fixed operation table changed')
    for operation in operations:
        if hashes[operation['capability']]!=operation['schemaHash']:raise ValueError('schema hash mismatch')
        for variant,code in failures:
            if code not in next(x['codes'] for x in contract['completion']['outcomes'] if x['kind']=='failure'):raise ValueError('unknown fixed failure')
            name=operation['import']+'-'+code+'.json'
            payload={'abi':1,'capability':operation['capability'],'schemaHash':operation['schemaHash'],'operation':operation['operation'],'outcome':{'kind':'failure','code':code}}
            result['generated/'+name]=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
            arms.append(f'        (Operation::{variants[operation["tag"]]}, FailureCode::{variant}) => include_bytes!("generated/{name}"),')
    code='// Independently authored offline generator; frozen transport '+CONTRACT_SHA+'\nuse crate::experimental_capability::{FailureCode, Operation};\n#[rustfmt::skip]\npub(super) fn terminal(operation: Operation, failure: FailureCode) -> &\'static [u8] {\n    match (operation, failure) {\n'+'\n'.join(arms)+'\n    }\n}\n'
    result['fixed.rs']=code.encode();return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    target=ROOT/'vm/src/experimental_capability_guest';expected=outputs()
    for name,raw in expected.items():
        path=target/name
        if args.write:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        elif not path.is_file() or path.read_bytes()!=raw:raise ValueError('generated output differs: '+name)
    actual={p.name for p in (target/'generated').glob('*.json')}
    if actual!={Path(p).name for p in expected if p.endswith('.json')}:raise ValueError('unexpected fixed payload file')
    print(json.dumps({'fixed_payloads':12,'generated_files':len(expected),'contract_sha256':CONTRACT_SHA,'mode':'write' if args.write else 'checked'},sort_keys=True))
if __name__=='__main__':main()
