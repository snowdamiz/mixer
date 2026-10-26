#!/usr/bin/env python3
"""Independent literal product packets and source-site inputs; not behavioral evidence."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent


def write(name,value):
    (HERE/name).write_text(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n')


def node(identifier,kind,properties=None,children=None):
    events={'button':['activate'],'textField':['textChange','submit'],'toggle':['valueChange']}.get(kind,[])
    return dict(id=identifier,kind=kind,properties=properties or {},children=children or [],actions=[dict(id=identifier+'-'+event,event=event) for event in events])


def root():
    return node('navigation','navigation',dict(title='Independent navigation'),[
        node('list','list',children=[
            node('section','section',dict(title='First section'),[
                node('body','text',dict(text='Independent body')),
                node('caption','text',dict(text='Independent caption',style='caption')),
                node('button','button',dict(label='Activate',role='normal')),
                node('field','textField',dict(label='Field',value='alpha')),
                node('toggle','toggle',dict(label='Toggle',value=False))]),
            node('horizontal','hStack',dict(alignment='center'),[
                node('left','text',dict(text='Left')),node('right','text',dict(text='Right',style='caption'))]),
            node('overlay','zStack',children=[node('behind','text',dict(text='Behind')),node('front','text',dict(text='Front',style='caption'))]),
            node('cancel','button',dict(label='Cancel',role='cancel')),
            node('second','section',dict(title='Second section'),[
                node('vertical','vStack',dict(alignment='leading'),[
                    node('above','text',dict(text='Above')),
                    node('last','text',dict(text='Last row'))]),
                node('destructive','button',dict(label='Delete',role='destructive')),
                node('trailing','text',dict(text='Trailing row'))])])])


def packet(revision,field='alpha',toggle=False,changed=False,reorder=False):
    tree=root();all_nodes=[]
    def walk(n):
        all_nodes.append(n)
        if n['id']=='field':n['properties']['value']=field
        if n['id']=='toggle':n['properties']['value']=toggle
        if changed and n['id']=='body':n['properties']['text']='A different body'
        for child in n['children']:walk(child)
    walk(tree)
    if reorder:tree['children'][0]['children'][0]['children'].reverse()
    return dict(schemaVersion=1,document=dict(schemaVersion=1,revision=revision,root=tree),identities=[dict(id=n['id'],generation=index+1) for index,n in enumerate(all_nodes)])


def main():
    for name,value in {'base':packet(1),'echo':packet(2),'empty':packet(2,field=''),'toggle':packet(2,toggle=True),'changed':packet(2,field='beta',changed=True),'reorder':packet(2,field='beta',changed=True,reorder=True)}.items():
        write('matrix-packet-'+name+'.json',value)
    mapping=json.loads((HERE/'source-call-index-2/baseline-mapping.json').read_text())
    assert mapping['mapped']==184 and not mapping['unresolved']
    all_calls=[json.loads(line) for line in (HERE/'source-call-index-2/02-index-sources.stdout').read_text().splitlines()]
    old_keys={(x['classes'],x['methods'],x['select']) for x in all_calls if '/preaccess/baseline/' in x['source']}
    added=[x for x in all_calls if '/candidate-4/source/' in x['source'] and x['classes']=='NativeAppearanceViewsV2/NativeField/<anonymous>' and x['select'].startswith('super.') and (x['classes'],x['methods'],x['select']) not in old_keys]
    assert len(added)==4 and {x['select'] for x in added}=={'super.beginBatchEdit','super.endBatchEdit','super.clearMetaKeyStates','super.closeConnection'}
    forward=[x for x in all_calls if '/candidate-4/source/' in x['source'] and x['classes']=='NativeAppearanceViewsV2/Group' and x['methods']=='onLayout(boolean,int,int,int,int)' and x['select']=='onLayout' and x['arguments']==6]
    assert len(forward)==1
    sites=[]
    for row in mapping['bindings']:
        sites.append(dict(id=row['id'],historical=True,current=row['current'],explicit_contract_move=row['explicit_contract_move']))
    for row in added+forward:
        sites.append(dict(id='introduced:'+row['classes']+':'+row['methods']+':'+row['select'],historical=False,current=row,explicit_contract_move=False))
    assert len(sites)==189 and len({row['id'] for row in sites})==189
    lines=[]
    for site in sites:
        call=site['current'];select=call['select']
        kind='constructor' if select.startswith('new ') else 'helper-forward' if site['current'] in forward else 'native-call'
        callee='<init>' if kind=='constructor' else select.rsplit('.',1)[-1]
        site.update(kind=kind,callee=callee)
        lines.append('\t'.join(map(str,[site['id'],Path(call['source']).name,call['line'],call['column'],callee,kind,call['classes'],call['methods'],select]))+'\n')
    (HERE/'matrix-sites.tsv').write_text(''.join(lines))
    write('selected-site-input-map.json',dict(schema=1,scope='Supplemental independent source identity; no behavior rows qualified',baseline=184,introduced=5,total=189,seven_case_rows_required=1323,sites=sites))
    write('matrix-input-hashes.json',{p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(HERE.glob('matrix-*')) if p.is_file() and p.name!='matrix-input-hashes.json'})
    print(json.dumps(dict(status='independent-product-packets-and189-source-inputs',product_tests=0)))


if __name__=='__main__':main()
