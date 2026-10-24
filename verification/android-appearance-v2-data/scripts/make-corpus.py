#!/usr/bin/env python3
"""Independently authored admission and geometry inputs; no platform claims."""
import base64, copy, gzip, hashlib, json, math, random, struct, sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
golden=(root/'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json').read_bytes()
base=json.loads(golden);cases=[]
def canonical(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def add(name,value,ok=True,raw=False):
 b=value if raw else canonical(value)
 cases.append((name,int(ok),b))
def modified(name,path,value,ok=False):
 x=copy.deepcopy(base);p=x
 for k in path[:-1]:p=p[k]
 p[path[-1]]=value;add(name,x,ok)
add('golden',golden,raw=True)
platform={'format':base['format'],'id':'app.platform.v2','mode':'platformSpecific','iOS':base['theme'],'android':copy.deepcopy(base['theme']),'reason':'Deliberate complete theme choice','resources':[]}
add('platform-specific',platform)
x=copy.deepcopy(platform);x['android']['light']['canvas']='#A1B2C37F';x['android']['button']['overlayRadius64']=128;add('platform-independent-values',x)
for profile in ['xs','s','m','l','xl','xxl','xxxl','a1','a2','a3','a4','a5']:
 modified('default-profile-'+profile,['theme','typography','defaultProfile'],profile,True)
for alignment in ['leading','center','trailing']:modified('horizontal-'+alignment,['theme','stacks','vStackAlignment'],alignment,True)
for alignment in ['top','center','bottom','firstTextBaseline','lastTextBaseline']:modified('vertical-'+alignment,['theme','stacks','hStackAlignment'],alignment,True)
for alignment in ['center','leading','trailing','top','bottom','topLeading','topTrailing','bottomLeading','bottomTrailing']:
 modified('overlay-'+alignment,['theme','stacks','zStackAlignment'],alignment,True)
# Complete colors are app-defined; exact clear/inactive contracts remain fixed.
x=copy.deepcopy(base);rng=random.Random(302)
def recolor(p):
 if isinstance(p,dict):
  for k,v in p.items():
   if isinstance(v,str) and v.startswith('#'):p[k]='#'+''.join(rng.choice('0123456789ABCDEF') for _ in range(8))
   else:recolor(v)
for mode in ['light','dark']:
 p=x['theme'][mode];recolor(p)
 for role in ['normal','destructive','cancel']:p['button'][role]['disabled']['background']='#00000000'
 p['field']['disabled']['caret']=p['field']['disabled']['selection']='#00000000'
 p['toggle']['on']['disabled']['overlay']=p['toggle']['off']['disabled']['overlay']='#00000000'
add('custom-complete-paints',x)
for bound in [0,65536]:
 x=copy.deepcopy(base);t=x['theme']
 for component in [t['button']['labelInsets64'],t['field']['insets64'],t['groupedList']['contentInsets64'],t['navigation']['expandedInsets64'],t['navigation']['compactInsets64']]:
  for k in component:component[k]=bound
 for k in ['outerHorizontal64','topPadding64','bottomPadding64','headerToGroup64','groupToNextHeader64','groupWithoutHeaderGap64','separatorInset64','separatorThickness64','radius64']:t['groupedList'][k]=bound
 for k in t['groupedList']['profileFloors64']:t['groupedList']['profileFloors64'][k]=max(1792,bound)
 for parent,keys in [(t['button'],['minimumHitHeight64','minimumHitWidth64']),(t['field'],['minimumHitHeight64','minimumContentHeight64']),(t['toggle'],['minimumHitHeight64','minimumHitWidth64']),(t['navigation'],['minimumExpandedBar64','minimumCompactBar64'])]:
  for k in keys:parent[k]=max(1,bound)
 t['button']['overlayRadius64']=bound;t['stacks']['defaultGap64']=bound;t['stacks']['bodyCaptionGap64']=bound;t['toggle']['labelGap64']=bound
 add('custom-geometry-'+str(bound),x)
modified('identifier128',['id'],'A'*128,True)
x=copy.deepcopy(platform);x['reason']='R'*512;add('reason512',x)
x=copy.deepcopy(platform);x['reason']='Escaped "quote" and backslash \\';add('canonical-escapes',x)
# Synthetic metadata, not usable font bytes or native resource receipts.
def resource(i,kind='iconPNG',size=1):return {'id':'r'+str(i),'kind':kind,'path':'Assets/R'+str(i)+('.ttf' if kind=='fontSFNT' else '.png'),'sha256':'0123456789abcdef'*4,'bytes':size,'provenance':'Independent synthetic test metadata','scale':1,'locale':'und','direction':'neutral'}
def face(i,weight,style='normal'):return {'resourceID':'r'+str(i),'postScriptName':'Synthetic-'+str(weight)+'-'+style,'weight':weight,'style':style}
x=copy.deepcopy(base);x['resources']=[resource(i,'fontSFNT') for i in range(3)];x['theme']['typography']['font']={'kind':'bundled','faces':[face(i,w) for i,w in enumerate([400,600,700])],'fallback':'none'}
add('bundled-required-normal',x)
bundledFixture=copy.deepcopy(x)
y=copy.deepcopy(x);y['theme']['typography']['font']['fallback']='systemSans';add('bundled-system-fallback',y)
y=copy.deepcopy(x);y['resources'].append(resource(3,'fontSFNT'));y['theme']['typography']['font']['faces'] += [face(3,500),face(3,500,'italic')];add('bundled-optional-weight-and-italic',y)
y=copy.deepcopy(platform);y['resources']=x['resources'];y['iOS']=x['theme'];add('platform-bundled-and-system',y)
for name,change in [
 ('missing-normal',lambda z:z['theme']['typography']['font']['faces'].pop()),
 ('duplicate-pair',lambda z:z['theme']['typography']['font']['faces'].append(z['theme']['typography']['font']['faces'][0])),
 ('missing-resource',lambda z:z['resources'].pop()),
 ('wrong-resource-kind',lambda z:z['resources'][0].update(kind='iconPNG')),
 ('italic-without-normal500',lambda z:z['theme']['typography']['font']['faces'].append(face(0,500,'italic'))),
 ('empty-faces',lambda z:z['theme']['typography']['font'].update(faces=[])),
 ('faces17',lambda z:z['theme']['typography']['font'].update(faces=[face(0,400)]*17)),
 ('space-postscript',lambda z:z['theme']['typography']['font']['faces'][0].update(postScriptName='Bad Name'))]:
 y=copy.deepcopy(x);change(y);add(name,y,False)
for count in [16,64,65]:
 x=copy.deepcopy(base);x['resources']=[resource(i) for i in range(count)];add('icon-count-'+str(count),x,count<=64)
for count in [16,17]:
 x=copy.deepcopy(base);x['resources']=[resource(i,'fontSFNT') for i in range(count)];add('font-count-'+str(count),x,count<=16)
x=copy.deepcopy(base);x['resources']=[resource(i,size=4194304) for i in range(4)];add('resource-total-exact',x)
x['resources'].append(resource(4));add('resource-total-over',x,False)
x=copy.deepcopy(base);x['resources']=[resource(0)]
for name,path,value,ok in [('resource-byte0',['bytes'],0,False),('resource-byte-max',['bytes'],4194304,True),('resource-byte-over',['bytes'],4194305,False),('resource-scale4',['scale'],4,True),('resource-scale0',['scale'],0,False),('locale-valid',['locale'],'en-Latn-US',True),('locale-double',['locale'],'en--US',False),('locale-leading',['locale'],'-en',False),('locale-trailing',['locale'],'en-',False),('provenance-space',['provenance'],' Bad',False),('provenance-tail',['provenance'],'Bad ',False),('digest-uppercase',['sha256'],'A'*64,False),('resource-direction',['direction'],'rightToLeft',True)]:
 y=copy.deepcopy(x);y['resources'][0][path[0]]=value;add(name,y,ok)
for path,ok in [('Assets/ok-file_1.ttf',True),('_/A.B',True),('../a',False),('Assets/../a',False),('/a',False),('a/',False),('a//b',False),('.hidden',False),('a/.hidden',False),('a/./b',False),('C:\\a',False),('a%20b',False),('a b',False),('a\\b',False)]:
 y=copy.deepcopy(x);y['resources'][0]['path']=path;add('path-'+str(len(cases)),y,ok)
for field in ['id','path']:
 y=copy.deepcopy(x);y['resources'].append(resource(1));y['resources'][1][field]=y['resources'][0][field];add('duplicate-resource-'+field,y,False)
y=copy.deepcopy(x);y['resources'].append(resource(1));y['resources'][1]['path']=y['resources'][0]['path'].lower();add('folded-resource-path',y,False)
for field,val in [('scale',2),('locale','en'),('direction','rightToLeft')]:
 y=copy.deepcopy(x);y['resources'][0]['kind']='fontSFNT';y['resources'][0][field]=val;add('font-variant-'+field,y,False)
# Adversarial unknown/missing fields at every object, wrong types at every leaf.
def walk(value,path=()):
 if isinstance(value,dict):
  yield path,value
  for k,v in value.items():yield from walk(v,path+(k,))
 elif isinstance(value,list):
  for i,v in enumerate(value):yield from walk(v,path+(i,))
def at(obj,path):
 for k in path:obj=obj[k]
 return obj
for idx,(path,obj) in enumerate(walk(base)):
 y=copy.deepcopy(base);at(y,path)['unknownV2']=0;add('unknown-object-'+str(idx),y,False)
 for key in obj:
  y=copy.deepcopy(base);del at(y,path)[key];add('missing-'+str(idx)+'-'+key,y,False)
 for key,value in obj.items():
  if isinstance(value,(str,int)):
   y=copy.deepcopy(base);at(y,path)[key]=[];add('wrong-type-'+str(idx)+'-'+key,y,False)
   if isinstance(value,str) and not value.startswith('#'):
    y=copy.deepcopy(base);at(y,path)[key]='unknown';
    if key not in ['id']:add('unknown-string-'+str(idx)+'-'+key,y,False)
# Missing/unknown catalog and face fields are independent of the empty default catalog.
for idx,(path,obj) in enumerate(walk(bundledFixture)):
 if path and (path[0]=='resources' or path[:3]==('theme','typography','font')):
  y=copy.deepcopy(bundledFixture);at(y,path)['unknownV2']=0;add('catalog-unknown-'+str(idx),y,False)
  for key in obj:
   y=copy.deepcopy(bundledFixture);del at(y,path)[key];add('catalog-missing-'+str(idx)+'-'+key,y,False)
   if isinstance(obj[key],(str,int)):
    y=copy.deepcopy(bundledFixture);at(y,path)[key]=[];add('catalog-type-'+str(idx)+'-'+key,y,False)
# Contract-specific semantic boundaries.
for role in ['body','headline','title','caption','sectionHeader','navigationExpanded']:
 for field,value in [('size64',64),('weight',500)]:
  modified('changed-profile-'+role+'-'+field,['theme','typography','profiles','l',role,field],value)
for mode in ['light','dark']:
 for role in ['normal','destructive','cancel']:
  modified('disabled-button-'+mode+role,['theme',mode,'button',role,'disabled','background'],'#00000001')
 for field in ['caret','selection']:
  modified('disabled-field-'+mode+field,['theme',mode,'field','disabled',field],'#01000000')
 for state in ['enabled','disabled']:modified('inactive-outline-'+mode+state,['theme',mode,'field',state,'outline','width64'],1)
 for val in ['on','off']:modified('disabled-overlay-'+mode+val,['theme',mode,'toggle',val,'disabled','overlay'],'#00010000')
modified('floor-below-track',['theme','groupedList','profileFloors64','xs'],1791)
modified('floor-decreases',['theme','groupedList','profileFloors64','xs'],65536)
modified('nav-inverted',['theme','navigation','minimumCompactBar64'],65536)
for field in ['trackWidth64','trackHeight64','thumbWidth64','thumbHeight64','trackAuthoringRadius64','thumbAuthoringRadius64','thumbInset64']:
 modified('switch-fixed-'+field,['theme','toggle',field],base['theme']['toggle'][field]+1)
for val in ['', ' ', ' bad', 'bad ', 'x'*513]:
 y=copy.deepcopy(platform);y['reason']=val;add('bad-reason-'+str(len(cases)),y,False)
for val in ['', 'x'*129,'x/y','x y','x\n']:
 modified('bad-id-'+str(len(cases)),['id'],val)
for val in ['#abcdef01','#0000000','#000000000','#0000000G','#000000#0']:
 modified('bad-color-'+str(len(cases)),['theme','light','canvas'],val)
for val in [65537,4294967295,18446744073709551615,18446744073709551616]:
 modified('metric-bound-'+str(val),['theme','button','overlayRadius64'],val)
# Alternate wire forms and construction bounds.
for name,b in [('empty',b''),('no-lf',golden[:-1]),('double-lf',golden+b'\n'),('leading-space',b' '+golden),('crlf',golden[:-1]+b'\r\n'),('trailing-space',golden[:-1]+b' \n'),('bom',b'\xef\xbb\xbf'+golden),('nonascii',golden.replace(b'mixer.measured-candidate.v2',b'\xff')),('escaped-ascii',golden.replace(b'"format"',b'"\\u0066ormat"',1)),('escaped-slash',canonical(x).replace(b'Assets/',b'Assets\\/')),('duplicate-key',golden.replace(b'{',b'{"format":"mixer.native-appearance.2",',1)),('leading-zero',golden.replace(b':2816',b':02816',1)),('negative',golden.replace(b':2816',b':-1',1)),('fraction',golden.replace(b':2816',b':1.0',1)),('exponent',golden.replace(b':2816',b':1e3',1)),('boolean',golden.replace(b':2816',b':true',1)),('null',golden.replace(b':2816',b':null',1)),('unsorted',json.dumps(dict(reversed(list(base.items()))),separators=(',',':')).encode()+b'\n'),('truncated',golden[:100]),('trailing-json',golden+b'{}'),('oversize',b' '*65537),('depth21',b'['*21+b'0'+b']'*21+b'\n'),('array65',canonical([0]*65)),('values-over',canonical([[[0]*64 for _ in range(64)] for _ in range(2)]))]:
 add(name,b,False,True)
for length in [65535,65536]:add('byte-bound-'+str(length),b' '*length,False,True)
v1=(root/'verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json').read_bytes();add('v1-format',v1,False,True)
# Admit real complete descriptors at the wire byte boundary, not just junk of
# that length. Fill only admitted printable resource metadata; no resource loads.
for target in [65535,65536,65537]:
 x=copy.deepcopy(base);x['resources']=[resource(i) for i in range(64)]
 remaining=target-len(canonical(x))
 for field,limit in [('provenance',512),('path',256),('id',128),('locale',64)]:
  for r in x['resources']:
   amount=min(remaining,limit-len(r[field]));r[field]+='X'*amount;remaining-=amount
 assert remaining==0 and len(canonical(x))==target
 add('complete-byte-bound-'+str(target),x,target<=65536)
# Balanced synthetic arrays reach the global count without violating 64 slots.
def values_tree(count):
 if count==1:return 0
 slots=min(64,count-1);q,r=divmod(count-1,slots)
 return [values_tree(q+(i<r)) for i in range(slots)]
add('values-exact8192',values_tree(8192),False)
add('values-over8193',values_tree(8193),False)
# Every corpus input is retained exactly, gzip uses a deterministic timestamp.
raw=''.join(n+'\t'+str(ok)+'\t'+base64.b64encode(b).decode()+'\n' for n,ok,b in cases).encode()
with gzip.GzipFile(filename=str(out/'descriptors.tsv.gz'),mode='wb',mtime=0) as f:f.write(raw)
(out/'descriptor-input-hashes.json').write_text(json.dumps({n:{'accepted':bool(ok),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,ok,b in cases},sort_keys=True,indent=2)+'\n')
# Geometry outputs are emitted independently by both products, not copied from either.
g=[]
def geo(op,*args):g.append(('g'+str(len(g)),op,*map(str,args)))
geo('track');geo('thumb')
for w,h in [(0,1),(1,0),(0,0),(1,1),(2,3),(3,2),(5,7),(64,64),(2147483647,2147483647),(2147483647,1),(1,2147483647),(10001,9001),(2147483648,1),(4294967295,1)]:
 for r in [0,1,64,1664,65536,65537,4294967295]:geo('group',w,h,r)
for _ in range(300):geo('group',rng.randrange(0,2147483648),rng.randrange(0,2147483648),rng.randrange(0,65537))
for w in range(1,128):geo('group',w,w+1,65536)
for checked in [0,1]:
 for direction in ['leftToRight','rightToLeft']:geo('origin',checked,direction)
def bits(x):return struct.pack('>d',x).hex()
for op,lower,upper,scale in [('measure',0,2147483647/64,64),('spacing',0,256,64),('density',.125,16,1024)]:
 vals=[-0.0,0.0,float('nan'),float('inf'),-float('inf'),-1,lower,math.nextafter(lower,-math.inf),math.nextafter(lower,math.inf),upper,math.nextafter(upper,-math.inf),math.nextafter(upper,math.inf)]
 for k in [0,1,2,127,1023,8191]:
  v=(k+.5)/scale;vals += [math.nextafter(v,-math.inf),v,math.nextafter(v,math.inf)]
 for _ in range(100):vals.append(rng.uniform(lower,upper))
 for val in vals:geo(op,bits(val))
for coord in [0,1,31,32,33,63,64,65,127,128,129,65535,2147483647,2147483648,4294967295]:
 for density in [0,127,128,129,1023,1024,1025,3072,16383,16384,16385,65535]:
  geo('edge',coord,density);geo('coordinate',coord,density)
for _ in range(300):
 coord=rng.randrange(2147483648);density=rng.randrange(128,16385);geo('edge',coord,density);geo('coordinate',coord,density)
(out/'geometry.tsv').write_text(''.join('\t'.join(row)+'\n' for row in g))
print('PASS authored descriptors='+str(len(cases))+' accepted='+str(sum(x[1] for x in cases))+' geometry='+str(len(g)))
