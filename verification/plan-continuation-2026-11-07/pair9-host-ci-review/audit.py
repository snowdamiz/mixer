"""Data-only retained CI audit. Does not execute retained scripts or subject code."""
from pathlib import Path, PurePosixPath
import ast, collections, datetime, hashlib, json, os, struct, subprocess, sys, time, zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
V = ROOT / 'verification/plan-continuation-2026-11-07'
INPUT = V / 'ci96-android-host-actual'
ARCHIVE = Path('/tmp/mixer-ci96-android-host.zip')
REV = '96f03ab65966a6374e958e780fa09a3eed814c0b'
SHA = 'ea77e0529d5639b68fa8e8d3d9e30281b50e663d61ca66af6a6064bdc406a795'
started = time.monotonic()
checks = 0
commands = []
inputs = {}

def ident(b): return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
def check(v, why):
    global checks
    checks += 1
    if not v: raise ValueError(why)
def read(p):
    b = p.read_bytes(); inputs[str(p)] = ident(b); return b
def data(p): return json.loads(read(p))
def save(n, d): (OUT/n).write_text(json.dumps(d, indent=2, sort_keys=True)+'\n')
def git(*args, stdin=None):
    argv = ['git', *args]
    p = subprocess.run(argv, input=stdin, cwd=ROOT, capture_output=True, timeout=30,
                       env={**os.environ, 'GIT_NO_LAZY_FETCH':'1', 'GIT_TERMINAL_PROMPT':'0'})
    commands.append({'argv':argv,'exit':p.returncode,'stdout':ident(p.stdout),'stderr':ident(p.stderr)})
    check(p.returncode == 0, 'read-only Git failed '+repr(args)+': '+p.stderr.decode(errors='replace'))
    return p.stdout

git_version = git('--version').decode().strip()
tree = git('rev-parse', REV+'^{tree}').decode().strip()
acq = data(INPUT/'acquisition.json')
artifacts = data(INPUT/'artifact-list.json')['artifacts']
jobs = data(INPUT/'jobs.json')['jobs']
log = read(INPUT/'job.log').decode()
for p in [V/'android-host-review-r3/review.md', V/'android-host-review-r3/result.json',
          V/'android-motion-thread-review-r2/REVIEW.md', V/'android-motion-thread-review-r2/result.json']:
    read(p)
selection = data(V/'generated-java-pair9-r2-actual/selection.json')
check(ident(read(ARCHIVE)) == {'bytes':1716883,'sha256':SHA}, 'ZIP identity')
entries = {}
with zipfile.ZipFile(ARCHIVE) as z:
    infos = z.infolist()
    check(len({i.filename for i in infos}) == len(infos), 'duplicate ZIP members')
    for i in infos:
        check(not PurePosixPath(i.filename).is_absolute() and '..' not in PurePosixPath(i.filename).parts,
              'unsafe ZIP path')
        check((i.external_attr >> 16) & 0o170000 != 0o120000, 'ZIP symlink')
        if not i.is_dir(): entries[i.filename] = z.read(i)  # CRC checked by zipfile
zip_closed = z.fp is None
manifest = {n:ident(b) for n,b in sorted(entries.items())}
check(len(entries)==957 and sum(len(b) for b in entries.values())==11213090, 'ZIP count/bytes')
check(manifest == acq['files'], 'complete acquisition manifest')
check(acq['fileCount']==957 and acq['totalBytes']==11213090 and acq['status']=='complete', 'acquisition totals')
check((acq['run'],acq['attempt'],acq['job'],acq['artifact'],acq['head']) ==
      (42430741909,1,128578860306,13597407658,REV), 'acquisition identity')
extracted = {str(p.relative_to(INPUT/'artifact')):ident(read(p))
             for p in (INPUT/'artifact').rglob('*') if p.is_file()}
check(extracted==manifest, 'entire existing extraction equals ZIP')
artifact = next(a for a in artifacts if a['id']==13597407658)
check(artifact['digest']=='sha256:'+SHA and artifact['size_in_bytes']==1716883 and
      artifact['workflow_run']['head_sha']==REV and artifact['workflow_run']['id']==42430741909 and
      artifact['name']=='android-owner-host-'+REV, 'artifact API snapshot binding')
