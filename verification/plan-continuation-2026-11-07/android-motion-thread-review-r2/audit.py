"""Independent read-only candidate/R1 audit; writes only this review directory."""
import collections, datetime, hashlib, json, subprocess, sys
from pathlib import Path
OUT = Path(__file__).resolve().parent
PARENT = OUT.parents[2]
CAND = Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-7764d3ec')
R1 = Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-9ff4db6c')
REL = Path('verification/plan-continuation-2026-11-07')
E = CAND/REL/'android-motion-thread-fix-r2'
OLD = R1/REL/'android-motion-thread-fix'
def read(p): return json.loads(p.read_text())
def ident(p):
    b=p.read_bytes(); return {'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}
def digest(m): return hashlib.sha256(''.join(p+'\0'+v['sha256']+'\n' for p,v in sorted(m.items())).encode()).hexdigest()
def save(name,v): (OUT/name).write_text(json.dumps(v,indent=2)+'\n')
def check(ok,what):
    if not ok: raise RuntimeError(what)
def method(text,name):
    pos=text.index(name+'('); start=text.index('{',pos); depth=1; end=start+1
    while depth:
        depth += (text[end]=='{') - (text[end]=='}'); end+=1
    return text[start:end]
def main():
    stage=sys.argv[1] if len(sys.argv)>1 else 'before'
    report={'stage':stage,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version}
    for label,root in [('candidate',CAND),('parent',PARENT),('r1',R1)]:
        report[label+'Revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True,timeout=10).strip()
    final=read(E/'final-source-map.json'); canonical=read(E/'canonical-source-inputs-final.json')
    allpaths=set(final)|set(canonical['files'])
    for p,v in final.items(): check(ident(CAND/p)==v==ident(E/'final-inputs'/p),'final source '+p)
    report['finalFiles']=len(final)
    check(len(canonical['files'])==canonical['count']==101,'canonical count')
    check(digest(canonical['files'])==canonical['sha256'],'canonical digest')
    for p,v in canonical['files'].items(): check(ident(CAND/p)==v,'canonical source '+p)
    report['canonicalDigest']=canonical['sha256']
    manifest=read(E/'manifest.json')
    for p,v in manifest.items(): check(ident(E/p)==v,'candidate manifest '+p)
    report['candidateManifestFiles']=len(manifest)
    report['executionClosures']={}
    for name,mp,base in [('environment-final',E/'environment-final/source-map.json',E/'environment-final/inputs'),('full-B',E/'full-B/source-map.json',E/'full-B/inputs'),('instrumentation',E/'instrumentation/source-map.json',E/'instrumentation/inputs'),('targeted',E/'targeted-source-map.json',E/'targeted-inputs')]:
        mapping=read(mp); allpaths.update(mapping)
        for p,v in mapping.items(): check(ident(CAND/p)==v==ident(base/p),name+' input '+p)
        report['executionClosures'][name]=len(mapping)
    oldmanifest=read(OLD/'manifest.json')
    for p,v in oldmanifest.items(): check(ident(OLD/p)==v,'R1 manifest '+p)
    report['r1ManifestFiles']=len(oldmanifest)
    oldcanonical=read(E/'r1-canonical-source-inputs-final.json')['files']
    for p,v in oldcanonical.items(): check(ident(R1/p)==v,'R1 source '+p)
    report['canonicalChangesFromR1']=[p for p,v in canonical['files'].items() if oldcanonical[p]!=v]
    policy=(CAND/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
    profile=json.loads(policy.split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
    check(profile==read(E/'selected-pair9-r2.json'),'selected profile literal')
    for kind,count in [('sdk',22),('adapter',24)]:
        m=profile[kind+'_files']; check(len(m)==count,kind+' count')
        check(digest(m)==profile[kind+'_compatibility_sha256'],kind+' projection')
        for p,v in m.items():
            source=CAND/('sdk/'+p if kind=='sdk' else 'native/android/'+('engine/' if p.startswith('Sources/') else '')+p)
            check(ident(source)==v,kind+' identity '+p)
    report['profile']={k:profile[k] for k in ['id','sdk_compatibility_sha256','adapter_compatibility_sha256']}
    # Derive the canonical inventory independently, rather than trusting its recorded count.
    paths={'scripts/ci/check-android-generated-java.py','scripts/ci/check-android-binding.py','cli/Sources/MixerBuild/AndroidSDKCompatibility.swift','cli/Sources/MixerBuild/Resources/android-build.py'}
    for package in ['cli','sdk','updates']:
        paths.update(str(p.relative_to(CAND)) for p in (CAND/package/'Sources').rglob('*') if p.is_file())
        paths.update(str(p.relative_to(CAND)) for p in (CAND/package).glob('Package.*') if p.is_file())
    paths.update('native/android/'+('engine/' if p.startswith('Sources/') else '')+p for p in profile['adapter_files'])
    check(paths==set(canonical['files']),'canonical inventory exact')
    matrix=read(E/'full-B/barrier-cases.json'); cases=matrix['cases']
    check(len(cases)==1323 and not matrix['missing'],'full B matrix coverage')
    counts=collections.Counter(c['site'] for c in cases)
    check(len(counts)==189 and set(counts.values())=={7},'seven cases per 189 sites')
    check(all(c['hit'] for c in cases),'matrix missing hit')
    report['fullB']={'cases':len(cases),'sites':len(counts),'casesPerSite':7,'missing':matrix['missing'],'output':(E/'full-B/host.stdout').read_text().strip()}
    check(matrix==read(OLD/'concrete-B-1/barrier-cases.json'),'R1/R2 full matrix records differ')
    report['fullB']['identicalR1MatrixRecords']=True
    check((CAND/'cli/Sources/MixerBuild/Resources/android-build.py').read_bytes()==(R1/'cli/Sources/MixerBuild/Resources/android-build.py').read_bytes(),'R1/R2 driver templates differ')
    oldpolicy=(R1/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
    oldprofile=json.loads(oldpolicy.split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
    reconstructed=json.loads(json.dumps(profile))
    reconstructed['adapter_compatibility_sha256']='b8aad7b23e2917176d4ab1da2912e2acc098265609ffd40741283607496225b3'
    reconstructed['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java']={'bytes':17696,'sha256':'8396a3f5b923a40f3fd1a9121b8d5feaddd88583675e6596c1812c9c76520e1a'}
    check(reconstructed==oldprofile,'exact R1 stale driver policy reconstruction')
    report['exactR1DriverPolicyAndTemplateVerified']=True
    checks=[]
    for folder in ['environment-final','full-B','instrumentation']:
        commands=read(E/folder/'commands.json')
        for c in commands:
            label=c.get('label',c.get('name'))
            check(c['exit']==0,folder+' command exit '+label)
            for suffix in ['stdout','stderr']:
                check(ident(E/folder/(label+'.'+suffix))==c[suffix],folder+' output '+label)
        checks.append({'folder':folder,'commands':len(commands)})
    for name in ['python-admission','python-admission-O','swift-admission','instrumentation-compile','full-B','targeted','environment-final']:
        c=read(E/(name+'.json')); check(c['exit']==0 and c['boundExceeded'] is None,name+' result')
        for suffix in ['stdout','stderr']: check(ident(E/(name+'.'+suffix))==c[suffix],name+' output')
    report['receiptChecks']=checks
    instr='native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java'
    current=(CAND/instr).read_text(); previous=(R1/instr).read_text()
    report['identicalNativeMethods']={}
    for name in ['onStart','awaitPresentation','motionWait','exerciseMotionCallback']:
        # Match declaration for methods also called earlier in the source.
        import re
        def body(text):
            hit=re.search(r'(?:public|private)\s+(?:final\s+)?(?:void|boolean)\s+'+name+r'\(',text)
            check(hit is not None,'method declaration '+name)
            return method(text[hit.start():],name)
        a=body(current); b=body(previous); check(a==b,'preserved method '+name)
        report['identicalNativeMethods'][name]=hashlib.sha256(a.encode()).hexdigest()
    # R2 touched only the two exchanges/comments in the product adapter.
    platform='native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'
    old=(R1/platform).read_text(); new=(CAND/platform).read_text()
    check(new[new.index('        static Observed<Float> animator()'):]==old[old.index('        static Observed<Float> animator()'):],'getter/lifecycle/API tail changed')
    for p in ['native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java','native/android/tests/private-owner-barrier-map.json','native/android/tests/NativeOwnerV2ConcreteHostTests.java']:
        check((CAND/p).read_bytes()==(R1/p).read_bytes(),'unchanged R1 boundary '+p)
    candidate_map={p:ident(CAND/p) for p in sorted(allpaths)}
    rootpaths=set(final)|{'AGENTS.md','PLAN.md','STATUS.md','work-graph.json','gates/ga.json','verification/plan-continuation-2026-11-07/generated-java-ci-integration/bootstrap.py','verification/plan-continuation-2026-11-07/generated-java-ci-integration/test_bootstrap.py'}
    rootmap={p:ident(PARENT/p) for p in sorted(rootpaths) if (PARENT/p).is_file()}
    snapshot={'candidate':candidate_map,'candidateManifest':ident(E/'manifest.json'),'r1Manifest':ident(OLD/'manifest.json'),'parentProtected':rootmap}
    save('sources-'+stage+'.json',snapshot)
    if stage=='after':
        before=read(OUT/'sources-before.json')
        check(snapshot['candidate']==before['candidate'],'candidate changed during review')
        check(snapshot['candidateManifest']==before['candidateManifest'],'candidate evidence changed')
        check(snapshot['r1Manifest']==before['r1Manifest'],'R1 evidence changed')
        report['parentConcurrentChanges']=[p for p,v in rootmap.items() if before['parentProtected'].get(p)!=v]
    report['status']='PASS'; save('audit-'+stage+'.json',report)
    print(json.dumps({k:report[k] for k in ['stage','status','finalFiles','canonicalDigest','candidateManifestFiles','r1ManifestFiles','executionClosures']}))
if __name__=='__main__':main()
