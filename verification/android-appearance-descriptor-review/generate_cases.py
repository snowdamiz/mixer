#!/usr/bin/env python3
"""Independent concrete byte cases. No production/design validator used as oracle."""
import base64, copy, gzip, json, random, sys
from pathlib import Path
root = Path(sys.argv[1]); out = Path(sys.argv[2])
base = json.loads((root/'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json').read_bytes())
cases=[]
def canonical(v): return (json.dumps(v, sort_keys=True, ensure_ascii=True, separators=(',', ':'))+'\n').encode('ascii')
def raw(name, data, accepted=False): cases.append({'name':name,'accepted':accepted,'base64':base64.b64encode(data).decode('ascii')})
def add(name,v,accepted=False): raw(name,canonical(v),accepted)
def clone(v): return copy.deepcopy(v)
def resource(i=0, **kw):
    r=dict(id=f'R{i}', kind='iconPNG',path=f'Icons/I{i}.png',sha256='0123456789abcdef'*4,bytes=1,provenance='Independent metadata',scale=1,locale='und',direction='neutral');r.update(kw);return r
def changed(v,path,what):
    v=clone(v)
    if not path:return what
    at=v
    for p in path[:-1]:at=at[p]
    at[path[-1]]=what
    return v
def walk(v,p=()):
    yield p,v
    if isinstance(v,dict):
        for k,x in v.items():yield from walk(x,p+(k,))
    if isinstance(v,list):
        for i,x in enumerate(v):yield from walk(x,p+(i,))
add('exact-default',base,True)
# Distinct complete theme catalogs and explicit quote/backslash canonical strings.
fonted=clone(base);fonted['resources']=[resource(0,kind='fontSFNT',path='Fonts/Owned.ttf')]
fonted['theme']['typography']['font']={'kind':'bundled','fallback':'systemSans','faces':[dict(resourceID='R0',postScriptName=f'Owned-{w}-{style}',weight=w,style=style) for w in [400,500,600,700] for style in ['normal','italic']]}
for role,w in zip(['body','headline','title','caption'],[400,500,600,700]):fonted['theme']['typography'][role]['weight']=w
add('eight-distinct-font-faces',fonted,True)
platform=dict(format=base['format'],id='platform-X',mode='platformSpecific',reason='"'+''.join(map(chr,range(32,127)))+'\\',resources=clone(fonted['resources']),iOS=clone(fonted['theme']),android=clone(base['theme']))
platform['android']['light']['canvas']='#01234567';platform['android']['layout']['hStackAlignment']='lastTextBaseline';add('distinct-platform-values-printable-reason',platform,True)
# Broad accepted ASCII paths/locales and catalog extremes.
for path in ['A','A.','A..','A./B','A..B/C_D-E','a/b/C','A'*256]:
    b=clone(base);b['resources']=[resource(path=path)];add('valid-path-'+str(len(cases)),b,True)
for locale in ['A','0','Ab-12-c','A'*64]:
    b=clone(base);b['resources']=[resource(locale=locale)];add('valid-locale-'+str(len(cases)),b,True)
for count in [1,16,64]:
    b=clone(base);b['resources']=[resource(i) for i in range(count)];add('icons-'+str(count),b,True)
b=clone(base);b['resources']=[resource(i,kind='fontSFNT' if i<16 else 'iconPNG') for i in range(64)];add('16-fonts-48-icons',b,True)
b=clone(base);b['resources']=[resource(i,bytes=4194304 if i<4 else 1) for i in range(64)];b['resources'][0]['bytes']-=60
add('64-resources-exact-16MiB-total',b,True);b['resources'][0]['bytes']+=1;add('64-resources-over-total-by-one',b)
# Maximum accepted byte boundary with legal catalog strings; exact count includes LF.
b=clone(base);b['resources']=[resource(i,id=f'R{i:02d}'+'I'*125,path=f'P{i:02d}/'+'P'*252,locale='L'*64,provenance='V'*512) for i in range(64)]
assert len(canonical(b))>65536
for entry in b['resources']:
    excess=len(canonical(b))-65536
    if excess<=0:break
    shrink=min(excess,len(entry['provenance'])-1);entry['provenance']=entry['provenance'][:-shrink] if shrink else entry['provenance']
assert len(canonical(b))==65536
add('exact-65536-byte-canonical-catalog',b,True)
for entry in b['resources']:
    if len(entry['provenance'])<512:entry['provenance']+='V';break
assert len(canonical(b))==65537;add('65537-byte-canonical-catalog',b)
# Endpoint themes coherently satisfy dependent line/toggle geometry.
for endpoint in ['low','high']:
    b=clone(base);t=b['theme']
    for path,v in list(walk(t)):
        if isinstance(v,int):
            key=path[-1]
            val=(400 if key=='weight' else 64 if key in ['size64','minimumLineBox64'] else 0) if endpoint=='low' else (700 if key=='weight' else 16384 if key=='size64' else 1000 if key.endswith('Permille') else 65536)
            t=changed(t,path,val)
    if endpoint=='high': t['controls']['toggle'].update(thumb64=0,inset64=32768)
    b['theme']=t;add('coherent-'+endpoint+'-numeric-endpoints',b,True)
