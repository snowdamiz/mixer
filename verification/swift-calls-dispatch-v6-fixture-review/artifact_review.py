#!/usr/bin/env python3
"""Read-only compiler-attempt, archive, paired-layout and Frozen replay."""
from pathlib import Path
import argparse, datetime, gzip, hashlib, json, re, sys
from review import BASE,PACKET,archive,contexts,read,require,sha
PIN='b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'
BASELINE='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c'
SYSROOT_IDENTITIES=set()
def encoded(o):return (json.dumps(o,sort_keys=True,indent=2)+'\n').encode()
def attempt(name,expected=None,overlay=False,require_sysroot=True):
 p=PACKET/name;c=read(p/'command.json');m=read(p/'source-manifest.json');tools=read(p/'tools.json');cleanup=read(p/'cleanup.json')
 require(sha(encoded(m))==c['sourceClosure'],'attempt source digest')
 require(c['exitCode']==0 and c['sourceUnchanged']and not c['remainingGroup'],'failed/drifting compiler attempt')
 require(cleanup['removed']and cleanup['holderCheckEmpty']and cleanup['nativeInstancesCreated']==0,'attempt cleanup incomplete')
 version=tools['rustc']['stdout'];require(PIN in version and 'release: 1.99.0' in version and 'host: aarch64-apple-darwin'in version,'compiler pin drift')
 require(tools['actualCompiler']['sha256']=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0','compiler binary drift')
 if require_sysroot:
  compiler=tools['actualCompiler'];files=compiler['sysrootCompilerFiles'];digest=sha(encoded(files));require(digest==compiler['sysrootCompilerFilesSHA256'],'per-attempt sysroot manifest digest')
  original=read(PACKET/'tool-preparation/20261024T160529443594Z/original-sysroot-bindings.json');require(all(files.get(k)==v for k,v in original.items()),'original sysroot byte drift')
  require(files['bin/rustc']==compiler['sha256'],'resolved compiler not in sysroot manifest');SYSROOT_IDENTITIES.add(digest);require(len(SYSROOT_IDENTITIES)==1,'compiler/sysroot changed between required contexts')
 for stream in ['stdout','stderr']:
  require(sha(gzip.decompress((p/(stream+'.log.gz')).read_bytes()))==c[stream+'SHA256'],'compiler output digest mismatch')
 files=archive(p/'source.tar.gz',m)
 if overlay:
  project=read(p/'source-projection.json');require(project['originalClosure']==expected,'layout source closure mismatch');require(project['probeManifest']==m,'layout projection source mismatch')
  original=project['originalManifest'];require(sha(encoded(original))==expected,'layout original manifest mismatch')
  require(project['onlyProbeAppendAndBin']and project['noInterpreterExecution'],'unreviewed layout probe')
  require(set(project['appends'])=={'src/experimental_swift_reactor/frame_operations.rs','src/experimental_swift_reactor/mod.rs','src/lib.rs'},'unexpected probe append')
  for n,h in original.items():
   if n in project['appends']:
    a=project['appends'][n];require(a['originalSHA256']==h and sha(files[n][:a['prefixBytes']])==h and sha(files[n][a['prefixBytes']:])==a['appendedSHA256'],'probe changed original source')
   else:require(sha(files[n])==h,'probe changed original file')
  require(set(m)-set(original)=={'src/bin/calls_layout.rs'},'probe added unexpected file')
  require(b'mixer_vm::calls_layout_metadata_only()'in files['src/bin/calls_layout.rs'],'probe binary entry changed')
  identity=read(p/'executable-identity.json');require(identity['sourceClosure']==c['sourceClosure'],'metadata executable source mismatch')
  require(c.get('postExitCode')==0 and c.get('postExecutionSucceeded'),'metadata execution failed')
  require(all(x['exitCode']==0 and not x['remainingGroup']for x in identity['commands']),'metadata command failed')
  binaries=read(p/'artifacts.json');require(any(x['sha256']==identity['sha256']for x in binaries),'metadata executable not archived')
  for x in binaries:
   require(sha(gzip.decompress((p/x['path']).read_bytes()))==x['sha256'],'archived artifact digest')
  out=gzip.decompress((p/'execute-stdout.gz').read_bytes()).decode();parsed={k:{}for k in ['totals','types','owners']}
  for line in out.splitlines():
   if 'CL_'not in line:continue
   kind,key,*vs=line[line.index('CL_'):].split();values=list(map(int,vs));target={'CL_TOTAL':'totals','CL_TYPE':'types','CL_OWNER':'owners'}[kind]
   require(key not in parsed[target],'duplicate layout output');parsed[target][key]=values[0]if len(values)==1 else dict(bytes=values[0],alignment=values[1])
  return parsed
 if expected is not None:require(c['sourceClosure']==expected,'attempt not final source closure')
 return files
def balanced(text,start):
 # Expanded Rust bodies here are retained byte-for-byte; quoted strings contain
 # braces, so use a scanner that ignores string/char literals and comments.
 pos=text.index('{',start);depth=0;i=pos;state=None
 while i<len(text):
  ch=text[i];nxt=text[i:i+2]
  if state=='line':
   if ch=='\n':state=None
  elif state=='block':
   if nxt=='*/':state=None;i+=1
  elif state in ['"',"'"]:
   if ch=='\\':i+=1
   elif ch==state:state=None
  elif nxt=='//':state='line';i+=1
  elif nxt=='/*':state='block';i+=1
  elif ch=='"':state=ch
  elif ch=="'" and i+2<len(text)and(text[i+2]=="'"or text[i+1]=='\\'):state=ch
  elif ch=='{':depth+=1
  elif ch=='}':
   depth-=1
   if depth==0:return text[start:i+1]
  i+=1
 raise ValueError('unbalanced expanded/source body')
def frozen(expected):
 f=read(PACKET/'frozen-identity.json');allmethods={}
 for label,closure in [('baseline',BASELINE),('candidate',expected)]:
  attempt(f[label]['attempt'],closure,require_sysroot=False);p=PACKET/f[label]['attempt'];raw=gzip.decompress((p/'stdout.log.gz').read_bytes()).decode();body=balanced(raw,raw.index('impl SpanInstance {'))
  matches=list(re.finditer(r'^\s+(?:pub )?fn (\w+)\(',body,re.M));require(len(matches)==39,'Frozen method count')
  methods={m[1]:sha(balanced(body,body.index('fn '+m[1]+'(')).encode())for m in matches};require(methods==f[label]['methods'],'Frozen map does not match actual expansion');allmethods[label]=methods
 require(allmethods['baseline']==allmethods['candidate'],'Frozen expanded semantic drift')
 return allmethods['candidate']
def paired(expected):
 result={}
 unchanged=['frame_permanent','frame_active','frame_frozen_permanent','frame_frozen_active','value','control_permanent','control_active','memory_permanent','memory_active','bulk_permanent','bulk_active','growth_permanent','growth_active','host_permanent','host_active','ticket_max','state_limit','combined_limit']
 for cfg in contexts():
  pair={}
  compiler_types={}
  for label,closure in [('baseline',BASELINE),('candidate',expected)]:
   f=read(PACKET/f'paired-layout-{label}-{cfg}.json');require(f['sourceClosure']==closure and f['exitCode']==0,'paired source or compile mismatch')
   parsed=attempt(f['attempt'],closure,True);require(all(f[k]==parsed[k]for k in ['totals','types','owners']),'paired values do not match raw executable output')
   raw=gzip.decompress((PACKET/f['attempt']/f['compilerLayouts']['path']).read_bytes());require(sha(raw)==f['compilerLayouts']['sha256'],'paired compiler layout digest');compiler_types[label]=json.loads(raw)
   pair[label]=f
  b,c=pair['baseline'],pair['candidate'];require(b['owners']==c['owners']and b['types']==c['types'],'original owner layout changed')
  require(all(b['totals'][k]==c['totals'][k]for k in unchanged),'prior reservation or ceiling changed')
  t=c['totals'];require(t['header']==b['totals']['header']+t['calls_permanent'],'nonadditive header')
  require(t['frame']==b['totals']['frame']+t['calls_active'],'nonadditive active envelope')
  require(t['calls_active']==sum(t[k]for k in ['calls_typed_active','calls_kind_active','calls_never_active','calls_numeric_active']),'active component total')
  require(t['calls_permanent']==sum(t[k]for k in ['calls_typed_permanent','calls_kind_permanent','calls_never_permanent','calls_numeric_permanent']),'permanent component total')
  require(t['ticket_max']==86 and t['state_limit']==128*1024**2 and t['combined_limit']==256*1024**2,'ceiling drift')
  prior={k:v for k,v in compiler_types['baseline'].items()if ('Positions'in k or'Inventory'in k)and k.startswith(('experimental_swift_reactor::','experimental_wasi::'))};require(prior,'missing original position class layouts')
  require(all(compiler_types['candidate'].get(k)==v for k,v in prior.items()),'old positive position class layout drift')
  bounds={}
  if cfg.startswith('all-'):
   names=['experimental::execution::SpanInstance','experimental::cache::FunctionCache','experimental::execution::ExecutionFailure','experimental::cache::CacheFailure','experimental::cache::DecodedInstruction','experimental::execution::Control',"experimental::execution::ScalarReader<'_>"]
   for label,types in compiler_types.items():
    s=[types[n]['bytes']for n in names];bound=s[0]-s[1]+3*s[2]+2*s[3]+s[4]+s[5]+s[6]+512;require(bound==2912,'Frozen original bound changed');bounds[label]=dict(zip(names,s))
   require(bounds['baseline']==bounds['candidate'],'Frozen component layout changed')
  result[cfg]={'baselineHeader':b['totals']['header'],'candidateHeader':t['header'],'baselineActive':b['totals']['frame'],'candidateActive':t['frame'],'callsActive':t['calls_active'],'callsPermanent':t['calls_permanent'],'ownersIdentical':True,'priorComponentsIdentical':True,'priorClassesIdentical':len(prior),'frozen2912ComponentSizes':bounds}
 return result
def compiler_tool(bindings):
 build=read(PACKET/'layout-driver-build.json');p=PACKET/build['attempt'];require(sha((PACKET/'layout_driver.rs').read_bytes())==build['sourceSHA256'],'current callback source differs from compiled tool')
 require(sha((p/'layout_driver.rs').read_bytes())==build['sourceSHA256'],'archived callback source differs from compiled tool')
 binary=gzip.decompress((p/'layout-driver.gz').read_bytes());require(sha(binary)==build['sha256']and len(binary)==build['bytes'],'actual metadata driver binary digest')
 require(all(q['toolSHA256']==build['sha256']for q in bindings.values()),'final query tool identity changed')
 prep=PACKET/'tool-preparation/20261024T160529443594Z';result=read(prep/'result.json');members=read(prep/'added-component-files.json');provenance=read(prep/'official-source-provenance.json');require(len(provenance)==2,'official compiler hash-source provenance incomplete')
 checked=[]
 for r in provenance:
  raw=(prep/r['artifact']).read_bytes();require(sha(raw)==r['sha256']and len(raw)==r['bytes'],'official source content digest')
  require(r['compilerCommit']==PIN and PIN in r['immutableOfficialSourceURL'],'official source commit drift')
  require(r['distributionFetchReceipt']['sha256']==result['componentSHA256'],'source distribution component drift')
  rel=r['componentArchiveMember'].split('/rustc-dev/',1)[1];require(members[rel]==r['sha256'],'source is not exact checked official component member')
  checked.append({'artifact':r['artifact'],'sha256':r['sha256'],'immutableOfficialSourceURL':r['immutableOfficialSourceURL']})
 require(sha((prep/'official-manifest.toml').read_bytes())==result['officialManifestSHA256'],'official distribution manifest drift')
 return {'driverSourceSHA256':build['sourceSHA256'],'driverBinarySHA256':build['sha256'],'pinnedOfficialSources':checked,'scope':'Metadata-only callback audited against pinned compiler root/path hashing algorithm; never product runtime code.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-closure',required=True);ap.add_argument('--query-bindings',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();result={'schema':1,'status':'in-progress','command':sys.argv,'cwd':str(Path.cwd()),'verifierSHA256':sha(Path(__file__).read_bytes()),'tool':sys.version,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'qualifiedRuntimeExecuted':False,'nativeInstancesCreated':0,'accountingAccepted':False}
 try:
  queries=read(a.query_bindings);require(set(queries)==set(contexts()),'eight contexts missing')
  result['queries']={cfg:{'attempt':q['attempt'],'sourceClosure':q['sourceClosure'],'files':len(attempt(q['attempt'],a.source_closure))}for cfg,q in queries.items()}
  result['pairedLayouts']=paired(a.source_closure);result['frozenMethods']=frozen(a.source_closure);result['compilerTool']=compiler_tool(queries);result['requiredCompilerSysrootSHA256']=sorted(SYSROOT_IDENTITIES);result['status']='artifact-replay-passed-additional-review-pending'
 except BaseException as e:result['status']='rejected';result['error']=repr(e)
 a.output.write_bytes(encoded(result));print(json.dumps(result,sort_keys=True,indent=2));return result['status']=='rejected'
if __name__=='__main__':raise SystemExit(main())
