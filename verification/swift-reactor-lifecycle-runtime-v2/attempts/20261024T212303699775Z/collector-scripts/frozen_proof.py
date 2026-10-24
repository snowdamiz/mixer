#!/usr/bin/env python3
"""Fresh official expansion against exact retained full Frozen methods."""
import gzip,re
import collect as c

def item(text,key):
    a=text.index(key);b=text.index('{',a)+1;depth=1
    while depth:depth+=(text[b]=='{')-(text[b]=='}');b+=1
    return text[a:b]

code,attempt,out,err=c.run(['cargo','rustc','--lib','--locked','--offline','--all-features','--','-Zunpretty=expanded'],env_extra={'RUSTC_BOOTSTRAP':'1'},label='expanded-frozen-candidate')
assert code==0
oldroot=c.ROOT/'verification/swift-reactor-lifecycle-accounting'
oldrecord=c.read_json(oldroot/'frozen-identity.json')['candidate']
old=gzip.decompress((oldroot/oldrecord['attempt']/'stdout.log.gz').read_bytes()).decode()
records=[]
for label,text in [('sealed',old),('candidate',out.decode())]:
    body=item(text,'impl SpanInstance {')
    names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',body,re.M);assert len(names)==39
    records.append({n:item(body,'fn '+n+'(')for n in names})
assert records[0]==records[1]
c.save(c.HERE/'frozen-identity-proof.json',{'methods':39,'byteIdentical':True,'candidateAttempt':str(attempt.relative_to(c.HERE)),'oldAttempt':oldrecord['attempt'],'oldExpandedMethods':records[0],'newExpandedMethods':records[1],'methodSHA256':{k:c.sha(v.encode())for k,v in records[1].items()},'sourceClosure':c.read_json(c.HERE/'source-delta.json')['candidateClosure']})
print('All39 Frozen expanded methods byte-identical')