# Fresh deterministic valid themes exercise all numeric/color/control values together.
rng=random.Random(150723)
for i in range(160):
    b=clone(base);t=b['theme']
    for path,v in list(walk(t)):
        key=path[-1] if path else ''
        if isinstance(v,int):
            val=rng.choice([400,500,600,700]) if key=='weight' else rng.randint(64,16384) if key=='size64' else rng.randint(64,65536) if key=='minimumLineBox64' else rng.randint(0,1000) if key.endswith('Permille') else rng.randint(0,65536)
            t=changed(t,path,val)
        elif isinstance(v,str) and v.startswith('#'):
            t=changed(t,path,'#'+''.join(rng.choice('0123456789ABCDEF') for _ in range(8)))
    for role in ['body','headline','title','caption']:t['typography'][role]['minimumLineBox64']=max(t['typography'][role]['size64'],t['typography'][role]['minimumLineBox64'])
    toggle=t['controls']['toggle'];toggle['thumb64']=rng.randint(0,32768);toggle['inset64']=rng.randint(0,(65536-toggle['thumb64'])//2);envelope=toggle['thumb64']+2*toggle['inset64'];toggle['trackWidth64']=rng.randint(envelope,65536);toggle['trackHeight64']=rng.randint(envelope,65536);toggle['minimumRow64']=rng.randint(toggle['trackHeight64'],65536)
    b['theme']=t;add('valid-random-theme-'+str(i),b,True)
# Closed shape/type checks through every retained field of three concrete branches.
for label,seed in [('base',base),('fonted',fonted),('platform',platform)]:
    for path,v in walk(seed):
        tag=label+'-'+'.'.join(map(str,path))
        for bad in [None,True,False]:add(tag+'-type-'+str(bad),changed(seed,path,bad))
        if isinstance(v,dict):
            ext=clone(v);ext['unsupported']=0;add(tag+'-extra',changed(seed,path,ext))
            for key in v:
                missing=clone(v);del missing[key];add(tag+'-missing-'+key,changed(seed,path,missing))
        if isinstance(v,int):
            for bad in [-1,4294967296,18446744073709551615,18446744073709551616,0.5,'1',[],{}]:add(tag+'-number-'+str(bad),changed(seed,path,bad))
        if isinstance(v,str):
            for bad in ['', '\x00','\x1f','\x7f','\u0080','\ud800','X'*513]:add(tag+'-string-'+str(len(cases)),changed(seed,path,bad))
# Every prefix truncates a previously accepted canonical descriptor.
valid=canonical(base)
for cut in range(len(valid)):raw('truncate-'+str(cut),valid[:cut])
# Noncanonical whitespace/trailer/escapes and malformed integer spellings.
for data in [b' '+valid,b'\n'+valid,valid+b'\n',valid+b' ',valid[:-1]+b'\r\n',valid[:-1]+b'\x00',valid.replace(b':',b': ',1),valid.replace(b',',b',\n',1),valid.replace(b'"format"',b'"\\u0066ormat"',1),valid.replace(b'"format"',b'"format" :',1),b'\xef\xbb\xbf'+valid]:raw('alternate-'+str(len(cases)),data)
for token in [b'00',b'01',b'-0',b'-1',b'+1',b'1.',b'.1',b'1.0',b'1e0',b'1E+0',b'NaN',b'Infinity',b'null',b'true',b'false',b'9'*1000]:raw('integer-token-'+token[:15].decode('ascii'),valid.replace(b'1088',token,1))
# All byte values disallowed by string grammar at multiple actual string positions.
for c in list(range(32))+list(range(127,256)):
    for needle in [b'mixer.default.v1',b'sharedCandidate1',b'#FFFFFFFF']:
        raw('raw-byte-'+str(c)+'-'+needle.decode('ascii'),valid.replace(needle,bytes([c]),1))
# Guard limits independently reached before schema checks.
for depth in [16,17,10000]:raw('nested-depth-'+str(depth),b'['*depth+b'0'+b']'*depth+b'\n')
for count in [4095,4096,4097]:raw('object-values-'+str(count),b'{'+b','.join(('"k%04d":0'%i).encode('ascii') for i in range(count))+b'}\n')
for count in [64,65,1000]:raw('array-count-'+str(count),b'['+b','.join([b'0']*count)+b']\n')
for n in [512,513,65000]:raw('string-length-'+str(n),b'"'+b'x'*n+b'"\n')
# Byte-level canonical duplicate/ordering violations use actual keys.
raw('duplicate-root-id',valid.replace(b'"id":"mixer.default.v1"',b'"id":"mixer.default.v1","id":"mixer.default.v1"',1))
raw('decoded-duplicate-root-id',valid.replace(b'"id":"mixer.default.v1"',b'"id":"mixer.default.v1","\\u0069d":"mixer.default.v1"',1))
for i in range(len(valid)-1):
    if valid[i:i+2] in [b':{',b':[']:
        raw('token-internal-space-'+str(i),valid[:i+1]+b' '+valid[i+1:])
# Store preserved expected decisions and transport bytes; names are ASCII only.
encoded=json.dumps(cases,sort_keys=True,separators=(',',':')).encode('ascii')
(out/'independent-corpus.json.gz').write_bytes(gzip.compress(encoded,mtime=0))
tsv=''.join(f"{i}-{c['name']}\t{int(c['accepted'])}\t{c['base64']}\n" for i,c in enumerate(cases)).encode('ascii')
(out/'cases.tsv.gz').write_bytes(gzip.compress(tsv,mtime=0));(out/'build/cases.tsv').write_bytes(tsv)
print(json.dumps({'cases':len(cases),'accepted':sum(c['accepted'] for c in cases),'rejected':sum(not c['accepted'] for c in cases),'max_valid_bytes':max(len(base64.b64decode(c['base64'])) for c in cases if c['accepted'])},sort_keys=True))
