#!/usr/bin/env python3
"""Positive additive named objects for the uncalled host seam, not stack/RSS.

New source/argument/return/caller placements and all source aliases are charged
separately. Existing rows, owners, padding and foundational observation slots
provide no credit. Unit positions are additional to production positions.
"""
from pathlib import Path
import gzip, json, re
from collect import HERE, enc, save

def split_top(text):
    result=[];start=0;depth=0
    for i,c in enumerate(text):
        if c in '<([{':depth+=1
        elif c in '>)]}':depth-=1
        elif c==',' and depth==0:result.append(text[start:i].strip());start=i+1
    return [v for v in result+[text[start:].strip()] if v]
def selected(name):
    if 'host_operation_tests.rs:' in name: return False
    return ('host_operation' in name
        or ('accounted::' in name and any('::'+n in name for n in ['dispatch','checked_usage','usage']))
        or ('descriptor::' in name and any('::'+n+'(' in name+'(' or '::'+n+'::' in name for n in ['parameters','results'])))
def bodies(text):
    for m in re.finditer(r'^fn ([^\n]+)',text,re.M):
        head=m[1];at=head.index('(');end=at+1;depth=1
        while depth:depth+=(head[end]=='(')-(head[end]==')');end+=1
        name=head[:at]
        if selected(name):yield name,head[at+1:end-1],text[m.start():text.find('\n}',m.start())+2],text.count('\n',0,m.start())+1
    for m in re.finditer(r'^const ([^\n]+)',text,re.M):
        head=m[1]
        if 'promoted[' in head and selected(head):
            yield head,'',text[m.start():text.find('\n}',m.start())+2],text.count('\n',0,m.start())+1
def normalize(ty,captures):
    ty=re.sub(r'\{closure@[^}]+\}',lambda m:captures[m[0]],ty)
    ty=re.sub(r"'[A-Za-z_][A-Za-z_0-9]*","'static",ty)
    for prefix,target in [('experimental_swift_reactor::','crate::experimental_swift_reactor::'),('experimental_wasi::','crate::experimental_wasi::'),('experimental::','crate::experimental::'),('control::','crate::experimental_swift_reactor::control::'),('accounted::','crate::experimental_wasi::accounted::')]:
        ty=re.sub(r'(?<![:\w])'+re.escape(prefix),target,ty)
    ty=ty.replace('crate::experimental_wasi::descriptor::WasiFunction','crate::experimental_wasi::WasiFunction')
    ty=re.sub(r'(?<![:\w])descriptor::WasiFunction','crate::experimental_wasi::WasiFunction',ty)
    ty=re.sub(r'(?<![:\w])execute::Cancellation','crate::Cancellation',ty)
    ty=re.sub(r"&(?!(?:'|\s*'))","&'static ",ty)
    return ty
def canonical(config):
    text=gzip.decompress((HERE/('mir-'+config+'.mir.gz')).read_bytes()).decode()
    functions=[];captures={};rows=[];manifest=[]
    for name,params,body,line in bodies(text):
        decl=dict(re.findall(r'let (?:mut )?(_\d+): ([^\n]+);',body))
        for arg in split_top(params):
            ident,ty=arg.split(': ',1);decl[ident]=ty
        for site in re.findall(r'\{closure@[^}]+\}',params):
            fields={int(i):ty for i,ty in re.findall(r'_1\.(\d+): ([^\n]*?)\)',body)}
            if fields:
                assert set(fields)==set(range(len(fields))),(name,fields)
                captures[site]='('+', '.join(fields[i] for i in range(len(fields)))+(',' if len(fields)==1 else '')+')'
            else:
                assert not re.search(r'_1\.\d+',body),name
                captures[site]='()'
        functions.append((name,params,body,line,decl))
    for ordinal,(name,params,body,line,decl) in enumerate(functions):
        aliases={}
        for source,ident in re.findall(r'debug ([\w_]+) => (_\d+);',body):aliases.setdefault(ident,[]).append(source)
        def add(binding,ty,kind,source,stem):
            for position in ['source','argument','returned','caller']:
                rows.append(dict(envelope='active',field=stem+'_'+position,rustType=normalize(ty,captures),
                    binding=binding,kind=kind,sourceNames=source,position=position,config=config,
                    mirFunction=name,mirLine=line,mirType=ty))
        for ident,ty in decl.items():
            add(ident,ty,'canonical',aliases.get(ident,[]),f'mir_{config}_{ordinal}_{ident[1:]}')
            for i,source in enumerate(aliases.get(ident,[])):
                add(source,ty,'authored-alias',[source],f'alias_{config}_{ordinal}_{ident[1:]}_{i}_{source}')
        literals=re.findall(r'const ("(?:[^"\\]|\\.)*"|true|false|\d+_(?:u|i)(?:size|8|16|32|64|128))',body)
        for i,literal in enumerate(literals):
            ty="&'static str" if literal.startswith('"') else 'bool' if literal in ['true','false'] else literal.rsplit('_',1)[1]
            add('literal_'+str(i),ty,'direct-literal',[literal],f'literal_{config}_{ordinal}_{i}')
        manifest.append(dict(config=config,function=name,mirLine=line,canonicalTypedBindings=len(decl),
            sourceAliases=sum(map(len,aliases.values())),directTypedLiterals=len(literals)))
    return rows,manifest,captures
def main():
    rows=[];functions=[];captures={}
    for config in ['production','unit']:
        r,f,c=canonical(config);rows+=r;functions+=f;captures[config]=c
    # The original fixed slot remains the sole outcome. These are fresh charged
    # caller and terminal-completion placements, never an additional live slot.
    roles={
      'caller_storage':"FrameOperationStorage<'static>",
      'completion_storage':"FrameOperationStorage<'static>",
      'completion_drop_tuple':"(ExecutionParts<'static,SwiftMode>,FrameOperationStorage<'static>)",
      'outcome':"Option<Result<(),SwiftRunFailure>>",
      'outcome_result':"Result<(),SwiftRunFailure>",
      'outer_publication':"Result<(),SwiftRunFailure>",
      'first_failure':"Option<SwiftRunFailure>",
      'failure':"SwiftRunFailure",
      'drain_report':"FrameDrainReport",
      'completion':"FrameCompletion",
      'after_cleanup':"Option<SwiftRunUsage>",
    }
    for name,ty in roles.items():
        for position in ['source','argument','returned','caller']:
            rows.append(dict(envelope='permanent',field='fixed_'+name+'_'+position,rustType=ty,
                kind='authored-fixed-boundary',config='source',binding=name,position=position))
    rendered=[]
    for envelope,cls in [('permanent','HostPermanentPositions'),('active','HostActivePositions')]:
        rendered.append('pub(super) struct '+cls+' {')
        for row in rows:
            if row['envelope']!=envelope:continue
            row['ownerClass']=cls
            if row['config']=='unit':rendered.append('    #[cfg(test)]')
            rendered.append('    '+row['field']+': '+row['rustType']+',')
        rendered.append('}')
    (HERE/'positive-positions.rs').write_text('\n'.join(rendered)+'\n')
    save('inventory-schema.json',rows);save('function-manifest.json',functions);save('closure-captures.json',captures)
    print(len(rows),'positive fields',len(functions),'compiler bodies')
if __name__=='__main__':main()
