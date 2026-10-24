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
    return any(re.search(r'(?:^|::)'+n+r'(?=$|::|\()',name) for n in [
        'remove_live_at_with_wasi','primitive_pop','primitive_numeric',
        'control_remove','remove_live_at','finish_inner','host_operation_inner',
        'diagnostic_before_remove','diagnostic_numeric_before_remove','control_after_value_pop'])
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
    ty=re.sub(r"(?<![:\w])Cell<","std::cell::Cell<",ty)
    return ty
def canonical(config,prefix="full-preaccounting-mir"):
    text=gzip.decompress((HERE/(prefix+'-'+config+'.mir.gz')).read_bytes()).decode()
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
    # Every row adds new positive capacity. The shared contextual primitive and
    # value leaves are charged once in the nested value envelope. Remaining
    # changed active routes are charged once in the containing frame envelope.
    for r in rows:
        r['ownerClass'] = ('DiagnosticValuePositions' if any(re.search(r'(?:^|::)'+n+r'(?=$|::)',r['mirFunction']) for n in
            ['remove_live_at_with_wasi','primitive_pop','primitive_numeric','diagnostic_numeric_before_remove'])
            else 'DiagnosticFramePositions')
    for name,ty in {'failure':'SwiftRunFailure','first_failure':'Option<SwiftRunFailure>',
                   'after_cleanup':'Option<SwiftRunUsage>','fault':'Fault','cursor':'Cursor'}.items():
        for position in ['source','argument','returned','caller']:
            rows.append(dict(envelope='permanent',field='retained_'+name+'_'+position,rustType=ty,
                ownerClass='DiagnosticPermanentPositions',kind='authored-retained',config='source',binding=name,position=position))
    rendered=[]
    for cls in ['DiagnosticValuePositions','DiagnosticFramePositions','DiagnosticPermanentPositions']:
        rendered.append('pub(in crate::experimental_swift_reactor) struct '+cls+' {')
        for row in rows:
            if row['ownerClass']!=cls:continue
            if row['config']=='unit':rendered.append('    #[cfg(test)]')
            rendered.append('    '+row['field']+': '+row['rustType']+',')
        rendered.append('}')
    (HERE/'positive-positions.rs').write_text('\n'.join(rendered)+'\n')
    save('inventory-schema.json',rows);save('function-manifest.json',functions);save('closure-captures.json',captures)
    print(len(rows),'positive fields',len(functions),'compiler bodies')
if __name__=='__main__':main()
