#!/usr/bin/env python3
"""Review-owned discriminators. No producer generator or resolver imports."""
import base64, copy, json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
BASE = json.loads((ROOT/'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json').read_text())
CASES = []
def raw(v): return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
def b64(v): return base64.b64encode(v).decode()
def n(kind, id, props=None, children=None):
    p = {'text':{'text':'Arabic العربية / emoji 🧪'}, 'button':{'label':'Run'},
         'textField':{'label':'Input', 'value':'Value'}, 'toggle':{'label':'Checked','value':False}}.get(kind,{}) | (props or {})
    return {'id':id,'kind':kind,'properties':p,'children':children or [],
            'actions':[{'id':id+'-'+e,'event':e} for e in {'button':['activate'],'textField':['textChange','submit'],'toggle':['valueChange']}.get(kind,[])]}
def doc(root, revision=18446744073709551615): return {'schemaVersion':1,'revision':revision,'root':root}
def packet(d):
    identities=[]
    def walk(v):
        identities.append({'id':v['id'],'generation':len(identities)+1})
        for c in v['children']:walk(c)
    walk(d['root'])
    return {'schemaVersion':1,'document':d,'identities':identities}
def tree():
    c = [n('text','role-'+r,{'style':r,'selectable':i%2==1,'maxLines':[1,2,99,100][i]}) for i,r in enumerate(['body','headline','title','caption'])]
    c += [n('text','default-body'), *[n('button','role-'+r,{'role':r}) for r in ['normal','cancel','destructive']],n('button','default-button')]
    c += [n('textField','enabled-field'), n('toggle','off'), n('toggle','on',{'value':True})]
    c += [n('vStack','v-'+a,{'alignment':a,'spacing':0 if i==0 else 3.25}) for i,a in enumerate(['leading','center','trailing'])]
    c += [n('hStack','h-'+a,{'alignment':a,'spacing':1/128}) for a in ['top','center','bottom']]
    c += [n('zStack','z-'+a,{'alignment':a}) for a in ['center','leading','trailing','top','bottom','topLeading','topTrailing','bottomLeading','bottomTrailing']]
    c += [n('vStack','v-default'),n('hStack','h-default'),n('zStack','z-default')]
    c += [n('list','list',children=[n('section','empty-header',{'title':''},[n('text','row')]),n('section','no-header')])]
    c += [n('navigation','title-nav',{'title':'Title'},[n('text','nav-child')]), n('navigation','no-title-nav',children=[n('vStack','empty-content')])]
    c += [n('vStack','disabled-parent',{'disabled':True},[n('hStack','disabled-mid',{'disabled':False},[n('button','disabled-button',{'disabled':False,'role':'destructive'}),n('textField','disabled-field'),n('toggle','disabled-on',{'value':True})])])]
    return doc(n('vStack','root',children=c))
def config(seed):
    c = copy.deepcopy(BASE); c['id']='review-'+str(seed); t=c['theme']
    for si, scheme in enumerate(['light','dark']):
        for i,k in enumerate(sorted(t[scheme])):
            t[scheme][k] = '#'+''.join(f'{v:02X}' for v in [(seed*7+i*13+si*59)%256,(seed*31+i*17+si*61)%256,(seed*19+i*43+si*67)%256,[0,1,127,128,254,255][(i+seed+si)%6]])
    for i,r in enumerate(['body','headline','title','caption']):
        t['typography'][r]={'size64':65+128*i+seed*2,'minimumLineBox64':1001+257*i+seed*2,'weight':400+100*i}
    counter=1
    def numeric(v):
        nonlocal counter
        for k in sorted(v):
            if isinstance(v[k],dict):numeric(v[k])
            elif isinstance(v[k],int):v[k]=counter*17+seed;counter+=1
    numeric(t['controls']);numeric(t['layout'])
    # Distinct dimensions while satisfying the descriptor's envelope invariants.
    t['controls']['toggle'].update(inset64=19+seed,thumb64=101+seed,trackHeight64=503+seed*3,trackWidth64=911+seed*3,minimumRow64=1009+seed*3)
    t['layout'].update(hStackAlignment=['firstTextBaseline','lastTextBaseline','bottom'][seed%3],vStackAlignment=['trailing','leading','center'][seed%3],zStackAlignment=['bottomTrailing','topLeading','center'][seed%3])
    t['layout']['navigation']['titleAlignment']=['trailing','center','leading'][seed%3]
    return c
