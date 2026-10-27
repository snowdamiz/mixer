#!/usr/bin/env python3
"""Read-only full-packet/custody/derivation verification, no subprocesses."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    raw=(HERE/'seal.json').read_bytes();seal=json.loads(raw);expected={r['path']:r for r in seal['members']}
    actual={p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.name!='seal.json'}
    if actual!=set(expected):raise ValueError('full immutable packet membership')
    for name,r in expected.items():
        p=HERE/name
        if p.is_symlink() or not p.resolve().is_relative_to(HERE):raise ValueError('foreign member')
        b=p.read_bytes()
        if (len(b),sha(b))!=(r['bytes'],r['sha256']):raise ValueError('sealed packet member:'+name)
    import derive as D
    result=D.derive()
    for name,value in result.items():
        if D.canon(json.loads((HERE/name).read_bytes()))!=D.canon(value):raise ValueError('stale source derivation:'+name)
    final=json.loads((HERE/'final-validation.json').read_bytes())
    for name in final['qualifying_commands']:
        p=HERE/'commands'/name;r=json.loads((p/'receipt.json').read_bytes())
        if not (r['exit_code']==0 and not r['timed_out'] and r['child_reaped'] and r['owned_group_absent'] and r['input_custody_unchanged'] and not r['preparation_only']):raise ValueError('qualifying same-script command terminal/custody')
        for kind in ('stdout','stderr'):
            b=(p/kind).read_bytes();e=r[kind]
            if (len(b),sha(b))!=(e['bytes'],e['sha256']):raise ValueError('qualifying output custody')
        for filename,member in r['source_scripts'].items():
            b=(HERE/filename).read_bytes()
            if (len(b),sha(b))!=(member['bytes'],member['sha256']):raise ValueError('final source differs from qualifying command:'+filename)
    print(json.dumps({'seal_sha256':sha(raw),'members':len(expected),'bytes':sum(x['bytes'] for x in expected.values()),'priced_input_members':len(result['input-custody.json']['files']),'closed_interfaces':11,'partial_positive_frontiers':3,'status':'readonly-seal-custody-and-source-derivation-pass','runtime_or_native_or_root_price_acceptance':False}))
if __name__=='__main__':main()
