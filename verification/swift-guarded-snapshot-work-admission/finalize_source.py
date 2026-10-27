"""Reconcile the exact new MIR roles, then select their constant byte grant."""
from collections import Counter
from pathlib import Path
import difflib
import gzip
import json
import re
from prepare import HERE,BASE,CONTROL,TESTS,base_members,canonical,sha,write

def functions(label):
    text=(HERE/'commands'/label/'adoption-functions.mir').read_text()
    result={}
    for chunk in re.split(r'(?=^fn )',text,flags=re.M):
        if not chunk.startswith('fn '):continue
        head=chunk.split('\n',1)[0]
        name='core' if '::{closure#' not in head else head[head.index('::{closure#'):].split('(',1)[0]
        roles=[]
        for m in re.finditer(r'^\s+let (?:mut )?(_\d+): ([^;]+);([^\n]*)',chunk,re.M):
            roles.append(dict(local=m[1],type=re.sub(r'\{closure@[^}]+\}','{closure}',m[2]),source_span=m[3].strip()))
        result[name]=dict(body=chunk,roles=roles)
    return result

def main():
    assert not (HERE/'seal.json').exists()
    old,new=functions('metadata-base'),functions('metadata-probe-minimal')
    sizes={}
    raw=gzip.decompress((HERE/'commands/metadata-probe-minimal/stdout.gz').read_bytes())
    for name,size,alignment in re.findall(r'print-type-size type: `([^`]+)`: (\d+) bytes, alignment: (\d+) bytes',raw.decode()):
        sizes[name]=(int(size),int(alignment))
    sizes.update({'()':(0,1),'!':(0,1),'u64':(8,8),'bool':(1,1)})
    added=[];per_function=[]
    for name,b in new.items():
        a=old[name]
        ca=Counter(r['type'] for r in a['roles']);cb=Counter(r['type'] for r in b['roles'])
        assert not ca-cb,(name,dict(ca-cb))
        # Select actual injected source-span roles, then their referenced
        # compiler reborrow places. Do not assign arbitrary same-type old IDs.
        injected=lambda span: (m:=re.search(r'control.rs:(\d+):\d+: (\d+):\d+',span)) is not None and 704<=int(m[1])<=717
        direct=[r for r in b['roles'] if injected(r['source_span'])] if name=='::{closure#0}' else []
        used=set()
        for line in b['body'].splitlines():
            if injected(line) and 'let ' not in line:used.update(re.findall(r'\b_\d+\b',line))
        ids={r['local'] for r in direct}
        indirect=[r for r in b['roles'] if r['local'] in used and r['local'] not in ids and r['type'].startswith('&')]
        chosen=direct+indirect
        assert Counter(r['type'] for r in chosen)==cb-ca,(name,chosen,dict(cb-ca))
        for role in chosen:
            t=role['type'];size,align=(8,8) if t.startswith('&') else sizes[t]
            added.append(dict(function=name,**role,bytes=size,alignment=align))
        per_function.append(dict(function=name,before_roles=sum(ca.values()),after_roles=sum(cb.values()),
            added_types=dict(cb-ca),removed_types=dict(ca-cb)))
    # Equal type multisets preserve every old conservative role without credits.
    # The injection introduces no local into core or its four existing callbacks.
    assert len(added)==20 and sum(r['bytes'] for r in added)==1436
    for name in old:
        if name!='::{closure#0}':assert Counter(r['type'] for r in old[name]['roles'])==Counter(r['type'] for r in new[name]['roles'])
    capture=lambda f:re.findall(r'^\s+debug [^\n]+=> \(\*\(\(\*_1\)\.(\d+): ([^)]+)\)\);',f,re.M)
    a=capture(old['::{closure#0}']['body']);b=capture(new['::{closure#0}']['body'])
    assert a==b and len(a)==8,(a,b)
    write('source-role-delta.json',dict(schema=1,baseline='metadata-base',candidate_probe='metadata-probe-minimal',
        added_roles=added,added_role_count=len(added),added_bytes=1436,per_function=per_function,
        closure_captures_before=a,closure_captures_after=b,closure_size_growth=0,
        no_removed_role_credit=True,old_selected_floor_charge_retained=200,
        existing_callee_templates=['Fault::new','Fault::limit','RuntimeControl::fail'],
        rule='New MIR declaration roles are added in full; old declarations retained. Existing nonrecursive callee source templates remain funded once; new callsites/returns are newly included. Physical stack/RSS/private std excluded.',
        role_pairing='Actual source-span injection roles plus their referenced compiler reborrows are named. Their type multiset equals the whole-function added multiset; no old role is removed or credited.'))
    text=(HERE/'overlay'/CONTROL).read_text()
    text=text.replace('// Initial metadata probe uses zero only until all newly introduced compiler\n// source roles are measured. It must not be frozen or dispatched as funding.\nconst SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 0;',
        '// Twenty new unoptimized compiler source roles total1436 logical bytes.\n// No old role is credited; core and all existing closure captures are unchanged.\nconst SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;')
    assert 'const SNAPSHOT_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1: usize = 1_436;' in text
    (HERE/'overlay'/CONTROL).write_text(text)
    (HERE/'source-delta.patch').write_text(''.join(difflib.unified_diff(
        (BASE/'source/vm'/CONTROL).read_text().splitlines(True),text.splitlines(True),
        fromfile='accepted-source144/'+CONTROL,tofile='candidate-source144/'+CONTROL)))
    manifest=json.loads((HERE/'source-manifest.json').read_text())
    for row in manifest['members']:
        p=HERE/'overlay'/row['path']
        if p.exists():row.update(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
    manifest['source_tree_sha256']=sha(canonical(manifest['members']))
    write('source-manifest.json',manifest)
    base=(BASE/'source/vm'/TESTS).read_bytes();append=(HERE/'host-controls.inc.rs').read_bytes()
    unit=HERE/'test-overlay'/TESTS;unit.parent.mkdir(parents=True,exist_ok=True);unit.write_bytes(base+append)
    write('test-overlay.json',dict(schema=1,base=dict(path=TESTS,bytes=len(base),sha256=sha(base)),
        append=dict(path='host-controls.inc.rs',bytes=len(append),sha256=sha(append)),
        materialized=dict(path='test-overlay/'+TESTS,bytes=unit.stat().st_size,sha256=sha(unit.read_bytes())),
        execution='only seven work_admission_host_ tests; in-memory actual parser/validator and synthetic private policy core; no loader/guest/cache/snapshot/writer',
        operational_selected_ingress_qualification=False))
    prep=json.loads((HERE/'preparation.json').read_text());prep['provisional_storage_delta']=False;prep['selected_storage_delta']=1436;write('preparation.json',prep)
    # Keep exact compiler output compact; its uncompressed SHA remains recorded.
    for folder in (HERE/'commands').iterdir():
        p=folder/'stdout'
        if p.exists():
            (folder/'stdout.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0));p.unlink()
            r=json.loads((folder/'receipt.json').read_text());r['stdout_storage']='stdout.gz (gzip, exact uncompressed SHA256)';(folder/'receipt.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()
