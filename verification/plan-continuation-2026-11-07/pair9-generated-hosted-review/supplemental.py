#!/usr/bin/env python3
"""Data-only exact command/source supplement; imports only this review's inert helpers."""
import importlib.util
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('review_helpers', OUT/'audit.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
js, check, ident = a.js, a.check, a.ident
r = js(a.RUN/'receipt.json'); b = js(a.REMOTE/'bootstrap-receipt.json')
c = js(a.RUN/'commands/commands.json'); by = {x['label']:x for x in c}
bc = js(a.REMOTE/'bootstrap-commands/commands.json'); bby = {x['label']:x for x in bc}
t = r['official_toolchain']; paths = r['selected_paths']
scratch = Path(r['cleanup']['owned_scratch_path']); owned=Path(b['cleanup']['owned_path'])
python='/usr/local/bin/python3'
expected={'revision':['git','rev-parse','HEAD'],'git-tree':['git','rev-parse','HEAD^{tree}'],
          'd8-version':[t['tools']['d8']['path'],'--version']}
for label in ['official-inspect','official-inspect-postflight']:
    expected[label]=[python,'-B',str(a.ROOT/'cli/Sources/MixerBuild/Resources/android-build.py'),'inspect']
for label in ['javap-version','javap-version-postflight']:
    expected[label]=[r['javap_tool']['path'],'-version']
for mode in ['debug','release']:
    build=scratch/('producer-'+mode)
    flags=[paths['swift'],'build','--package-path',str(a.ROOT/'cli'),'--scratch-path',str(build),'--disable-automatic-resolution','-j','2','-c',mode]
    expected[mode+'-producer-build']=flags+['--product','mixer']
    expected[mode+'-producer-bin']=flags+['--show-bin-path']
    cli=str(Path(a.read(by[mode+'-producer-bin']['logs']['stdout']['path']).decode().strip())/'mixer')
    for phase in ['dependency','post-dependency']:
        for name in ['swift-asn1','swift-crypto']:
            prefix=mode+'-'+phase+'-'+name;git=['git','-C',str(build/'checkouts'/name)]
            expected[prefix+'-revision']=git+['rev-parse','HEAD']
            expected[prefix+'-status']=git+['status','--porcelain','--untracked-files=all']
    original=str(scratch/mode/'original')
    expected[mode+'-create']=[cli,'create','GeneratedJavaApp','--platform','android','--directory',original,'--application','dev.mixer.generatedjava','--sdk-path',str(a.ROOT/'sdk'),'--android-adapter-path',str(a.ROOT/'native/android')]
    expected[mode+'-export']=[cli,'export',str(scratch/mode/'exported'),'--directory',original]
    for form in ['original','relocated','exported']:
        label=mode+'-'+form; dest=a.RUN/label; rec=js(dest/'receipt.json')
        jar=paths['android_sdk']+'/platforms/android-37.0/android.jar'
        sources=[str(scratch/mode/form/v) for v in sorted(rec['sources'])]
        classes=[str(dest/'classes'/v) for v in sorted(rec['classes'])]
        expected[label+'-javac']=[t['tools']['javac']['path'],'--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath','','-classpath',jar,'-d',str(dest/'classes')]+sources
        expected[label+'-javap-members']=[r['javap_tool']['path'],'-v','-p','-c','-s']+classes
        expected[label+'-d8']=[t['tools']['d8']['path'],'--min-api','28','--lib',jar,'--output',str(dest/'dex')]+classes
        expected[label+'-dexdump']=[t['tools']['dexdump']['path'],str(dest/'dex/classes.dex')]
        inv=js(dest/'consumer-inventory.json');dirs=js(dest/'consumer-directories.json')
        required={str(parent) for path in inv for parent in Path(path).parents if str(parent)!='.'}
        check(set(dirs)==required|({'Resources'} if form!='exported' else set()),label+': exact directory topology')
    for case in ['sdk','adapter','descriptor','extra-java','profile','missing-lock']:
        root=scratch/mode/'tamper'/case
        expected[mode+'-tamper-'+case]=[cli,'build','--platform','android','--directory',str(root)]
        expected[mode+'-driver-tamper-'+case]=[python,'-B',str(root/'Generated/MixerAndroid/android-build.py'),'build',str(root)]
        outcome=next(x for x in r['tamper'][mode] if x['case']==case)
        diagnostic='android.sdk-profile-mismatch' if case=='profile' else 'mixer.lock' if case=='missing-lock' else 'Android SDK source compatibility rejected'
        check(diagnostic in outcome['driver_refusal'],mode+'-'+case+': specific driver rejection')
check(set(expected)==set(by) and len(expected)==79,'Independently constructed exact map covers all 79 integration commands')
for label,argv in expected.items():
    check(by[label]['argv']==argv and by[label]['cwd']==str(a.ROOT),label+': entire argv and cwd')
# The main audit covers all download/trust/extract/setup arguments; cover the remaining bootstrap commands here.
be={'revision':expected['revision'],'git-tree':expected['git-tree'],
    'curl-version':['/usr/bin/curl','--version'],'tar-version':['/usr/bin/tar','--version'],
    'official-inspect':expected['official-inspect']}
for label,argv in be.items():check(bby[label]['argv']==argv,label+': exact bootstrap argv')
for x in bc:
    want=paths['android_artifact'] if x['label']=='official-sdk-setup' else str(a.ROOT)
    check(x['cwd']==want,x['label']+': exact bootstrap cwd')
check(b['argv']==r['argv']==['verification/plan-continuation-2026-11-07/generated-java-ci-integration/bootstrap.py','--output',str(a.REMOTE),'--execute'],'Actual bootstrap argv shared by in-process runner')
equiv=[python,'-B',str(a.ROOT/'scripts/ci/check-android-generated-java.py')]
for name in ['swift','swift_sdks','android_artifact','jdk','android_sdk']:equiv+=['--'+name.replace('_','-'),paths[name]]
equiv+=['--output',str(a.RUN),'--execute-toolchains']
check(b['integration_argv_equivalent']==equiv,'Equivalent integration argv is correctly labelled: in-process call, not an extra subprocess receipt')
check(set(t['tools'])=={'python','swift','clang','readelf','nm','java','javac','d8','aapt2','zipalign','dexdump'},'All eleven canonical tool identities retained')
check(set(t['metadata'])=={'ndk','platform','build_tools','jdk','swift_sdk','swift_toolset'},'All six metadata identities retained')
check(t['tools']['python']['path']=='/usr/local/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14' and t['python_version']==r['python']==b['python'],'Recorded resolved Python and reported versions agree; no current-host resolution')
check(t['tools']['swift']['path']==paths['swift'] and t['tools']['javac']['path']==paths['jdk']+'/bin/javac' and t['sdk_search_path']==paths['swift_sdks'],'Inspection and explicit selected tool paths agree')
check(t['javac_version']=='javac 25.0.4.1' and r['javap_tool']['version']=='25.0.4.1' and 'Swift version 6.3.3 ' in t['swift_version'],'Actual compiler version scope')
check(set(b['bootstrap_system_tools'])=={'/usr/bin/curl','/usr/sbin/pkgutil','/usr/bin/tar','/usr/bin/ditto','/bin/bash'} and all(x['bytes']>0 and len(x['sha256'])==64 for x in b['bootstrap_system_tools'].values()),'Five bootstrap system-tool historical identities')
check(sum('-tamper-' in x['label'] for x in c)==24 and sum(len(x) for x in r['tamper'].values())==12,'12 tamper case/configurations, 24 actual invocations')
check(all(x['signal']['outcome']=='already-absent' for x in c+bc),'Every recorded cleanup signal found its owned group already absent')
jobs=js(a.ART.parent/'jobs.json')['jobs']
check(len(jobs)==7 and all(x['run_id']==42430741909 and x['status']=='completed' and x['conclusion']=='success' for x in jobs),'Captured metadata: all seven run jobs successful, other jobs not artifact-qualified here')
# Retain exact owning code, never import or execute it.
extra=['cli/Sources/MixerBuild/Resources/android-build.py','cli/Sources/MixerBuild/AndroidSDKCompatibility.swift','cli/Sources/MixerBuild/ProjectGenerator.swift','cli/Sources/MixerBuild/AndroidProject.swift','scripts/ci/check-android-binding.py']
for path in extra:
    data=a.read(a.ROOT/path);target=OUT/'frozen'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
old='25ac442c5213326b3601456a5fd62898f152111f'
diff_paths=['verification/plan-continuation-2026-11-07/generated-java-ci-integration/bootstrap.py','verification/plan-continuation-2026-11-07/generated-java-ci-integration/test_bootstrap.py','verification/plan-continuation-2026-11-07/generated-java-ci-integration/test_sparse_checkout.py','scripts/ci/check-android-generated-java.py','.github/workflows/verify.yml']
(OUT/'frozen-owner-diff.patch').write_bytes(a.git('diff',old,a.REV,'--',*diff_paths))
main=js(OUT/'audit.json');check(main['verdict']=='ACCEPT','Main actual-data audit accepted')
check(a.inventory(a.ART)==js(OUT/'artifact-inventory.json'),'Entire capture still unchanged at supplemental postflight')
check({p:ident(a.ROOT/p) for p in r['source_inputs']}==r['source_inputs'],'All101 frozen sources unchanged at supplemental postflight')
report={'schema':1,'verdict':'ACCEPT','finished_utc':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve())],'script':ident(__file__),'checks':a.CHECKS,'git_calls':a.GIT_CALLS,'read_manifest':a.MANIFEST,'audit':ident(OUT/'audit.json'),'exact_integration_command_count':len(expected),'bootstrap_command_count':len(bc),'all_job_metadata':[{'id':x['id'],'name':x['name'],'conclusion':x['conclusion']} for x in jobs],'own_reader_closure':'Python Path.read_bytes and read_text close their own readers; main audit uses ZIP context manager and checks fp is None. Git subprocess.run pipes complete before return. No network readers created. Provider-internal disposal unobserved.','custody_scope':'All92 recorded outer commands; nested compiler/version processes rely on enclosing owned-group records and frozen runner. No per-grandchild reap, escaped-descendant containment, current process state or whole-worker disposal is claimed.','source_inspection':'Inspected frozen trust parser, disk/source admission, bounded HTTPS downloads, official full distribution hashing, exact two producer builds, export and move-before-relocation, tamper changes with recomputed generic locks, source/Apple/tools/javap postflight, failure retention and success cleanup. No product source executed.','nonblocking_notes':['Bootstrap signature policy unchanged from pair8; pinned source digest and pair name updated in frozen source.','Original/relocated keep source-created empty Resources directory, export contains only file parents.','Two static bootstrap proposal annotations are stale; actual completed job, logs, receipts and exact sources establish this narrow verdict.'],'compiler_jvm_native_runs':0,'process_probes_or_signals':0,'network':0,'child_agents':0,'commits':0,'pushes':0}
(OUT/'supplemental.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'verdict':'ACCEPT','checks':len(a.CHECKS),'exact_commands':len(expected)+len(bc)}))