job = next(j for j in jobs if j['id']==128578860306)
check(job['name']=='android-owner-host' and job['run_id']==42430741909 and
      job['status']=='completed' and job['conclusion']=='success','job snapshot')
steps = {s['name']:s for s in job['steps']}
for name in ['Private Android owner orchestration on the JVM', 'Private Android renderer callback matrix on the JVM',
             'Android platform observations and observer host regressions','Preserve private Android owner host evidence']:
    check(steps[name]['status']=='completed' and steps[name]['conclusion']=='success','required step '+name)
check(steps['Show retained Android host failure diagnostics']['conclusion']=='skipped','diagnostic skip')
check([s['name'] for s in job['steps'] if s['conclusion']=='skipped']==['Show retained Android host failure diagnostics'], 'only diagnostic skipped')
for token in [REV,'Uploaded bytes 1716883','SHA256 digest of uploaded artifact zip is '+SHA,
              'Artifact ID 13597407658', '--closure A','--closure B','run-environment-platform-host.py']:
    check(token in log,'job log binding '+token)

def ej(lane,name): return json.loads(entries[lane+'/'+name])
lanes = ['android-owner-orchestration','android-owner-renderer','android-owner-environment']
paths = set(selection['sourceInputs']) | {'.github/workflows/verify.yml','cli/Sources/MixerBuild/AndroidSDKCompatibility.swift'}
for lane in lanes: paths.update(ej(lane,'source-map.json'))
# Read immutable owning blobs in one bounded, read-only batch; no lazy network fetch.
def blobs(names):
    names = sorted(names)
    b = git('cat-file','--batch',stdin=''.join(REV+':'+n+'\n' for n in names).encode())
    result = {}; pos = 0
    for n in names:
        end=b.index(b'\n',pos); header=b[pos:end].split(); pos=end+1
        check(len(header)==3 and header[1]==b'blob','owning Git blob '+n)
        size=int(header[2]); result[n]=b[pos:pos+size];pos+=size
        check(b[pos:pos+1]==b'\n','Git batch delimiter');pos+=1
    check(pos==len(b),'Git batch complete')
    return result
frozen = blobs(paths)
workflow = frozen['.github/workflows/verify.yml'].decode()
jobsource = workflow.split('  android-owner-host:\n',1)[1].split('\n  swift:',1)[0]
check('name: Show retained Android host failure diagnostics\n        if: failure()' in jobsource,
      'diagnostics intentionally conditional')
check('if: always()' in jobsource and 'name: android-owner-host-${{ github.sha }}' in jobsource,
      'artifact preservation and naming')
profile_source=frozen['cli/Sources/MixerBuild/AndroidSDKCompatibility.swift'].decode()
profile=json.loads(profile_source.split('Data(#"""',1)[1].split('"""#',1)[0])
check(profile['id']=='mixer.android-source-pair.9','pair9 profile')
check(len(profile['sdk_files'])==22 and len(profile['adapter_files'])==24,'SDK22 adapter24 counts')
profile_paths = {'sdk/'+n:v for n,v in profile['sdk_files'].items()}
profile_paths.update({('native/android/engine/' if n.startswith('Sources/') else 'native/android/')+n:v
                      for n,v in profile['adapter_files'].items()})
frozen.update(blobs(set(profile_paths)-set(frozen)))
for n, expected in profile_paths.items(): check(ident(frozen[n])==expected,'profile owning byte '+n)
def source_digest(files):
    return hashlib.sha256(''.join(n+'\0'+v['sha256']+'\n' for n,v in sorted(files.items())).encode()).hexdigest()
check(source_digest(profile['sdk_files'])==profile['sdk_compatibility_sha256'] and
      source_digest(profile['adapter_files'])==profile['adapter_compatibility_sha256'],'recomputed SDK/adapter digests')
