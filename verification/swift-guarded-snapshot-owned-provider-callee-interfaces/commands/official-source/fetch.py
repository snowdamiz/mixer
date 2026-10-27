#!/usr/bin/env python3
"""Retrieve only explicit official source files at the retained compiler revision."""
from pathlib import Path
import hashlib, json, ssl, sys, urllib.request
HERE=Path(__file__).resolve().parent
REV='b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
FILES=['library/core/src/iter/range.rs','library/core/src/iter/traits/collect.rs','library/core/src/slice/mod.rs','library/core/src/slice/cmp.rs','library/core/src/slice/memchr.rs','library/core/src/slice/iter.rs','library/core/src/iter/macros.rs','library/core/src/array/equality.rs','library/core/src/cmp.rs','library/core/src/option.rs','library/core/src/result.rs','library/core/src/num/uint_macros.rs','library/core/src/mem/mod.rs','library/core/src/intrinsics/mod.rs','library/core/src/ub_checks.rs','library/core/src/hint.rs','library/std/src/path.rs']
def main():
    out=HERE/'official-source'; out.mkdir(exist_ok=False)
    entries=[]
    for name in FILES:
        url='https://raw.githubusercontent.com/rust-lang/rust/'+REV+'/'+name
        req=urllib.request.Request(url,headers={'User-Agent':'Mixer-bounded-official-source-review/1'})
        with urllib.request.urlopen(req,timeout=8) as response:
            b=response.read(2000000); final=response.url; status=response.status
        if status!=200 or final!=url or len(b)>=2000000: raise ValueError('exact bounded source fetch')
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        entries.append({'path':name,'url':url,'final_url':final,'status':status,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    report={'schema':1,'repository':'https://github.com/rust-lang/rust','revision':REV,'bound_compiler_revision':'verification/swift-guarded-snapshot-owned-provider-work-storage/compiler-plan.json','tool':'Python urllib.request, '+sys.version,'tls':ssl.OPENSSL_VERSION,'members':entries}
    (HERE/'official-source-custody.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'source_members':len(entries),'bytes':sum(x['bytes'] for x in entries),'revision':REV}))
if __name__=='__main__':main()
