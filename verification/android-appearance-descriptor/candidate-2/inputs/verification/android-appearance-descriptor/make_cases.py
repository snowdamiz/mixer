#!/usr/bin/env python3
import base64, copy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
cases=json.loads((ROOT/'verification/ui-appearance-foundation/design-corpus.json').read_text())
def raw(name,data,accepted=False):cases.append({'name':name,'base64':base64.b64encode(data).decode(),'accepted':accepted})
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def add(name,value,accepted=False):raw(name,canonical(value),accepted)
base=json.loads((ROOT/'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json').read_text())
resource={'id':'font','kind':'fontSFNT','path':'Fonts/Owned.ttf','sha256':'a'*64,'bytes':4194304,'provenance':'Owned test metadata','scale':1,'locale':'und','direction':'neutral'}
bundled=copy.deepcopy(base);bundled['resources']=[resource]
bundled['theme']['typography']['font']={'kind':'bundled','fallback':'none','faces':[{'resourceID':'font','postScriptName':'Owned-Regular','weight':400,'style':'normal'},{'resourceID':'font','postScriptName':'Owned-Semibold','weight':600,'style':'normal'}]}
platform={'format':base['format'],'id':'explicit','mode':'platformSpecific','reason':'A \\ deliberate "choice"','resources':bundled['resources'],'iOS':bundled['theme'],'android':base['theme']}
for name,value in [('base',base),('bundled',bundled),('platform',platform)]:
 add('accept-'+name,value,True)
 def paths(v,path=()):
  yield path,v
  if isinstance(v,dict):
   for k,child in v.items():yield from paths(child,path+(k,))
  elif isinstance(v,list):
   for i,child in enumerate(v):yield from paths(child,path+(i,))
 def replace(v,path,new):
  if not path:return new
  out=copy.deepcopy(v);p=out
  for key in path[:-1]:p=p[key]
  p[path[-1]]=new;return out
 for path,v in paths(value):
  label=name+'-'+'.'.join(map(str,path))
  add(label+'-null',replace(value,path,None))
  if isinstance(v,dict):
   changed=copy.deepcopy(v);changed['unknownField']=0;add(label+'-unknown',replace(value,path,changed))
   for key in v:
    changed=copy.deepcopy(v);del changed[key];add(label+'-missing-'+key,replace(value,path,changed))
  if isinstance(v,int):
   for invalid in [-1,4294967296,True,0.5]:add(label+'-number-'+str(invalid),replace(value,path,invalid))
for prop,val in [('scale',2),('locale','en'),('direction','leftToRight')]:
 b=copy.deepcopy(base);b['resources']=[copy.deepcopy(resource)];b['resources'][0][prop]=val;add('unreferenced-font-'+prop,b)
for badpath in ['/root/a','a//b','a/','../a','a/.hidden','a/..','a\\b','a:b','a%2fb']:
 b=copy.deepcopy(base);b['resources']=[copy.deepcopy(resource)];b['resources'][0]['path']=badpath;add('path-'+badpath,b)
for count in [16,17,64,65]:
 b=copy.deepcopy(base);b['resources']=[dict(resource,id='f'+str(i),path='f'+str(i)+'.ttf',bytes=1) for i in range(count)];add('font-count-'+str(count),b,count<=16)
for count in [64,65]:
 b=copy.deepcopy(base);b['resources']=[dict(resource,id='i'+str(i),kind='iconPNG',path='i'+str(i)+'.png',bytes=1) for i in range(count)];add('icon-count-'+str(count),b,count<=64)
for n in [4,5]:
 b=copy.deepcopy(base);b['resources']=[dict(resource,id='r'+str(i),path='r'+str(i)+'.ttf') for i in range(n)];add('aggregate-'+str(n),b,n==4)
b=copy.deepcopy(base);b['resources']=[resource,dict(resource,id='other',path='fonts/owned.ttf')];add('case-fold-collision',b)
for old,new in [(b'1088',b'01'),(b'1088',b'1.0'),(b'1088',b'1e3'),(b'1088',b'+1'),(b'1088',b'18446744073709551615'),(b'"mode":"shared"',b'"mode":"shared","mode":"shared"'),(b'"mode":"shared"',b'"mode":"shared","m\\u006fde":"shared"')]:raw('lexical-'+new.decode(),canonical(base).replace(old,new))
for data in [b'',b' '*65537,canonical(base).rstrip(b'\n'),canonical(base)+b'\n',b' '+canonical(base),canonical(base).replace(b'"format"',b'"\\u0066ormat"'),b'['*17+b'0'+b']'*17+b'\n',b'{'+b','.join(('"k%04d":0'%i).encode() for i in range(4097))+b'}\n',b'["'+b'x'*513+b'"]\n',b'\xef\xbb\xbf'+canonical(base)]:raw('raw-'+str(len(cases)),data)
for d in [b'\x7f',b'\x80',b'\xff']:
 raw('bad-ascii-'+d.hex(),canonical(base).replace(b'mixer.default.v1',d))
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
(HERE/'cases.tsv').write_text(''.join(f"{i}-{c['name']}\t{int(c['accepted'])}\t{c['base64']}\n" for i,c in enumerate(cases)))
print(json.dumps({'cases':len(cases),'accepted':sum(c['accepted'] for c in cases)}))