check(profile['sdk_compatibility_sha256']=='bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0' and
      profile['adapter_compatibility_sha256']=='ee9414d3b68f9d66ba275c93339018e5eaebb161a7dc25d7056538c652305d89', 'R2 exact tuple')
canonical={n:ident(frozen[n]) for n in selection['sourceInputs']}
canonical_changes={n:{'isolatedR2':selection['sourceInputs'][n],'git96':v} for n,v in canonical.items() if v!=selection['sourceInputs'][n]}
check(len(canonical)==101,'canonical 101 inventory')
canonical_digest=source_digest(canonical)
check(canonical_digest==selection['inputDigest']=='a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca','recomputed canonical digest')
runner_tree=ast.parse(frozen['scripts/ci/check-android-generated-java.py'])
constants={n.targets[0].id:ast.literal_eval(n.value) for n in runner_tree.body if isinstance(n,ast.Assign)
           and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('POLICY','DRIVER')}
all_package_paths=git('ls-tree','-r','--name-only',REV,'cli','sdk','updates').decode().splitlines()
closed_paths={n for n in all_package_paths if any(n.startswith(pkg+'/Sources/') or
              (str(PurePosixPath(n).parent)==pkg and PurePosixPath(n).name.startswith('Package.')) for pkg in ('cli','sdk','updates'))}
closed_paths.update(['scripts/ci/check-android-generated-java.py','scripts/ci/check-android-binding.py',constants['POLICY'],constants['DRIVER']])
closed_paths.update(n for n in profile_paths if n.startswith('native/android/'))
check(closed_paths==set(canonical),'closed canonical Git inventory')
lane_results={}
all_tools=[]
for lane in lanes:
    sm=ej(lane,'source-map.json'); receipt=ej(lane,'receipt.json'); cs=ej(lane,'commands.json')
    check(receipt['status']=='passed-host-only' and receipt['source_stable'] is True, 'receipt outcome '+lane)
    for n,v in sm.items():
        check(ident(entries[lane+'/inputs/'+n])==v==ident(frozen[n]),'frozen source '+lane+'/'+n)
    check({n.split('/inputs/',1)[1] for n in entries if n.startswith(lane+'/inputs/')}==set(sm),'closed source inventory')
    cm=ej(lane,'classes.json' if lane.endswith('environment') else 'class-map.json')
    retained_classes={n.split('/classes/',1)[1] for n in entries if n.startswith(lane+'/classes/')}
    check(retained_classes==(set() if lane.endswith('environment') else set(cm)), 'closed retained class inventory')
    if lane.endswith('environment'):
        check(len(cm)==178 and all(set(v)=={'bytes','sha256'} and len(v['sha256'])==64 and v['bytes']>0 for v in cm.values()),'environment class manifest shape')
    for n in retained_classes:
        v=cm[n]
        b=entries[lane+'/classes/'+n]
        check(ident(b)==v and b[:4]==b'\xca\xfe\xba\xbe' and struct.unpack('>H',b[6:8])[0]==61, 'class identity/version '+n)
    for c in cs:
        check(c['exit']==0 and c['child_reaped'] is True and c['timeout'] is False and
              c['output_limit_exceeded'] is False,'command outcome '+lane+'/'+c['label'])
        for stream in ['stdout','stderr']:
            check(ident(entries[lane+'/'+c['label']+'.'+stream])==c[stream], 'command stream '+lane+'/'+c['label'])
    cc=next(c for c in cs if c['label']=='compile')['argv']
    check(cc[1:7]==['--release','17','-Xlint:all','-Werror','-proc:none','-classpath'] and
          cc[8]=='-sourcepath' and cc[7]==cc[9] and cc[10]=='-d', 'strict isolated compilation')
    prefix='/home/runner/work/_temp/'+lane+'/inputs/'
    selected=[s.removeprefix(prefix) for s in cc[12:]]
    check(len(selected)==len(set(selected)) and all(prefix+s in cc for s in selected) and
          set(selected)<=set(sm), 'explicit frozen compile inputs')
    if lane.endswith('environment'):
        closure=ej(lane,'source-closure.json');check(selected==closure['sources'],'environment roster')
        check(set(sm)==set(closure['sources']+closure['auxiliary']), 'environment closed inputs')
        check(receipt['context_revision_is_inherited_not_live_git'] is True,'inherited revision labeled')
        check(receipt['cleanup']=={'owned_scratch_removed':True,'owned_children_reaped':True,'native_or_capture_instances_created':False},'environment cleanup receipt')
    else:
        roster=ej(lane,'roster.json')
        expected=roster['actual_production_sources']+['native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java']
        expected += [s['source'] for s in roster['substitutes']]+roster['test_support_sources']+[roster['test_source']]
        check(selected==expected,'exact A/B roster')
        check(receipt['revision']==REV and entries[lane+'/revision.stdout'].decode().strip()==REV,'live CI revision')
        check('--skip-matrix' not in receipt['argv'],'full matrix requested')
        check(receipt['cleanup']=={'scratch_removed':True,'children_reaped':True,'native_instances_created':False},'A/B cleanup receipt')
    check(entries[lane+'/compile.stdout']==entries[lane+'/compile.stderr']==b'', 'no compiler diagnostics')
    host_labels=['NativeEnvironmentV2ObserverHostTests','NativeEnvironmentPlatformV2HostTests'] if lane.endswith('environment') else ['host']
    for label in host_labels:
        host=next(c for c in cs if c['label']==label)
        expected_test=label if lane.endswith('environment') else ('NativeOwnerV2ConcreteHostTests' if lane.endswith('renderer') else 'NativeOwnerV2HostTests')
        check(host['argv'][1:4]==['-ea','-Xmx128m' if lane.endswith('environment') else '-Xmx256m','-cp'] and
              host['argv'][4]==cc[11] and host['argv'][5]=='dev.mixer.android.'+expected_test,'host runtime argv/compiled classpath')
        check(host.get('elapsed',host.get('seconds')) < (300 if lane.endswith('renderer') else 60),'retained host command bound')
    for c in cs:
        if Path(c['argv'][0]).name in ['java','javac','javap']:
            check(c['argv'][0] in receipt['tools'],'tool argv bound to receipt')
    all_tools.append(receipt['tools'])
    check('17.0.21' in entries[lane+'/java-version.stderr'].decode() and
          entries[lane+'/javac-version.stdout']==b'javac 17.0.21\n','actual tool versions')
    lane_results[lane]={'inputCount':len(sm),'compiledSources':len(selected),'classes':len(cm),
                        'retainedClassBytes':len(retained_classes),'commands':len(cs),'cleanupClaim':receipt['cleanup'],'receipt':ident(entries[lane+'/receipt.json'])}