def add(id, d=None,c=None,scale=1024,density=1024,scheme='light',direction='leftToRight',platform='android',expected='accepted',boundary='',descriptor=None,history=None):
    d=tree() if d is None else d;c=BASE if c is None else c
    CASES.append({'id':id,'document':b64(raw(d)),'packet':b64(raw(packet(d))),
       'descriptor':b64(raw(c)+b'\n' if descriptor is None else descriptor),'history':[b64(raw(h)) for h in history or []],
       'environment':{'scheme':scheme,'direction':direction,'textScale1024':scale,'density1024':density},'platform':platform,'expected':expected,'boundary':boundary})
for seed in [0,1,2,11,23]:
    for scheme in ['light','dark']:
        for direction in ['leftToRight','rightToLeft']:
            for platform in ['iOS','android']:
                add(f'all-{seed}-{scheme}-{direction}-{platform}',c=config(seed),scheme=scheme,direction=direction,platform=platform,scale=[512,1023,1024,1025,4096][seed%5],density=[128,129,1023,1024,16384][seed%5])
# Half-up odd metrics and bounds, including values just either side of ties.
for scale in [512,513,767,768,769,1023,1024,1025,1535,1536,1537,2047,2048,2049,3071,3072,3073,4095,4096]:
    add('scale-'+str(scale),c=config(1),scale=scale)
for density in [128,129,1023,1024,1025,16383,16384]:add('density-'+str(density),c=config(2),density=density)
for v in [0,-0.0,math.nextafter(1/128,0),1/128,math.nextafter(1/128,1),math.nextafter(3/128,0),3/128,math.nextafter(3/128,1),0.1,127.9921875,255.9921875,256]:
    add('spacing-'+repr(v),doc(n('hStack','spacing',{'spacing':v})),config(2))
# Extrema admit scaling beyond individual metric inputs and aggregate beyond 262144.
for scale in [512,1023,1024,1025,4096]:
    c=config(1)
    for r in ['body','headline','title','caption']:c['theme']['typography'][r].update(size64=16384,minimumLineBox64=65536)
    for area in [c['theme']['controls']['button']['labelInsets64'],c['theme']['controls']['field']['insets64'],c['theme']['layout']['navigation']['titleInsets64']]:
        area.update(top=65536,leading=1,bottom=65536,trailing=65535)
    add('aggregate-'+str(scale),c=c,scale=scale)
specific={'format':BASE['format'],'id':'review-specific','mode':'platformSpecific','resources':[],'iOS':config(1)['theme'],'android':config(23)['theme'],'reason':'Explicit review alternative'}
for platform in ['iOS','android']:
    for scheme in ['light','dark']:add('specific-'+platform+'-'+scheme,c=specific,platform=platform,scheme=scheme)
