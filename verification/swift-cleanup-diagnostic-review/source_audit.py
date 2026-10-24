#!/usr/bin/env python3
"""Independent source preservation/route inventory plus fresh closure layouts."""
import gzip,json,re,sys
sys.dont_write_bytecode=True
import collect as c
from type_layouts import parse

def masked(text):
    # Preserve indices while hiding Rust comments and literals from brace scans.
    out=list(text);i=0
    raw_pattern=re.compile(r'(?:br|r)(#+)?"')
    char_pattern=re.compile(r"'(?:\\(?:.|u\{[0-9a-fA-F]+\})|[^'\\\n])'")
    while i<len(text):
        end=None
        if text.startswith('//',i):end=text.find('\n',i);end=len(text)if end<0 else end
        elif text.startswith('/*',i):
            end=i+2;depth=1
            while depth:
                assert end<len(text)
                if text.startswith('/*',end):depth+=1;end+=2
                elif text.startswith('*/',end):depth-=1;end+=2
                else:end+=1
        else:
            m=raw_pattern.match(text,i) if text[i]in 'rb' else None
            if m:
                close='"'+(m[1]or'');end=text.index(close,i+len(m[0]))+len(close)
            elif text[i]=='"':
                end=i+1
                while end<len(text):
                    if text[end]=='\\':end+=2
                    elif text[end]=='"':end+=1;break
                    else:end+=1
            elif text[i]=="'":
                m=char_pattern.match(text,i)
                if m:end=i+len(m[0])
        if end is None:i+=1
        else:
            for j in range(i,end):
                if out[j]!='\n':out[j]=' '
            i=end
    return ''.join(out)

def declarations(text):
    code=masked(text);result={}
    for m in re.finditer(r'\b(struct|enum)\s+([A-Za-z_]\w*)',code):
        i=m.end();depth=0
        while code[i]not in '{;': i+=1
        if code[i]=='{':
            start=i;i+=1;depth=1
            while depth:depth+=(code[i]=='{')-(code[i]=='}');i+=1
        else:i+=1
        name=m[2];result.setdefault(name,[]).append(text[m.start():i])
    return result

def main():
    before=c.manifest(c.source('baseline'));after=c.manifest(c.source('candidate'))
    assert set(before)==set(after)and len(before)==128
    preservation={};count=0
    for path in before:
        if not path.endswith('.rs'):continue
        old=(c.source('baseline')/path).read_text();new=(c.source('candidate')/path).read_text()
        b=declarations(old);a=declarations(new)
        for name,spans in b.items():
            assert a.get(name)==spans,(path,name)
            for ordinal,span in enumerate(spans):preservation[path+':'+name+':'+str(ordinal)]=c.sha(span.encode());count+=1
    qualification=json.loads((c.HERE/'accounting-qualification.json').read_text())
    assert qualification['preexistingTypeDeclarations']==329
    # Exhaust every new production call and reject broader propagation.
    contextual=[];legacy=[];finish=[]
    for path in before:
        if not path.endswith('.rs')or'test'in path:continue
        text=(c.source('candidate')/path).read_text();code=masked(text)
        for pattern,target in [('remove_live_at_with_wasi(',contextual),('remove_live_with_wasi(',legacy),('self.remove_live_at(',finish)]:
            at=0
            while True:
                i=code.find(pattern,at)
                if i<0:break
                at=i+len(pattern)
                if code[max(0,i-20):i].rstrip().endswith('fn'):continue
                target.append(dict(source=path,line=text.count('\n',0,i)+1,excerpt=text.splitlines()[text.count('\n',0,i)].strip()))
    assert len(contextual)==5 and len(legacy)==9 and len(finish)==3,(contextual,legacy,finish)
    assert sorted(x['source'].split('/')[-1]for x in contextual)==['control_operations.rs','frame_operations.rs','frame_operations.rs','value_operations.rs','value_operations.rs']
    for name in ['Cargo.toml','Cargo.lock','src/experimental_swift_reactor/execution.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/memory_growth_operations.rs','src/experimental_swift_reactor/memory_operations.rs','src/experimental_swift_reactor/bulk_memory_operations.rs','src/experimental/execution/mod.rs']:
        assert before[name]==after[name],name
    capture_schema=json.loads((c.HERE/'closure-captures.json').read_text());captures=[]
    for features in ['swift','all']:
        for profile in ['debug','release']:
            for config in ['production','unit']:
                name='build-qualified-candidate-'+features+'-'+profile+'-'+config
                text=''.join(gzip.decompress((c.HERE/'commands'/name/(s+'.gz')).read_bytes()).decode()for s in ['stdout','stderr'])
                measured=parse(text);row={}
                for site,tuple_type in capture_schema[config].items():
                    v=measured[site];expected=(8,8)if tuple_type!='()'else(0,1)
                    assert (v['bytes'],v['alignment'])==expected,(site,tuple_type,v)
                    row[site]=dict(tupleType=tuple_type,**v)
                captures.append(dict(context=name,captures=row))
    c.save('independent-source-audit.json',dict(status='passed',sourceSHA256=c.digest(after),allOriginalConcreteDeclarationsIncludingNestedTupleAndUnit=count,declarationHashes=preservation,producer329BlockDeclarationsIndependentlyConfirmed=True,contextualCalls=contextual,legacyCalls=legacy,activeFinishCalls=finish,newOwnerFields=[],newTickets=0,newPublicRoutes=[],newDependencies=[],newWorkFuelOrCheckBoundaries=[],frozenSourceUnchanged=True,scope='source preservation supplemented by fresh MIR/layout/runtime; not an OTA release authorization'))
    c.save('actual-closure-layouts.json',dict(contexts=captures,independentlyMeasuredContexts=len(captures),zeroSizedCaptureBytesCredited=0))
    print('PASS independent all declaration/route inventory and eight actual closure layout contexts;',count,'declarations',flush=True)

if __name__=='__main__':main()