check(all(t==all_tools[0] for t in all_tools),'same tool identities across closures')
expected_outputs={
 'android-owner-orchestration/host.stdout':'PASS actual owner/core/coordinator/observer closure A cases=231 assertions=1250; renderer leaf only, native runtime pending\n',
 'android-owner-renderer/host.stdout':'PASS concrete actual16 host checks=14692; platform/JNI leaves, native runtime pending\n',
 'android-owner-environment/NativeEnvironmentV2ObserverHostTests.stdout':'PASS 190 production Observer host cases; faulting Android leaves only; native runtime pending\n',
 'android-owner-environment/NativeEnvironmentPlatformV2HostTests.stdout':'PASS actual platform/Observer host cases=134 assertions=699; SDK28..36 finite leaves only; native linkage/runtime pending\n'}
for n,s in expected_outputs.items(): check(entries[n].decode()==s and entries[n.replace('.stdout','.stderr')]==b'','actual suite output '+n)

class Reader:
    def __init__(self,b): self.b=b;self.p=0
    def take(self,n):
        b=self.b[self.p:self.p+n];self.p+=n
        if len(b)!=n: raise ValueError('truncated class')
        return b
    def u1(self): return self.take(1)[0]
    def u2(self): return struct.unpack('>H',self.take(2))[0]
    def u4(self): return struct.unpack('>I',self.take(4))[0]