res=config(11)
res['resources']=[{'id':'f'+str(w),'kind':'fontSFNT','path':f'Fonts/F{w}.ttf','sha256':f'{w:064x}','bytes':w+17,'provenance':'Review metadata; absent fixture bytes','scale':1,'locale':'und','direction':'neutral'} for w in [400,500,600,700]]
res['resources'] += [{'id':'icon','kind':'iconPNG','path':'Icons/right.png','sha256':'ab'*32,'bytes':1234,'provenance':'Review icon metadata','scale':4,'locale':'ar-SA','direction':'rightToLeft'}]
res['theme']['typography']['font']={'kind':'bundled','fallback':'none','faces':[{'resourceID':'f'+str(w),'postScriptName':'Review-'+str(w),'weight':w,'style':'normal'} for w in [400,500,600,700]]}
add('resources-all',c=res)
history=doc(n('vStack','root',children=[n('text','survive'),n('text','replace'),n('button','remove')]),1)
current=doc(n('vStack','root',children=[n('button','replace'),n('toggle','insert'),n('text','survive')]),18446744073709551615)
add('identity-reordered-kind-replacement',current,config(2),history=[history])
for rev in [0,1,9007199254740991,9007199254740992,9223372036854775807,9223372036854775808,18446744073709551615]:
    add('revision-'+str(rev),doc(n('text','revision'),rev),config(1))
for rev in [-1,1.5,18446744073709551616,'1',None]:
    add('invalid-revision-'+str(rev),doc(n('text','revision'),rev),expected='rejected')
for alignment in ['firstTextBaseline','lastTextBaseline']:
    add('known-explicit-'+alignment,doc(n('hStack','baseline',{'alignment':alignment})),boundary='packet-baseline-rejected')
add('known-nested-list',doc(n('list','outer',children=[n('section','section',children=[n('list','inner')])])),boundary='packet-baseline-rejected')
# Reject closed schema/capability failures and all unseen branches/resources.
mutations=[('extra-root',lambda c:c.update(extra=1)),('format',lambda c:c.update(format='future')),('mode',lambda c:c.update(mode='implicit')),
 ('id',lambda c:c.update(id='bad/id')),('recipe',lambda c:c['theme'].update(recipe='future')),
 ('unselected-dark',lambda c:c['theme']['dark'].update(accent='#abcdefFF')),('extra-palette',lambda c:c['theme']['light'].update(extra='#00000000')),
 ('short-color',lambda c:c['theme']['light'].update(canvas='#FFFFFFFFF')),('low-size',lambda c:c['theme']['typography']['body'].update(size64=63)),
 ('high-size',lambda c:c['theme']['typography']['body'].update(size64=16385)),('line-too-small',lambda c:c['theme']['typography']['body'].update(minimumLineBox64=64)),
 ('weight',lambda c:c['theme']['typography']['headline'].update(weight=450)),('metric-overflow',lambda c:c['theme']['layout'].update(stackGap64=65537)),
 ('negative-metric',lambda c:c['theme']['controls']['field'].update(border64=-1)),('fraction-metric',lambda c:c['theme']['controls'].update(focusWidth64=0.5)),
 ('pressed-overflow',lambda c:c['theme']['controls'].update(pressedOpacityPermille=1001)),('selection-overflow',lambda c:c['theme']['controls'].update(selectionOpacityPermille=1001)),
 ('toggle-envelope',lambda c:c['theme']['controls']['toggle'].update(thumb64=65536)),('toggle-row',lambda c:c['theme']['controls']['toggle'].update(minimumRow64=0)),
 ('alignment',lambda c:c['theme']['layout'].update(zStackAlignment='left')),('unknown-font',lambda c:c['theme']['typography'].update(font={'kind':'future'}))]
for id,fn in mutations:
    c=config(1);fn(c);add('bad-config-'+id,c=c,expected='rejected')
for branch in ['iOS','android']:
    c=copy.deepcopy(specific);c[branch]['dark']['canvas']='#abcd1234';add('bad-unselected-'+branch,c=c,platform='android' if branch=='iOS' else 'iOS',expected='rejected')
