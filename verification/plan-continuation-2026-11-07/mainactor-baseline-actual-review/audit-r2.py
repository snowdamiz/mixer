import hashlib, importlib.util, json, os, sys, time, zipfile
from pathlib import Path
OWN = Path(__file__).resolve().parent
BASE = OWN.parent
ROOT = BASE.parents[1]
CTRL = BASE / 'mainactor-controller-rebind-r2'
PACKAGE = BASE / 'android-mainactor-witness-fix-r2'
REPORT = {'schema':1,'scope':'retained actual API37 baseline evidence; data and oracle only','python':sys.version,'checks':{},'identities':{},'failures':[]}
def guard(event,args):
    if event.startswith(('subprocess.','socket.','os.exec','os.spawn','os.fork','os.posix_spawn','pty.')) or event in ('os.system','os.kill','os.killpg'):
        raise RuntimeError('audit forbidden effect: '+event)
    if event == 'open':
        p,mode,flags=args
        writing = (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and (not isinstance(p,(str,bytes,os.PathLike)) or not Path(p).resolve().is_relative_to(OWN)):
            raise RuntimeError('audit write outside ownership')
sys.addaudithook(guard)
def check(key,ok,detail=None):
    REPORT['checks'][key]={'passed':bool(ok),'detail':detail}
    if not ok: REPORT['failures'].append(key)
def identity(p):
    p=Path(p); b=p.read_bytes()
    v={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    REPORT['identities'][str(p)] = v
    return v
def read(p):
    identity(p)
    return json.loads(Path(p).read_text())
def match(p,want):
    return identity(p)=={k:want[k] for k in ('bytes','sha256')}
def ref(r):
    p=Path(r['path'])
    return p if p.is_absolute() else ROOT/p
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod
    spec.loader.exec_module(mod); return mod
start=time.monotonic()
r=read(CTRL/'runtime-baseline/receipt.json')
res=read(BASE/'mainactor-root-runtime-r2/result.json')
sel=read(BASE/'mainactor-root-runtime-r2/selection.json')
ad=read(BASE/'mainactor-root-runtime-r2/admission.json')
bl=read(BASE/'mainactor-root-runtime-r2/baseline.json')
packet=read(CTRL/'controller-packet.json')
handoff=read(BASE/'mainactor-combined-review-r2/handoff.json')
pr=read(BASE/'mainactor-combined-review-r2/package-review.json')
cr=read(BASE/'mainactor-combined-review-r2/controller-review.json')
for k in ('receipt','selection','rootAdmission','externalBefore','externalAfter'):
    check('root-result-ref:'+k,match(ref(res[k]),res[k]))
for k in ('review','controller'):
    check('selection-ref:'+k,match(ref(sel[k]),sel[k]))
for k,v in handoff.items():
    if isinstance(v,dict) and {'path','bytes','sha256'} <= v.keys():
        check('combined-handoff-ref:'+k,match(ref(v),v))
check('actual-receipt-pinned',identity(CTRL/'runtime-baseline/receipt.json')['sha256']=='09f1e971670729295162f74773283ca648e84c47053606932736a11200424452')
check('admission-baseline-binding',match(ref(ad['externalRuntimeBaselineEvidence']),ad['externalRuntimeBaselineEvidence']['identity']))
check('actual-admission-equal',ad==r['rootAdmission'] and match(BASE/'mainactor-root-runtime-r2/admission.json',r['rootAdmissionIdentity']))
check('nonce-across-selection',ad['nonce']==bl['nonce']==r['nonce']==r['observation']['nonce'])
canon=hashlib.sha256(json.dumps(pr,sort_keys=True,separators=(',',':')).encode()).hexdigest()
check('prior-combined-review-real',pr['verdict']==cr['verdict']==handoff['verdict']=='ACCEPT' and cr['packageReview']==canon==handoff['packageCanonicalSHA256'])
check('controller-identity',identity(CTRL/'run_mainactor.py')['sha256']==r['controllerSHA256']==cr['controllerSHA256'])
check('packet-identity',identity(CTRL/'controller-packet.json')['sha256']==r['packetSHA256']==cr['packetSHA256']==ad['packetSHA256'])
check('package-review-binding',pr['apkSHA256']==packet['apk']['sha256']==r['apkSHA256'] and pr['oracleSHA256']==packet['oracle']['sha256'] and pr['sourceDigest']==packet['witnessSourceDigest'])
for key in ('apk','witnessLibrary','witnessPacket','witnessSeal','witnessSourceInputs','oracle'):
    check('artifact:'+key,match(ref(packet[key]),packet[key]))
for namespace,p in [('package',PACKAGE/'seal.json'),('controller',CTRL/'candidate-seal.json')]:
    seal=read(p); failures=[]
    for rel,want in seal['files'].items():
        target=p.parent/rel
        if not match(target,want): failures.append(rel)
    check(namespace+'-sealed-files',not failures,{'count':len(seal['files']),'mismatches':failures})
check('controller-seal-review-binding',identity(CTRL/'candidate-seal.json')['sha256']==cr['combinedSealSHA256'])
files=packet['sourceFiles']; current={}
for rel,want in files.items():
    current[rel]=identity(ROOT/rel)
digest=hashlib.sha256(''.join(k+'\0'+v['sha256']+'\n' for k,v in sorted(current.items())).encode()).hexdigest()
check('canonical103',len(current)==103 and current==files and digest==packet['sourceSHA256']==ad['sourceSHA256'],{'count':len(current),'sha256':digest})
check('runtime-source-preflight',r['currentRootSourceClosure']=={'files':files,'count':103,'sha256':digest})
check('runtime-postflight-record',r['postflightStable'] is True and res['sourcePostflightStable'] is True and 'postflightError' not in r)
inputs=read(ref(packet['witnessSourceInputs']))
for rel,want in inputs.items():
    check('witness-current:'+rel,match(Path(want['realPath']),want))
    check('witness-retained:'+rel,match(PACKAGE/'campaign-1/source-retained'/rel,want))
witness_digest=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
check('witness-source-digest',witness_digest==packet['witnessSourceDigest'],witness_digest)
with zipfile.ZipFile(ref(packet['apk'])) as z:
    native=z.read('lib/arm64-v8a/libExecutorWitness.so')
    check('apk-native-byte-identity',hashlib.sha256(native).hexdigest()==packet['witnessLibrary']['sha256'] and native==ref(packet['witnessLibrary']).read_bytes())
    embedded=json.loads(z.read('assets/witness-source.json'))
    check('apk-embedded-source-manifest',embedded=={'sourceDigest':witness_digest,'sources':inputs})
commands=r['commands']
check('command-count',len(commands)==30 and sum(c['label']=='executor-instrumentation' for c in commands)==1 and r['nativeInstancesStarted']==1 and res['attempts']==1)
check('commands-json-coherence',read(CTRL/'runtime-baseline/commands.json')==commands)
raw={}
for c in commands:
    b={k:Path(p).read_bytes() for k,p in c['logs'].items()}
    for p in c['logs'].values(): identity(p)
    raw[c['label']]=b
    check('command:'+c['label'],
        all(c[k] is True for k in ('direct_child_reaped','stdout_eof','stderr_eof','owned_group_absent','terminal_custody'))
        and c['state']=='TERMINAL' and not c['cleanup_errors'] and c['stop'] is None
        and sum(map(len,b.values()))==c['output_bytes']<=8388608 and c['output_limit']==8388608 and c['aggregate_limit']==67108864)
check('aggregate-output',sum(c['output_bytes'] for c in commands)==r['cleanup']['aggregateBytes']==18078 and r['commandLimit'] is None and not r['outputLimitCommands'])
check('cleanup-records',r['cleanup']['allTerminalCustody'] is True and r['cleanup']['scratchRemoved'] is True and r['cleanup']['retainedListenerClosed'] is True and r['privateADBKeysRemoved'] is True and r['hold'] is None and r['cleanup']['hold'] is None)
check('protected-fs-records',r['externalBaselineBefore']==r['externalBaselineAfter'] and r['externalBaselineStable'] is True)
check('time-bounds-records',r['elapsedSeconds']==res['elapsedSeconds']<600 and packet['bounds']=={'bootSeconds':180,'instrumentationSeconds':20,'totalSeconds':600,'commandBytes':8388608,'aggregateBytes':67108864})
text=raw['executor-instrumentation']['stdout'].decode()
log=raw['executor-prestart-log']['stdout'].decode()
check('raw-bundle-copy',text==r['instrumentationOutput'] and not raw['executor-instrumentation']['stderr'])
check('raw-log-copy',log==r['startupAppLog'] and not raw['executor-prestart-log']['stderr'])
check('uid-routing',raw['executor-uid']['stdout']==b'package:dev.mixer.executor uid:10231\n' and '--uid=10231' in commands[28]['argv'])
check('log-before-instrument',commands[28]['started_monotonic']<commands[29]['started_monotonic'] and r['logCaptureStartedBeforeInstrumentation'] is True)
check('instrument-nonce',commands[29]['argv'][-3:]==['nonce',r['nonce'],'dev.mixer.executor/dev.mixer.executor.Witness'])
for prop,want in r['observedRuntime'].items():
    check('runtime:'+prop,raw['identity-'+prop]['stdout'].decode().strip()==want)
check('runtime-image',r['observedRuntime']['ro.build.version.sdk']=='37' and r['observedRuntime']['ro.product.cpu.abi']=='arm64-v8a' and r['observedRuntime']['ro.build.fingerprint']==packet['selectedImage']['fingerprint'])
check('console-identity',json.loads(raw['owned-console-avd-name']['stdout'])==r['consoleIdentity'])
check('install-bytes',packet['apk']['path']==commands[26]['argv'][-1] and raw['executor-install']['stdout']==b'Performing Push Install\nSuccess\n' and '-r' not in commands[26]['argv'])
ext=[]
for k in ('externalBefore','externalAfter'):
    e=read(ref(res[k])); c=e['commands'][0]; stdout=Path(c['logs']['stdout']).read_bytes()
    identity(c['logs']['stdout']); identity(c['logs']['stderr'])
    parsed=json.loads(stdout); normalized={}
    for runtime,devices in parsed['devices'].items():
        for d in devices:
            normalized[d['udid']]={'runtime':runtime,**{k:d[k] for k in ('name','state','isAvailable')}}
    check(k+':raw-normalized',normalized==e['allDeviceStates'])
    check(k+':custody',all(c[x] is True for x in ('direct_child_reaped','stdout_eof','stderr_eof','owned_group_absent','terminal_custody')) and c['exit_code']==0 and not c['cleanup_errors'] and e['cleanup']['scratchRemoved'] is True)
    ext.append(e)
check('external-eight-unchanged',len(ext[0]['allDeviceStates'])==8 and ext[0]['allDeviceStates']==ext[1]['allDeviceStates']=={d['udid']:{k:v for k,v in d.items() if k!='udid'} for d in bl['externalDevices']})
check('protected-booted',all(d['state']=='Booted' for e in ext for d in e['protectedDevices'].values()))
check('admission-fresh-timeline',ext[0]['completedUnixSeconds']<=bl['observedUnixSeconds']<=ad['observedUnixSeconds']<=ext[1]['observedUnixSeconds'] and ext[1]['observedUnixSeconds']-ad['observedUnixSeconds']<120)
oracle=load('witness_oracle',CTRL/'witness_oracle.py')
stage=load('actual_root_rebind',CTRL/'root_rebind.py')
vals=oracle.parse(text)
obs=stage.classify_terminal(text,log,nonce=r['nonce'])
check('actual-oracle-replay',obs==r['observation'] and obs['outcome']=='MAINACTOR_START_NOT_REACHED' and obs['actualOutcome']=='MainActor-undrained')
rows=[line.split(',') for line in vals['events'].splitlines() if line]
REPORT['events']=rows
REPORT['oracleResult']=obs
REPORT['cutoff']={k:vals[k] for k in ('cutoffLowerNs','cutoffNs','serializationEndNs','elapsedNs','eventSlots','inflightAtCutoff','incompleteSlots','overflowAtCutoff','contentionLoss','exactWindowProven')}
mutations=[
('inflight',text.replace('inflightAtCutoff=0','inflightAtCutoff=1'),log),
('cutoff',text.replace('cutoffNs=6017567753','cutoffNs=1'),log),
('nonce',text.replace(r['nonce'],'different_nonce_123'),log),
('terminal',text.replace('INSTRUMENTATION_CODE: -1','INSTRUMENTATION_CODE: -10'),log),
('duplicate-terminal',text+'INSTRUMENTATION_CODE: -1\n',log),
('missing-log-row',text,'\n'.join(log.splitlines()[0:1]+log.splitlines()[2:])+'\n'),
('wrong-log-pid',text,log.replace('  2519  ','  9999  ',1)),
('wrong-log-tid',text,log.replace('  2574 I','  9999 I',1)),
('wrong-outcome',text.replace('outcome=MAINACTOR_START_NOT_REACHED','outcome=SHARED_UI_EXECUTOR_OBSERVED'),log),
('pump-contamination',text.replace('pumpCount=0','pumpCount=1'),log)]
for name,t,l in mutations:
    refused=False
    try: stage.classify_terminal(t,l,nonce=r['nonce'])
    except (RuntimeError,ValueError): refused=True
    check('oracle-negative-control:'+name,refused)
refused=False
try: oracle.evaluate(vals,mode='cf-pump',nonce=r['nonce'])
except ValueError: refused=True
check('oracle-cf-disabled',refused)
REPORT['limits']=['No native/device/process/network probe or inner launch','No revalidation of SDK/tool inventory of 1283 bound files','Cleanup and port release are retained historical assertions, not fresh OS observations','Root result lists released ports without a separate raw post-run bind transcript','No package-manager install or compiler performed by reviewer','No signature math repeated; exact APK hash bound to prior combined acceptance','No exact observation window, product executor, UI responsiveness, phone, FieldLog or GA qualification']
REPORT['elapsedSeconds']=time.monotonic()-start
REPORT['status']='PASS' if not REPORT['failures'] else 'FAIL'
(OWN/'audit-result-r2.json').write_text(json.dumps(REPORT,indent=2)+'\n')
print(json.dumps({k:REPORT[k] for k in ('status','python','failures','elapsedSeconds','oracleResult')},indent=2))
print('checks='+str(len(REPORT['checks']))+' identities='+str(len(REPORT['identities'])))
sys.exit(0 if not REPORT['failures'] else 1)