parsed={}
def instruction_boundaries(code):
    boundaries=set();p=0
    fixed={16:2,17:3,18:2,19:3,20:3,132:3,169:2,178:3,179:3,180:3,181:3,
           182:3,183:3,184:3,185:5,186:5,187:3,188:2,189:3,192:3,193:3,197:4,198:3,199:3,200:5,201:5}
    fixed.update({i:2 for i in list(range(21,26))+list(range(54,59))})
    fixed.update({i:3 for i in range(153,169)})
    while p<len(code):
        boundaries.add(p);op=code[p]
        if op in (170,171):
            q=(p+4)&~3
            if op==170:
                low,high=struct.unpack('>ii',code[q+4:q+12]);size=q+12+4*(high-low+1)-p
                check(high>=low,'tableswitch bounds')
            else:
                count=struct.unpack('>i',code[q+4:q+8])[0];size=q+8+8*count-p
                check(count>=0,'lookupswitch bounds')
        elif op==196:size=6 if code[p+1]==132 else 4
        else:size=fixed.get(op,1)
        check(0<=op<=201 and size>0 and p+size<=len(code),'instruction structure')
        p+=size
    check(p==len(code),'instruction stream end')
    return boundaries
def parse_class(name):
    r=Reader(entries['android-owner-renderer/classes/'+name.replace('.','/')+'.class'])
    check(r.u4()==0xcafebabe,'class magic');r.u2();check(r.u2()==61,'class version')
    pool=[None];count=r.u2();i=1
    while i<count:
        tag=r.u1()
        if tag==1: v=r.take(r.u2()).decode('utf-8',errors='replace')
        elif tag in (3,4):v=r.take(4)
        elif tag in (5,6):v=r.take(8)
        elif tag in (7,8,16,19,20):v=r.u2()
        elif tag in (9,10,11,12,17,18):v=(r.u2(),r.u2())
        elif tag==15:v=(r.u1(),r.u2())
        else:raise ValueError('class constant '+str(tag))
        pool.append((tag,v));i+=1
        if tag in (5,6):pool.append(None);i+=1
    utf=lambda i:pool[i][1]
    def attrs(reader):return [(utf(reader.u2()),reader.take(reader.u4())) for _ in range(reader.u2())]
    r.take(6);r.take(2*r.u2())
    for _ in range(r.u2()):r.take(6);attrs(r)
    methods={}
    for _ in range(r.u2()):
        r.u2();method,desc=utf(r.u2()),utf(r.u2())
        for n,b in attrs(r):
            if n!='Code':continue
            c=Reader(b);c.take(4);code=c.take(c.u4());c.take(8*c.u2());lines=[]
            for an,ab in attrs(c):
                if an=='LineNumberTable':
                    lr=Reader(ab);lines=[(lr.u2(),lr.u2()) for _ in range(lr.u2())]
            methods[(method,desc)]=(code,sorted(lines),instruction_boundaries(code))
    return methods,pool
def resolve(f):
    name=f['class']
    if name not in parsed:parsed[name]=parse_class(name)
    methods,pool=parsed[name];code,lines,boundaries=methods[(f['method'],f['descriptor'])];bci=f['bytecodeIndex']
    check(bci in boundaries and code[bci] in (182,183,184,185,186),'actual invocation BCI at instruction boundary')
    check(next(l for s,l in reversed(lines) if s<=bci)==f['line'],'compiled source line')
    constant=pool[struct.unpack('>H',code[bci+1:bci+3])[0]]
    check(constant[0] in (10,11,18),'invocation constant')
    oi,nt=constant[1];cn,cd=pool[nt][1]
    return {'name':pool[cn][1],'descriptor':pool[cd][1],
            'owner':None if constant[0]==18 else pool[pool[oi][1]][1]}
