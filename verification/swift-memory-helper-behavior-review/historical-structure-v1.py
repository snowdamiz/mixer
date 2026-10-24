from review import *
import collections
schema=json.loads((PRODUCER/'inventory-schema.json').read_text())
def metadata(output):
 result={k:{} for k in ['types','owners','fields','totals','classes']}
 for line in output.splitlines():
  if 'MM_' not in line:continue
  tag,name,*raw=line[line.index('MM_'):].split();values=list(map(int,raw));target={'MM_TYPE':'types','MM_OWNER':'owners','MM_FIELD':'fields','MM_TOTAL':'totals','MM_CLASS':'classes'}[tag];assert name not in result[target]
  result[target][name]=values
 return result
layouts=[]
for label in ['baseline','candidate']:
 vm=SCRATCH/('metadata-'+label)/'vm'
 for feature,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for release in [False,True]:
   for unit in [False,True]:
    name='layout-'+label+'-'+feature+('-release' if release else '-debug')+('-unit' if unit else '-production')
    args=['cargo','test','--lib','--locked','--offline',*flags,*(['--release'] if release else []),'memory_contract_metadata_only','--','--nocapture','--test-threads=1'] if unit else ['cargo','run','--locked','--offline','--bin','memory_contract_layout',*flags,*(['--release'] if release else [])]
    p=run(name,args,vm);assert p.returncode==0
    actual=metadata(p.stdout.decode());assert actual['totals']['state_limit']==[134217728] and actual['totals']['combined_limit']==[268435456]
    if feature=='all':assert actual['totals']['frozen_header']==[2912]
    if label=='candidate':
     old=next(x['actual'] for x in layouts if (x['label'],x['feature'],x['release'],x['unit'])==('baseline',feature,release,unit));assert old['types']==actual['types'] and old['owners']==actual['owners']
     selected=[r for r in schema if unit or r['config']!='unit'];assert set(actual['fields'])=={r['field'] for r in selected}
     ends={}
     for row in sorted(selected,key=lambda x:(x['ownerClass'],actual['fields'][x['field']][0])):
      offset,size,align=actual['fields'][row['field']];cls=row['ownerClass'];assert offset>=ends.get(cls,0) and offset%align==0;ends[cls]=offset+size;assert ends[cls]<=actual['classes'][cls][0]
     t=actual['totals'];assert t['memory_active']==[1142696 if unit else 624544] and t['memory_permanent']==[121856];assert t['header'][0]==old['totals']['header'][0]+121856;assert t['frame'][0]==old['totals']['frame'][0]+t['memory_active'][0]
     for key in ['construction','frame_permanent','frame_active','control_active','control_permanent','value']:assert t[key]==old['totals'][key]
    layouts.append(dict(label=label,feature=feature,release=release,unit=unit,actual=actual));(HERE/'layouts.json').write_bytes(enc(layouts))
# Compiler-expanded Frozen identity, independently split complete impl methods.
methods={}
for label in ['baseline','candidate']:
 p=run('expanded-'+label,['cargo','rustc','--lib','--all-features','--locked','--offline','--','-Zunpretty=expanded'],SCRATCH/label/'vm',{'RUSTC_BOOTSTRAP':'1'});assert p.returncode==0
 text=p.stdout.decode();span=text[text.index('impl SpanInstance {'):];start=span.index('{')+1;depth=1;end=start
 while depth:depth+=(span[end]=='{')-(span[end]=='}');end+=1
 span=span[start:end-1];m={}
 for line in re.finditer(r'^    (?:pub )?fn (\w+)\(',span,re.M):
  a=span.index('{',line.start());b=a+1;level=1
  while level:level+=(span[b]=='{')-(span[b]=='}');b+=1
  body=span[line.start():b];m[line.group(1)]=hashlib.sha256(body.encode()).hexdigest()
 assert len(m)==39;methods[label]=m
assert methods['baseline']==methods['candidate']
# Original owner declarations are compared byte for byte; no field/ticket changes.
def item(source,needle):
 start=source.index(needle);i=source.index('{',start)+1;depth=1
 while depth:depth+=(source[i]=='{')-(source[i]=='}');i+=1
 return source[start:i]
old=json.loads((PRODUCER/'frozen-identity.json').read_text());owners={}
for path,names in {'src/experimental/execution/mod.rs':['pub struct SpanInstance','pub(crate) struct Control','struct Frame','pub struct ExecutionBudget','pub struct ExecutionUsage','pub struct ExecutionFailure'],'src/experimental_swift_reactor/execution.rs':['pub(crate) struct SwiftExecutionState','pub(crate) struct SwiftReactorInstance','pub(crate) struct SwiftExecutionOperation','pub(crate) struct SwiftFrame','pub(crate) struct ExecutionOperationPhase'],'src/experimental_swift_reactor/frame_operations.rs':['pub(crate) struct FrameOperationPhase','pub(crate) struct FrameOperationStorage','pub(crate) struct FrameCleanupState']}.items():
 for needle in names:
  parts=[item((SCRATCH/label/'vm'/path).read_text(),needle) for label in ['baseline','candidate']];assert parts[0]==parts[1];owners[needle]=hashlib.sha256(parts[0].encode()).hexdigest()
# The authoritative ticket source and unchanged dependency manifests are byte-identical.
base=manifest(SCRATCH/'baseline/vm');candidate=manifest(SCRATCH/'candidate/vm');unchanged=[p for p in base if base[p]==candidate.get(p)]
assert base['Cargo.toml']==candidate['Cargo.toml'] and base['Cargo.lock']==candidate['Cargo.lock']
assert any('reservation' in p or 'control' in p for p in unchanged)
(HERE/'structural-results.json').write_bytes(enc(dict(layouts=16,frozenMethods=methods['candidate'],frozenReservationBytes=2912,ownerDeclarations=owners,unchangedSourcePaths=unchanged,sourceChanges=[p for p in sorted(set(base)|set(candidate)) if base.get(p)!=candidate.get(p)])))
print('16 paired layouts, 14 original owner declarations, 39 Frozen methods and unchanged manifests verified',flush=True)