for id,fn in [
 ('missing-face',lambda c:c['theme']['typography']['font']['faces'].pop()),
 ('missing-resource',lambda c:c['theme']['typography']['font']['faces'][0].update(resourceID='missing')),
 ('wrong-resource-kind',lambda c:c['resources'][0].update(kind='iconPNG')),
 ('duplicate-face',lambda c:c['theme']['typography']['font']['faces'].append(copy.deepcopy(c['theme']['typography']['font']['faces'][0]))),
 ('duplicate-id',lambda c:c['resources'][1].update(id=c['resources'][0]['id'])),
 ('case-path-alias',lambda c:c['resources'][1].update(path=c['resources'][0]['path'].lower())),
 ('dot-path',lambda c:c['resources'][0].update(path='Fonts/../font.ttf')),
 ('absolute-path',lambda c:c['resources'][0].update(path='/font.ttf')),
 ('uppercase-digest',lambda c:c['resources'][0].update(sha256='AB'*32)),
 ('zero-resource',lambda c:c['resources'][0].update(bytes=0)),
 ('high-resource',lambda c:c['resources'][0].update(bytes=4194305)),
 ('font-scale',lambda c:c['resources'][0].update(scale=2)),
 ('font-locale',lambda c:c['resources'][0].update(locale='en')),
 ('font-direction',lambda c:c['resources'][0].update(direction='leftToRight')),
 ('empty-locale-part',lambda c:c['resources'][-1].update(locale='en--US')),
 ('invalid-face-style',lambda c:c['theme']['typography']['font']['faces'][0].update(style='oblique'))]:
    c=copy.deepcopy(res);fn(c);add('bad-resources-'+id,c=c,expected='rejected')
canonical=raw(config(1))+b'\n'
for id,v in [('empty',b''),('no-newline',canonical[:-1]),('double-newline',canonical+b'\n'),('leading-space',b' '+canonical),('duplicate',canonical.replace(b'"format":',b'"format":"duplicate","format":',1)),('unicode-escape',canonical.replace(b'review-1',b'review-\\u0031')),('non-ascii',canonical.replace(b'review-1','review-é'.encode())),('beyond-bound',b' '*65537),('truncated',canonical[:-15]),('number-exponent',canonical.replace(b'"size64":67',b'"size64":67e0'))]:
    add('bad-encoding-'+id,descriptor=v,expected='rejected')
for scale in [-2147483648,-1,0,511,4097,65535,65536,2147483647]:add('bad-scale-'+str(scale),scale=scale,expected='rejected')
for density in [-2147483648,-1,0,127,16385,65535,65536,2147483647]:add('bad-density-'+str(density),density=density,expected='rejected')
for key,value in [('scheme','system'),('direction','RTL'),('platform','host')]:add('bad-env-'+key,**{key:value},expected='rejected')
for id,kind,p in [('bad-style','text',{'style':'future'}),('bad-selectable','text',{'selectable':1}),('bad-lines-low','text',{'maxLines':0}),('bad-lines-high','text',{'maxLines':101}),('bad-lines-fraction','text',{'maxLines':1.5}),('bad-role','button',{'role':'primary'}),('bad-value','toggle',{'value':1}),('bad-spacing-low','vStack',{'spacing':-0.001}),('bad-spacing-high','hStack',{'spacing':256.001}),('bad-disabled','text',{'disabled':0}),('unknown-node-property','text',{'unknown':True})]:
    add(id,doc(n(kind,id,p)),expected='rejected')
for depth in [64,65]:
    root=n('text','leaf')
    for i in range(depth-1):root=n('vStack','depth-'+str(i),children=[root])
    add('depth-'+str(depth),doc(root),expected='accepted' if depth==64 else 'rejected')
for count in [1000,1001]:add('children-'+str(count),doc(n('vStack','wide',children=[n('text','child-'+str(i)) for i in range(count)])),expected='accepted' if count==1000 else 'rejected')
Path(sys.argv[1]).write_bytes(b''.join(raw(c)+b'\n' for c in CASES))
print(json.dumps({'cases':len(CASES),'expected_accepted':sum(c['expected']=='accepted' for c in CASES),'expected_rejected':sum(c['expected']=='rejected' for c in CASES),'known_packet_boundary':sum(bool(c['boundary']) for c in CASES)},sort_keys=True))