mapping=json.loads(frozen['native/android/tests/private-owner-barrier-map.json'])
records={r['baseline']:r for r in mapping['records']}
matrix=ej('android-owner-renderer','barrier-cases.json');rows=matrix['cases']
required={(r['baseline'],k) for r in records.values() for k in r['required_cases']}
check(len(records)==189 and len(rows)==len(required)==1323 and
      {(r['site'],r['case']) for r in rows}==required and matrix['missing']==[] and
      matrix['baselineSites']==184 and matrix['introducedSites']==5,'full B Cartesian matrix')
resolved=[];callers={}
for r in records.values():
    c=r['candidates'][0];text=frozen[r['source']].decode();offset=sum(len(l) for l in text.splitlines(keepends=True)[:c['line']-1])+c['column']-1
    check(len(r['candidates'])==1 and text[offset:].startswith(c['text']),'source invocation anchor '+r['baseline'])
for row in rows:
    rec=records[row['site']];check(row['hit'] is True and len(row['selectedFrames'])==1,'case actual hit')
    f=row['selectedFrames'][0];base='dev.mixer.android.'+rec['class']
    check(f['line']==rec['candidates'][0]['line'] and (f['class']==base or f['class'].startswith(base+'$')),'source/frame')
    if rec.get('caller_frame'):check(f['method'].startswith(rec['caller_method_prefix']),'lambda selector')
    key=f"{f['class']}#{f['method']}{f['descriptor']}@{f['bytecodeIndex']}"
    check(key==row['exactCaller'],'serialized exact frame');callers.setdefault(row['site'],set()).add(key)
    phase='entry' if row['case']=='clean' or row['case'].endswith('entry') else 'beforeReturn'
    check(row['nativePhase']==phase and row['boundaryMode']==rec['boundary']['mode'] and
          row['boundaryEquivalence']==rec['boundary']['equivalence'],'phase/boundary')
    suffix=rec['boundary']['entry_native_suffix' if phase=='entry' else 'return_native_suffix']
    check(suffix=='*' or row['nativeMethod']==suffix or row['nativeMethod'].endswith('.'+suffix),'native method')
    target=resolve(f)
    if rec['source'].endswith('/NativeEditorConnectionV2.java'):
        check(target['owner']=='android/view/inputmethod/InputConnection' and
              target['name']==rec['candidates'][0]['text'].split('target.',1)[1].split('(',1)[0], 'actual IME target')
    if row['case']=='clean':resolved.append({'site':row['site'],'exactCaller':key,'target':target})
check(all(len(c)==1 for c in callers.values()) and len({next(iter(c)) for c in callers.values()})==189,'189 distinct bindings')
helpers=[json.loads(l) for l in entries['android-owner-renderer/helper-boundaries.jsonl'].splitlines()]
expected_helpers={r['baseline'] for r in records.values() if any(t in r['boundary']['mode'] for t in ('helper','constructor'))}
check(len(helpers)==len(expected_helpers)==15 and {h['site'] for h in helpers}==expected_helpers,'15 helper boundaries')
secondary=[]
for h in helpers:
    b=records[h['site']]['boundary'];clean=next(r for r in rows if r['site']==h['site'] and r['case']=='clean')
    check(h['helperNativeSequence']==clean['helperNativeSequence'] and h['exactCaller']==clean['exactCaller'],'retained helper equality')
    check(h['finalAnchorMatches'] is True and h['helperSequenceEnd']=='original invocation frame/operation left','helper observed end')
    last=h['helperNativeSequence'][-1]
    check(last['phase']=='beforeReturn' and last['nativeMethod']==b['return_native_suffix'],'helper final event')
    for actual,expected in [('receiverId','return_receiver_id'),('receiverClass','return_receiver_class')]:
        check(b[expected] is None or last[actual]==b[expected],'helper receiver')
    check(any(f"{f['class']}#{f['method']}{f['descriptor']}@{f['bytecodeIndex']}"==h['exactCaller'] for f in last['productionFrames']),'helper original frame')
    if b['return_frame_line'] is not None:
        fs=[f for f in last['productionFrames'] if f['class']=='dev.mixer.android.NativeAppearanceViewsV2' and f['line']==b['return_frame_line']]
        check(bool(fs),'secondary source anchor')
        for f in fs:resolve(f)
        secondary.append({'site':h['site'],'line':b['return_frame_line'],'event':last['nativeMethod']})
