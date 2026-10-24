#!/usr/bin/env python3
from pathlib import Path
import gzip,json,re
import run as r
def item(text,keyword):
    start=text.index(keyword);at=text.index('{',start);depth=0;quoted=False;escaped=False
    for i in range(at,len(text)):
        ch=text[i]
        if quoted:
            if escaped:escaped=False
            elif ch=='\\':escaped=True
            elif ch=='"':quoted=False
        elif ch=='"':quoted=True
        elif ch=='{':depth+=1
        elif ch=='}':
            depth-=1
            if depth==0:return text[start:i+1]
    raise AssertionError(keyword)
def main():
    identities=json.loads((r.PRODUCER/'frozen-identity.json').read_text());expanded={};maps={};owners={}
    for label in ['baseline','candidate']:
        text=gzip.decompress((r.HERE/'commands'/('fresh-expanded-'+label)/'stdout.gz').read_bytes()).decode()
        body=item(text,'impl SpanInstance {');expanded[label]=body
        names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',body,re.M);assert len(names)==39
        maps[label]={name:r.sha(item(body,'fn '+name+'(').encode())for name in names}
        data=r.archive(r.PRODUCER/(label+'-source.tar.gz'));decls={}
        for keyword in identities['containingOwners']:
            hits=[(p,b.decode())for p,b in data.items()if p.endswith('.rs')and keyword in b.decode()and(keyword!='struct Frame' or p=='src/experimental/execution/mod.rs')]
            assert len(hits)==1,(keyword,[h[0]for h in hits])
            path,source=hits[0];decls[keyword]=dict(path=path,sha256=r.sha(item(source,keyword).encode()))
        for keyword in ['pub(crate) struct GrowthTransfer','pub(crate) struct ExecutionParts']:
            hits=[(p,b.decode())for p,b in data.items()if p.endswith('.rs')and keyword in b.decode()]
            assert len(hits)==1,(keyword,[h[0]for h in hits]);path,source=hits[0];decls[keyword]=dict(path=path,sha256=r.sha(item(source,keyword).encode()))
        owners[label]=decls
    assert expanded['baseline']==expanded['candidate']
    assert maps['baseline']==maps['candidate']==identities['methods']
    assert owners['baseline']==owners['candidate']
    for keyword,digest in identities['containingOwners'].items():assert owners['candidate'][keyword]['sha256']==digest,(keyword,digest,owners['candidate'][keyword])
    base=r.archive(r.PRODUCER/'baseline-source.tar.gz');candidate=r.archive(r.PRODUCER/'candidate-source.tar.gz')
    for filename in ['control.rs','cache.rs']:
        p='src/experimental_swift_reactor/'+filename;assert base[p]==candidate[p]
    assert base['src/experimental_wasi/accounted.rs']==candidate['src/experimental_wasi/accounted.rs']
    for filename in ['memory_operations.rs','bulk_memory_operations.rs']:
        p='src/experimental_swift_reactor/'+filename;assert base[p].split(b'// ACCOUNTING_START')[1]==candidate[p].split(b'// ACCOUNTING_START')[1]
    r.write(r.HERE/'frozen-audit.json',dict(completeExpandedImplSHA256=r.sha(expanded['candidate'].encode()),methodCount=len(maps['candidate']),methods=maps['candidate'],acceptedOwnerCount=14,additionalOwners=['GrowthTransfer','ExecutionParts'],owners=owners['candidate'],actualControllerCacheWasiIdentical=True,acceptedAccountingTailsIdentical=True))
    print('PASS fresh compiler expansion: complete Frozen impl/all39methods identical;14accepted+2additional owner declarations identical;control/cache/WASI+old accounting tails identical')
if __name__=='__main__':main()
