#!/usr/bin/env python3
"""Independent descriptor/document/environment corpus, with no resolver constants table."""
from pathlib import Path
import base64, copy, json, math, random, sys
ROOT=Path(__file__).resolve().parents[2]
BASE=json.loads((ROOT/'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json').read_text())
R=random.Random(0x4d49584552)
def encoded(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def b64(value): return base64.b64encode(value).decode()
def canonical(value): return encoded(value)+b'\n'
def node(kind,id,properties=None,children=None):
    p={} if properties is None else properties
    defaults={'text':{'text':''},'button':{'label':''},'textField':{'label':'','value':''},'toggle':{'label':'','value':False}}
    p=defaults.get(kind,{})|p
    events={'button':['activate'],'textField':['textChange','submit'],'toggle':['valueChange']}.get(kind,[])
    return {'id':id,'kind':kind,'properties':p,'children':children or [],'actions':[{'id':'action-'+id,'event':e} for e in events]}
def doc(root,revision=1): return {'schemaVersion':1,'revision':revision,'root':root}
def packet(document):
    identities=[]
    def visit(n):
        identities.append({'id':n['id'],'generation':len(identities)+1})
        for c in n['children']:visit(c)
    visit(document['root'])
    return {'schemaVersion':1,'document':document,'identities':identities}
def full():
    children=[]
    for role in [None,'body','headline','title','caption']:
        for selectable,lines in [(False,None),(True,1),(True,100)]:
            p={'text':'Arabic العربية / Greek Ελληνικά / 👩🏽‍💻','selectable':selectable}
            if role:p['style']=role
            if lines:p['maxLines']=lines
            children.append(node('text',f't-{role}-{selectable}-{lines}',p))
    for role in [None,'normal','cancel','destructive']:
        children.append(node('button',f'button-{role}',{} if role is None else {'role':role}))
    children += [node('textField','field'),node('toggle','off'),node('toggle','on',{'value':True})]
    for a in ['leading','center','trailing']:children.append(node('vStack','v-'+a,{'alignment':a,'spacing':0}))
    for a in ['top','center','bottom']:children.append(node('hStack','h-'+a,{'alignment':a,'spacing':0.0078125}))
    for a in ['center','leading','trailing','top','bottom','topLeading','topTrailing','bottomLeading','bottomTrailing']:
        children.append(node('zStack','z-'+a,{'alignment':a}))
    children += [node('hStack','h-default'),node('vStack','v-default'),node('zStack','z-default')]
    children += [node('list','list',children=[node('section','section-titled',{'title':''},[node('text','list-row')]),node('section','section-empty')])]
    children += [node('navigation','navigation-title',{'title':'Title'},[node('vStack','nav-child')]),node('navigation','navigation-no-title',children=[node('text','nav-text')])]
    children += [node('vStack','disabled-parent',{'disabled':True},[node('button','disabled-button',{'disabled':False}),node('textField','disabled-field'),node('toggle','disabled-toggle',{'value':True})])]
    children += [node('text','Unicode-العربية-🧪')]
    return doc(node('vStack','root',children=children),18446744073709551615)
def distinct_config(seed):
    c=copy.deepcopy(BASE);c['id']='independent-'+str(seed)
    def theme(t):
        for scheme in ['light','dark']:
            for i,key in enumerate(t[scheme]):
                # Distinct all RGBA channels, including zero/partial/full alpha.
                t[scheme][key]='#'+''.join(f'{(seed*37+i*29+j*67)%256:02X}' for j in range(4))
        for role in ['body','headline','title','caption']:
            size=R.randint(64,16384);t['typography'][role]={'size64':size,'minimumLineBox64':R.randint(size,65536),'weight':R.choice([400,500,600,700])}
        def metrics(v):
            for key,value in v.items():
                if isinstance(value,dict):metrics(value)
                elif isinstance(value,int):v[key]=R.randint(0,1000 if key.endswith('Permille') else 65536)
        metrics(t['controls']);metrics(t['layout'])
        toggle=t['controls']['toggle'];toggle.update(trackWidth64=65536,trackHeight64=65536,thumb64=0,inset64=0,minimumRow64=65536)
        t['layout']['hStackAlignment']=R.choice(['top','center','bottom','firstTextBaseline','lastTextBaseline'])
        t['layout']['vStackAlignment']=R.choice(['leading','center','trailing'])
        t['layout']['zStackAlignment']=R.choice(['center','topLeading','bottomTrailing'])
    theme(c['theme']);return c
CASES=[]
def add(name,document=None,config=None,scale=1024,density=1024,scheme='light',direction='leftToRight',platform='android',history=None,boundary='',descriptor=None):
    d=full() if document is None else document
    c=BASE if config is None else config
    CASES.append({'id':name,'descriptor':b64(canonical(c) if descriptor is None else descriptor),'document':b64(encoded(d)),'packet':b64(encoded(packet(d))),
        'environment':{'scheme':scheme,'direction':direction,'textScale1024':scale,'density1024':density},'platform':platform,
        'history':[b64(encoded(h)) for h in history or []],'boundary':boundary})
# Every normalized text scale is tested with all four text roles, independent odd
# line/size metrics and fractional tie values, not just common accessibility scales.
odd=distinct_config(17)
roles=doc(node('vStack','scales',children=[node('text',r,{'style':r}) for r in ['body','headline','title','caption']]))
for scale in range(512,4097):add(f'all-scale-{scale}',roles,odd,scale=scale,density=[128,1024,16384][scale%3],direction=['leftToRight','rightToLeft'][scale%2])
for seed in range(32):
    c=distinct_config(seed)
    for scheme in ['light','dark']:
        for direction in ['leftToRight','rightToLeft']:
            for platform in ['iOS','android']:
                add(f'all-kinds-{seed}-{scheme}-{direction}-{platform}',config=c,scale=[512,1024,1434,2048,4096][seed%5],density=[128,1024,16384][seed%3],scheme=scheme,direction=direction,platform=platform)
for alignment in ['firstTextBaseline','lastTextBaseline']:
    c=copy.deepcopy(BASE);c['theme']['layout']['hStackAlignment']=alignment
    add('descriptor-default-'+alignment,doc(node('hStack','baseline-default')),c)
    add('explicit-packet-'+alignment,doc(node('hStack','baseline',{'alignment':alignment})),boundary='packet-baseline-rejected')
# Existing native parser intentionally rejects nested scrolling lists; resolver
# alone does not widen that native-admission boundary.
add('nested-list-packet-boundary',doc(node('list','outer',children=[node('list','inner')])),boundary='packet-baseline-rejected')
for value in [0,math.nextafter(1/128,0),1/128,math.nextafter(1/128,1),0.1,1.5,255.9921875,256]:
    add('spacing-'+repr(value),doc(node('hStack','spacing',{'spacing':value})))
for invalid in [-1,-0.00001,256.0001]:add('invalid-spacing-'+str(invalid),doc(node('vStack','spacing',{'spacing':invalid})))
for kind in ['vStack','hStack','zStack','list','section']:
    add('empty-'+kind,doc(node(kind,'empty')))
    add('empty-title-'+kind,doc(node(kind,'empty',{'title':''})) if kind=='section' else doc(node(kind,'empty')))
for limit in [64,65]:
    n=node('text','deep-leaf')
    for i in range(limit-1):n=node('vStack','depth-'+str(i),children=[n])
    add('depth-'+str(limit),doc(n))
for limit in [1000,1001]:add('children-'+str(limit),doc(node('vStack','wide',children=[node('text','c'+str(i)) for i in range(limit)])))
for limit in [4096,4097]:
    remaining=limit-1; groups=[];counter=0
    while remaining:
        if remaining==1:groups.append(node('text','last'));break
        amount=min(999,remaining-1); group=node('vStack','group'+str(counter),children=[node('text',f'n{counter}-{i}') for i in range(amount)])
        groups.append(group);remaining-=amount+1;counter+=1
    add('nodes-'+str(limit),doc(node('vStack','many',children=groups)))
for length in [16384,16385]:add('string-'+str(length),doc(node('text','string',{'text':'a'*length})))
# Identity retention under reorder, new insertion and same-ID kind replacement.
history=doc(node('vStack','root',children=[node('text','survivor'),node('text','replaced'),node('text','removed')]))
current=doc(node('vStack','root',children=[node('button','replaced'),node('text','inserted'),node('text','survivor')]),2)
add('retained-reordered-replaced-identities',current,history=[history])
# Aggregate floors must remain UInt32 sums above individual scaled metric bounds.
maximal=copy.deepcopy(BASE)
for role in ['body','headline','title','caption']:maximal['theme']['typography'][role].update(size64=16384,minimumLineBox64=65536)
for area in [maximal['theme']['controls']['button']['labelInsets64'],maximal['theme']['controls']['field']['insets64'],maximal['theme']['layout']['navigation']['titleInsets64']]:
    for k in area:area[k]=65536
add('maximum-aggregate-393216',config=maximal,scale=4096)
minimal=copy.deepcopy(BASE)
def zero(v):
    for k,x in v.items():
        if isinstance(x,dict):zero(x)
        elif isinstance(x,int):v[k]=0
zero(minimal['theme']['layout']);zero(minimal['theme']['controls'])
add('zero-layout-control-metrics',config=minimal,scale=512)
# Distinct iOS/Android themes and explicit reason exercise both selection branches.
specific=copy.deepcopy(BASE);specific.update(mode='platformSpecific',iOS=distinct_config(100)['theme'],android=distinct_config(101)['theme'],reason='Reviewed explicit alternative');del specific['theme']
for platform in ['iOS','android']:
    for scheme in ['light','dark']:add('platform-specific-'+platform+'-'+scheme,config=specific,platform=platform,scheme=scheme)
# Bounded data references deliberately name nonexistent bytes. Pure data resolution
# is allowed; native resource capture must fail separately before presentation.
resources=copy.deepcopy(BASE);resources['resources']=[{'id':'f'+str(w),'kind':'fontSFNT','path':'Fonts/f'+str(w)+'.ttf','sha256':f'{w:064x}','bytes':4194304,'provenance':'Independent metadata fixture','scale':1,'locale':'und','direction':'neutral'} for w in [400,500,600,700]]
resources['theme']['typography']['font']={'kind':'bundled','faces':[{'resourceID':'f'+str(w),'postScriptName':'Fixture-'+str(w),'weight':w,'style':'normal'} for w in [400,500,600,700]],'fallback':'systemSans'}
add('font-resource-reference-retention',config=resources)
# Complete configuration, including unselected platform/palette, must be admitted.
mutations=[('unknown-root',lambda c:c.update(extra=0)),('missing-id',lambda c:c.pop('id')),('unsupported-recipe',lambda c:c['theme'].update(recipe='future')),
('bad-opacity',lambda c:c['theme']['controls'].update(pressedOpacityPermille=1001)),('bad-color',lambda c:c['theme']['dark'].update(canvas='#abcdef00')),
('bad-unselected-theme',lambda c:c['android']['controls']['field'].update(border64=65537)),('missing-resource',lambda c:c['theme']['typography'].update(font={'kind':'bundled','faces':[{'resourceID':'none','postScriptName':'No','weight':400,'style':'normal'}],'fallback':'none'}))]
for name,mutate in mutations:
    c=copy.deepcopy(specific if name=='bad-unselected-theme' else BASE);mutate(c);add(name,config=c,platform='iOS')
for name,raw in [('descriptor-duplicate',canonical(BASE).replace(b'"format":',b'"id":"duplicate","format":',1)),('descriptor-no-newline',encoded(BASE)),('descriptor-empty',b''),('descriptor-too-large',b' '*65537)]:add(name,descriptor=raw)
for scale in [-1,0,511,4097,65536]:add('invalid-scale-'+str(scale),scale=scale)
for density in [-1,0,127,16385,65536]:add('invalid-density-'+str(density),density=density)
add('invalid-scheme',scheme='automatic');add('invalid-direction',direction='automatic');add('invalid-platform',platform='other')
Path(sys.argv[1]).write_bytes(b''.join(encoded(c)+b'\n' for c in CASES))
print('independent generated cases='+str(len(CASES)))
