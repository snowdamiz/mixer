#!/usr/bin/env python3
"""Bind exact selected and retained actual frames to unmodified compiled classes/source/invocations."""
from pathlib import Path
import hashlib
import json
import re
HERE=Path(__file__).resolve().parent
REFERENCE=HERE/'matrix-execution-1'

def record(path):
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def main():
    tables={}
    for path in sorted(REFERENCE.glob('01-bytecode-*.stdout')):
        command=json.loads(path.with_suffix('.command.json').read_text());assert command['exit_code']==0
        current_class=None;current=None;header=''
        for line in path.read_text().splitlines():
            match=re.match(r'^.*?\bclass (dev\.mixer\.android\.[^ <]+)',line)
            if match:current_class=match[1];tables[current_class]=dict(output=str(path.relative_to(HERE)),methods={});current=None
            if line.startswith('  ') and not line.startswith('    ') and '(' in line and line.endswith(';'):header=line.strip();current=None
            if current_class and line.strip().startswith('descriptor: ('):
                descriptor=line.strip().split(': ',1)[1];qualified=header.split('(',1)[0].split()[-1];method='<init>' if qualified==current_class else qualified.rsplit('.',1)[-1]
                current=dict(instructions={},lines=[]);tables[current_class]['methods'][(method,descriptor)]=current
            if current is not None:
                instruction=re.fullmatch(r'\s+(\d+):\s+([a-z][a-z0-9_]*.*)',line)
                mapping=re.fullmatch(r'\s+line (\d+): (\d+)',line)
                if instruction:current['instructions'][int(instruction[1])]=instruction[2]
                if mapping:current['lines'].append((int(mapping[2]),int(mapping[1])))
    classes=json.loads((REFERENCE/'compiled-class-hashes.json').read_text());sources=json.loads((REFERENCE/'01-compile.command.json').read_text())['source_map']
    def bind(name,method,descriptor,bci,line=None):
        table=tables[name];body=table['methods'][(method,descriptor)];instruction=body['instructions'][bci]
        mapped=max((pair for pair in body['lines'] if pair[0]<=bci),key=lambda pair:pair[0])[1]
        if line is not None:assert mapped==line,(name,method,bci,line,mapped)
        source='candidate-5/source/native/android/app/src/dev/mixer/android/'+name.rsplit('.',1)[1].split('$',1)[0]+'.java';assert record(HERE/source)==sources[source]
        return dict(class_name=name,method=method,descriptor=descriptor,bci=bci,line=mapped,instruction=instruction,source=source,source_hash=sources[source],compiled_class=classes[name.replace('.','/')+'.class'],javap=table['output'])
    selected=[];site_map={row['id']:row for row in json.loads((HERE/'selected-site-input-map.json').read_text())['sites']}
    for raw in (HERE/'matrix-targets.tsv').read_text().splitlines():
        identifier,scenario,leaf,name,method,descriptor,bci=raw.split('\t');site=site_map[identifier]
        bound=bind(name,method,descriptor,int(bci),site['current']['line'])
        assert bound['instruction'].startswith(('invokevirtual','invokespecial','invokestatic','invokeinterface'))
        if site['kind']=='constructor':assert '"<init>"' in bound['instruction']
        else:assert site['callee']+':' in bound['instruction'],(identifier,bound['instruction'])
        selected.append(dict(id=identifier,scenario=scenario,leaf=leaf,**bound))
    unique={};rows=0
    for number in [2]:
        out=HERE/f'matrix-execution-{number}';compiled=json.loads((out/'compiled-class-hashes.json').read_text())
        for path in sorted(out.glob('02-*.stdout')):
            for raw in path.read_text().splitlines():
                if not raw.startswith('{'):continue
                row=json.loads(raw)
                if 'variant' not in row:continue
                rows+=1
                for frame in row['orderedTrace']['frames']:
                    head,position=frame.rsplit('@',1);name_method,descriptor_tail=head.split('(',1);name,method=name_method.rsplit('#',1);bci,line=map(int,position.split(':'))
                    bound=bind(name,method,'('+descriptor_tail,bci,line);cp=name.replace('.','/')+'.class';assert compiled[cp]==classes[cp]
                    unique.setdefault(frame,dict(frame=frame,**bound))
        for name in tables:
            cp=name.replace('.','/')+'.class'
            if cp in compiled:assert compiled[cp]==classes[cp],(number,cp)
    assert rows==1323 and len(selected)==189
    result=dict(scope='Complete exact identity binding; behavior/source-authority classification separate',selected_sites=189,baseline_sites=184,introduced_sites=5,executed_rows_bound=rows,unique_postcallback_frames=len(unique),selected=selected,postcallback_frames=list(unique.values()),reference_class_count=len(tables))
    (HERE/'matrix-frame-bindings.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['selected','postcallback_frames']}))

if __name__=='__main__':main()
