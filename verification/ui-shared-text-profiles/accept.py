from pathlib import Path
import hashlib,json,datetime,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];bindings={}
def bind(p,expected=None):
    h=hashlib.sha256(p.read_bytes()).hexdigest();assert expected is None or expected==h,str(p)
    bindings[str(p.relative_to(ROOT))]=h;return h
host=json.loads((HERE/'receipt.json').read_text())
assert len(host['commands'])==3 and all(c['exit']==0 for c in host['commands'])
for p,h in host['source_files'].items():bind(ROOT/p,h)
for c in host['commands']:bind(ROOT/c['log'],c['sha256'])
for mode in ['debug','release']:
    text=(HERE/(mode+'.log')).read_text()
    assert 'Executed 3 tests, with 0 failures' in text
    for n in [74,10,2]:assert 'Test run with '+str(n)+' tests' in text
modules=HERE/'candidate-2';r=json.loads((modules/'module-receipt.json').read_text())
assert len(r['commands'])==17 and all(c['exit']==0 for c in r['commands'])
for p,h in r['source_manifest'].items():bind(ROOT/p,h);bind(modules/'inputs'/p,h)
for c in r['commands']:bind(ROOT/c['log'],c['sha256'])
for p,h in r['artifacts'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
assert (modules/'host-debug-run.log').read_bytes()==(modules/'host-release-run.log').read_bytes()
profiles=json.loads((ROOT/'verification/apple-appearance-font-profile/type-profiles.json').read_text())['profiles']
rows={p['normalizedProfileID']:p for p in profiles};anchors=[int(p['fonts']['body']['size']*64) for p in profiles]
count=selections=0
for line in (modules/'host-debug-run.log').read_text().splitlines():
    v=line.split()
    if v[0]=='METRIC':
        role=v[2];p=rows[v[1]]
        measured=p['actualExpandedNavigationUIFont'] if role=='navigationExpanded' else p['fonts']['sectionHeaderCandidate' if role=='sectionHeader' else role]
        assert int(v[3])==int(measured['pointSize']*64)
        assert int(v[4])==(700 if role=='navigationExpanded' else 600 if role in ['headline','sectionHeader'] else 400)
        count+=1
    else:
        assert v[0]=='SELECT';n=int(v[1]);expected='unsupported'
        if anchors[0]<=n<=anchors[-1]:expected=profiles[min(range(12),key=lambda i:(abs(n-anchors[i]),-i))]['normalizedProfileID']
        assert v[2]==expected;selections+=1
assert (count,selections)==(72,3502)
for p in [HERE/'receipt.json',modules/'module-receipt.json',HERE/'accept.py',ROOT/'verification/apple-appearance-font-profile-root-review/acceptance.json']:bind(p)
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'reviewer':'root','decision':'accepted-measured-shared-text-profile-data','binding_count':len(bindings),'bindings':dict(sorted(bindings.items())),'sdk_tests_per_mode':89,'public_role_metrics_compared_to_native_reference_per_mode':72,'public_selection_outcomes_per_mode':3502,'platform_modules':'iOS17 ARM64 and official Swift6.3.3 Android30 AArch64; public caller typechecks','limitations':['New profile data API only. V1 descriptor/default/resolver behavior unchanged; neither native renderer consumes measured profiles yet.','Nearest anchor policy explicitly rejects outside14..53 points; native preference conversion and environment-change handling are unimplemented and unqualified.','Section headline and expanded title are adopted shared roles from bounded measurements, not universal native contextual matches. No fixed line-height/clipping contract.','First standalone module-link attempt lacked -lMixerCore; failed command/source/log retained. Corrected harness changes no product source.','No physical parity, signed resource/display/health, immutable published FieldLog or GA qualification.']}
(HERE/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(bindings),'root bindings;89SDK tests per mode;72native-reference metrics;3502selection outcomes')
