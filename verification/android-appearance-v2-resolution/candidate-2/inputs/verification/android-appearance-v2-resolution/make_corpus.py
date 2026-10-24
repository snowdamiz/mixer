#!/usr/bin/env python3
"""Independent concrete documents/environments; descriptors are exact canonical input.
No generated source, native device or authority fixture is used."""
from pathlib import Path
import base64, copy, itertools, json, sys
root=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(exist_ok=False)
b64=lambda b:base64.b64encode(b).decode()
encode=lambda x:(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode()
golden=(root/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json').read_bytes()
def node(id,kind,props=None,children=None):
    p=props or {};actions=[]
    if kind=='button':actions=[dict(id=id+'Action',event='activate')]
    if kind=='textField':actions=[dict(id=id+'Edit',event='textChange'),dict(id=id+'Submit',event='submit')]
    if kind=='toggle':actions=[dict(id=id+'Change',event='valueChange')]
    return dict(id=id,kind=kind,properties=p,children=children or [],actions=actions)
def text(id,style='body'):return node(id,'text',dict(text='Original '+id+' \" \\ é العربية 👩🏽‍💻 e\u0301',style=style,selectable=True,maxLines=100))
def base():
    stack=node('stack','vStack',{},[text('body'),text('caption','caption'),text('headline','headline'),text('title','title'),
        *[node(role,'button',dict(label=role,role=role)) for role in ['normal','destructive','cancel']],
        node('field','textField',dict(label='Placeholder',value='Input 👩🏽‍💻')),
        node('on','toggle',dict(label='On',value=True)),node('off','toggle',dict(label='Off',value=False)),
        node('disabled','vStack',dict(disabled=True),[node('disabledButton','button',dict(label='Disabled',role='destructive')),
            node('disabledField','textField',dict(label='P',value='V')),node('disabledToggle','toggle',dict(label='T',value=False)),text('disabledText')]),
        node('h','hStack',{},[text('h1'),text('h2','caption')]),node('z','zStack',dict(alignment='bottomTrailing'),[text('z1'),text('z2')]),
        node('rowSemantic','section',dict(title='Nested semantic'),[text('nested1'),text('nested2')])])
    listed=node('list','list',{},[node('hidden','section'),stack,text('directSecond'),
        node('headed','section',dict(title='Header'),[text('c'),text('d')]),node('titleOnly','section',dict(title='Title only')),
        node('hidden2','section',dict(title='')),text('e'),node('unheaded','section',{},[text('f')])])
    return node('nav','navigation',dict(title='Expanded original'),[node('root','zStack',{},[listed,
        node('outside','section',dict(title='Outside'),[text('outside1'),text('outside2')]),node('siblingList','list')])])
def env(**changes):
    e=dict(scheme='light',direction='leftToRight',profile='l',density=1024,width=25728,height=55936,top=0,leading=0,bottom=0,trailing=0,
        locale='en_US',bold=0,contrast=0,motion=0,generation='0');e.update(changes)
    return '|'.join(str(e[k]) if k!='locale' else b64(e[k].encode()) for k in ['scheme','direction','profile','density','width','height','top','leading','bottom','trailing','locale','bold','contrast','motion','generation'])
cases=[]
def add(name,doc=None,descriptor=golden,environment=None,platform='android'):
    cases.append([name,doc or base(),descriptor,environment or env(),platform])
profiles=['xs','s','m','l','xl','xxl','xxxl','a1','a2','a3','a4','a5']
for profile,scheme,direction in itertools.product(profiles,['light','dark'],['leftToRight','rightToLeft']):
    add(f'base-{profile}-{scheme}-{direction}',environment=env(profile=profile,scheme=scheme,direction=direction,motion=1,generation='18446744073709551615',locale='ar'))
custom=json.loads(golden);custom['id']='mixer.custom-alpha-v2'
theme=custom['theme'];theme['stacks']['defaultGap64']=777;theme['stacks']['bodyCaptionGap64']=17
for scheme in ['light','dark']:
    theme[scheme]['text']['body']='#12345678'
    theme[scheme]['button']['normal']['pressed']['background']='#9ABCDE7F'
    theme[scheme]['field']['focused']['selection']='#19283746'
    theme[scheme]['toggle']['off']['disabled']['label']='#33445566'
theme['groupedList']['topPadding64']=7;theme['groupedList']['bottomPadding64']=9;theme['groupedList']['headerToGroup64']=11
theme['groupedList']['groupToNextHeader64']=13;theme['groupedList']['groupWithoutHeaderGap64']=15
theme['button']['minimumHitWidth64']=100;theme['button']['labelInsets64']['leading']=53
theme['field']['insets64']['bottom']=77;theme['toggle']['labelGap64']=99;theme['navigation']['expandedInsets64']['leading']=101
for profile,scheme,direction in itertools.product(profiles,['light','dark'],['leftToRight','rightToLeft']):
    add(f'custom-{profile}-{scheme}-{direction}',descriptor=encode(custom),environment=env(profile=profile,scheme=scheme,direction=direction))
platform=dict(format=custom['format'],id='mixer.platform-v2',mode='platformSpecific',resources=[],iOS=json.loads(golden)['theme'],android=theme,reason='Explicit complete app theme')
for target,scheme in itertools.product(['iOS','android'],['light','dark']):add('platform-'+target+'-'+scheme,descriptor=encode(platform),environment=env(scheme=scheme),platform=target)
for alignment in ['top','center','bottom']:
    add('h-align-'+alignment,node('halign','hStack',dict(alignment=alignment),[text('child1'),text('child2')]))
for alignment in ['leading','center','trailing']:
    add('v-align-'+alignment,node('valign','vStack',dict(alignment=alignment),[text('child1'),text('child2','caption')]))
for alignment in ['center','leading','trailing','top','bottom','topLeading','topTrailing','bottomLeading','bottomTrailing']:
    add('z-align-'+alignment,node('zalign','zStack',dict(alignment=alignment),[text('child1'),text('child2')]))
for kind,spacing,count in itertools.product(['vStack','hStack'],[0,0.0078125,0.0234375,1.5,256],[0,1,4]):
    add('spacing-'+kind+'-'+str(spacing)+'-'+str(count),node('spacing',kind,dict(spacing=spacing),[text('child'+str(i),'caption' if i%2 else 'body') for i in range(count)]))
for baseline in ['firstTextBaseline','lastTextBaseline']:
    configuration=json.loads(golden);configuration['theme']['stacks']['hStackAlignment']=baseline
    add('default-baseline-'+baseline,node('defaultBaseline','hStack',{},[text('child1'),text('child2')]),descriptor=encode(configuration))
for index,children in enumerate([[],[node('empty','section')],[node('title','section',dict(title='Only title'))],[node('blank','section',dict(title=''))]]):
    add('list-empty-'+str(index),node('emptyList','list',{},children))
for title in [None,'','Header']:
    add('section-'+str(title),node('section','section',{} if title is None else dict(title=title),[text('a'),text('b')]))
    add('navigation-'+str(title),node('navigation','navigation',{} if title is None else dict(title=title),[text('a')]))
for name,changes in [('density-min',dict(density=128)),('density-max',dict(density=16384)),('density-under',dict(density=127)),('density-over',dict(density=16385)),
    ('viewport-zero',dict(width=0)),('viewport-max',dict(width=2147483647,height=2147483647,top=2147483647,leading=2147483647)),
    ('viewport-over',dict(width=2147483648)),('safe-exact',dict(width=10,height=10,top=6,bottom=4,leading=3,trailing=7)),
    ('safe-over',dict(width=10,leading=6,trailing=5)),('safe-overflow',dict(width=2147483647,leading=4294967295,trailing=4294967295)),
    ('locale-128',dict(locale='é'*64)),('locale-129',dict(locale='x'*129)),('locale-emoji',dict(locale='😀'*32)),
    ('locale-empty',dict(locale='')),('locale-null',dict(locale='a\0b')),('locale-85',dict(locale='a\x85b')),('locale-format',dict(locale='a\u200db')),
    ('bold',dict(bold=1)),('contrast',dict(contrast=1)),('motion',dict(motion=1))]:
    add('environment-'+name,node('env','text',dict(text='Environment')),environment=env(**changes))
# This is a resolver restriction distinct from the V1 packet profile.
add('nonroot-navigation',node('root','vStack',{},[node('nonroot','navigation',dict(title='Title'),[text('child')])]))
# Whole configuration validation must include the unselected platform theme.
invalid=copy.deepcopy(platform);invalid['iOS']['typography']['profiles']['l']['body']['size64']=1
add('unselected-invalid',descriptor=encode(invalid),platform='android')
# Reparent and replace through one actual reconciler, exported packet identities
# are reused by Java; test-only generation fabrication is unnecessary.
for index in range(3):
    moving=text('moving') if index<2 else node('moving','button',dict(label='Replaced'))
    add('identity-'+str(index),node('identityRoot','vStack',{},[
        node('left','vStack',{},[moving] if index==0 else []),node('right','vStack',{},[] if index==0 else [moving])]))
lines=[]
for revision,(name,doc,descriptor,environment,target) in enumerate(cases,1):
    document=dict(schemaVersion=1,revision=revision,root=doc)
    lines.append('\t'.join([name,b64(encode(document)),b64(descriptor),environment,target]))
(out/'cases.tsv').write_text('\n'.join(lines)+'\n')
(out/'manifest.json').write_text(json.dumps(dict(cases=len(cases),profiles=12,schemes=2,directions=2,stateCombinationsPerNode=4,scope='Independent data combinations and actual Swift snapshot/packet identities only'),indent=2)+'\n')
print('PASS generated',len(cases),'independent data cases')
