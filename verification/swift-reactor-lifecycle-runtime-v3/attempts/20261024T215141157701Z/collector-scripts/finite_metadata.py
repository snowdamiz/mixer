"""Exact V2 accepted finite representation rules; no broader normalization."""
import re
def footer(body):
    # Actual declarations, never labels guessed from counts or arbitrary tokens.
    starts=list(re.finditer(r'^alloc\d+ \(size: \d+, align: \d+\) \{',body,re.M))
    return [(m.group().split(' ',1)[0],body[m.start():starts[i+1].start()if i+1<len(starts)else len(body)])for i,m in enumerate(starts)]

def rename(text,mapping):
    identifiers=re.findall(r'\balloc\d+\b',text)
    assert set(identifiers)<=set(mapping),'unbound allocation reference'
    return re.sub(r'\balloc\d+\b',lambda m:mapping[m[0]],text)

def display_free(value):
    # Session numeric DefIds retain every actual displayed definition path.
    if isinstance(value,str):return re.sub(r'DefId\(\d+:\d+ ~ ','DefId(<session-index> ~ ',value)
    if isinstance(value,list):return [display_free(x)for x in value]
    if isinstance(value,dict):return {k:display_free(v)for k,v in value.items()}
    return value

def finite_metadata(x,y,label,mapping,hygiene,hygiene_reverse,evidence,where):
    assert type(x)is type(y),(where,'metadata shape change')
    if isinstance(x,dict):
        assert set(x)==set(y)
        for k in x:finite_metadata(x[k],y[k],k,mapping,hygiene,hygiene_reverse,evidence,where+[k])
    elif isinstance(x,list):
        assert len(x)==len(y)
        for i,(a,b)in enumerate(zip(x,y)):finite_metadata(a,b,label,mapping,hygiene,hygiene_reverse,evidence,where+[i])
    elif isinstance(x,str)and x==y:
        if label in ['span','sourceInfo']:
            for index in re.findall(r'\(#(\d+)\)',x):
                assert index not in hygiene or hygiene[index]==index
                assert index not in hygiene_reverse or hygiene_reverse[index]==index
                hygiene[index]=index;hygiene_reverse[index]=index
    elif isinstance(x,str)and x!=y:
        if label=='constant':
            assert display_free(rename(x,mapping))==display_free(y),(where,'constant value changed')
            evidence.append({'field':where,'kind':'finite-allocation-reference-or-session-display','old':x,'new':y})
        elif label in ['span','sourceInfo']:
            old=re.findall(r'\(#(\d+)\)',x);new=re.findall(r'\(#(\d+)\)',y)
            assert len(old)==len(new)>0 and re.sub(r'\(#\d+\)','(#bound-context)',x)==re.sub(r'\(#\d+\)','(#bound-context)',y),(where,'source coordinates or scope changed')
            for a,b in zip(old,new):
                assert a not in hygiene or hygiene[a]==b
                assert b not in hygiene_reverse or hygiene_reverse[b]==a
                hygiene[a]=b;hygiene_reverse[b]=a
            evidence.append({'field':where,'kind':'finite-source-hygiene-index','old':x,'new':y,'sameFullFileCoordinatesAndScope':True,'fullExpansionChainQueried':False})
        else:
            assert display_free(x)==display_free(y),(where,'unexplained metadata change')
            evidence.append({'field':where,'kind':'compiler-session-display-index','old':x,'new':y,'sameDisplayedDefinitionPath':True})
    else:assert x==y,(where,'actual metadata scalar changed')