check(len(secondary)==2 and {s['line'] for s in secondary}=={521,719},'secondary helper anchors')
# Independent negative controls operate only on data, never on executable subjects.
check({(r['site'],r['case']) for r in rows[:-1]}!=required,'omitted row rejected')
check(not any(f['line']==826 and f['class']=='dev.mixer.android.NativeAppearanceViewsV2'
              for h in helpers if h['site']=='NativeRenderer:L238:C9:1'
              for f in h['helperNativeSequence'][-1]['productionFrames']),'obsolete helper anchor rejected')
check(ident(read(ARCHIVE))=={'bytes':1716883,'sha256':SHA},'retained ZIP unchanged')
for n,v in list(inputs.items()):check(ident(Path(n).read_bytes())==v,'input stability '+n)
save('archive-files.json',manifest)
save('source-bindings.json',{n:ident(b) for n,b in sorted(frozen.items())})
save('resolved-bytecode-anchors.json',resolved)
save('canonical-comparison.json',{'inventory':canonical,'digest':canonical_digest,'closedGitInventory':True,'isolatedR2Digest':selection['inputDigest'],'differences':canonical_changes})
save('inputs.json',inputs)
save('git-commands.json',commands)
save('audit-result.json',{'verdict':'ACCEPT','scope':'exact ordinary Android host CI artifact only; no GA/native or six-consumer qualification',
 'finishedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsedSeconds':round(time.monotonic()-started,3),
 'checks':checks,'revision':REV,'tree':tree,'python':sys.version,'git':git_version,'auditScript':ident(Path(__file__).read_bytes()),
 'archive':{'path':str(ARCHIVE),**ident(ARCHIVE.read_bytes()),'files':957,'uncompressedBytes':11213090,'readerClosed':zip_closed},
 'run':42430741909,'attempt':1,'job':128578860306,'artifact':13597407658,'laneResults':lane_results,
 'outputs':{n:{'text':s,**ident(entries[n])} for n,s in expected_outputs.items()},'toolClaims':all_tools[0],
 'canonicalInputCount':101,'canonicalDigest':canonical_digest,'canonicalChangedPaths':list(canonical_changes),'sourcePair':profile['id'],
 'sdkFiles':22,'adapterFiles':24,'sdkSHA256':profile['sdk_compatibility_sha256'],'adapterSHA256':profile['adapter_compatibility_sha256'],
 'matrix':{'checks':14692,'cases':1323,'sites':189,'helperBoundaries':15,'secondary':secondary,'caseDistribution':dict(collections.Counter(r['case'] for r in rows))},
 'custodyLimits':['CI direct-child reaping and scratch removal are retained source-bound producer claims, not reviewer process observations.',
 'No process-group absence, escaped descendant containment, provider cleanup or native runtime is established.',
 'Acquisition urllib/ZIP closure is an acquisition claim; only this audit ZIP reader closure was directly observed.',
 'Historical environment context revision is inherited; exact Git96 source bytes and job checkout establish the current binding.',
 'Environment retains 178 class identities and hash-bound javap reports, but no class bytes; those identities cannot be independently rehashed.',
 'Linux CI tool hashes are producer claims bound to argv and version outputs; this Mac audit did not independently rehash those unavailable binaries.',
 'No network authentication or fresh GitHub status lookup; verdict binds supplied API/job/log snapshots and retained ZIP.'],
 'actionsDenied':['compiler','JVM','D8','Swift','native','UI','capture','network','process probes/signals','children/delegation','commit/push','tracker edits','GA'],
 'holds':'Historical Binder and controller-admission preparation failures, all held groups/phones/v5/frozen lanes untouched.',
 'writesOnly':str(OUT),'newExtraction':False})
print(json.dumps({'verdict':'ACCEPT','checks':checks,'lanes':lane_results,'canonicalDifferences':list(canonical_changes),'zipReaderClosed':zip_closed,'seconds':round(time.monotonic()-started,3)}))
