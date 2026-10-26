#!/usr/bin/env python3
"""Prepare review data only. Do not execute repository code or apply a workflow."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import platform
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
source=ROOT/'.github/workflows/verify.yml'
original=source.read_text()
start=original.index('      - name: Isolated experimental capability archive and shared registry\n')
consumer=original.index('      - name: Generated consumer integration\n',start)
vm=original.index('  vm:\n',consumer)
header=original[original.index('  swift:\n'):original.index('      - name: CI selection regression tests\n')]
new_header=header.replace('  swift:\n','  swift-capability-native:\n',1)
# All five existing dependent steps move as one byte-for-byte chain.
chain=original[start:consumer]
core_receipt='''      - name: Preserve core Apple toolchain and owned VM receipts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: swift-core-toolchain-host-${{ github.sha }}
          retention-days: 14
          if-no-files-found: ignore
          path: |
            ${{ runner.temp }}/apple-toolchain.json
            ${{ runner.temp }}/native-vm/receipt.json
'''
candidate=original[:start]+original[consumer:vm]+core_receipt+new_header+chain+original[vm:]
(OUT/'proposed-verify.yml').write_text(candidate)
(OUT/'proposed-verify.diff').write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),candidate.splitlines(keepends=True),fromfile='a/.github/workflows/verify.yml',tofile='b/.github/workflows/verify.yml')))

def sha(raw): return hashlib.sha256(raw).hexdigest()

def run(label, argv):
 p=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
 (OUT/(label+'.stdout')).write_bytes(p.stdout);(OUT/(label+'.stderr')).write_bytes(p.stderr)
 row={'label':label,'argv':argv,'cwd':str(ROOT),'exit':p.returncode,'stdout_sha256':sha(p.stdout),'stderr_sha256':sha(p.stderr)}
 commands.append(row)
 if p.returncode: raise RuntimeError(str(row))
 return p.stdout.decode().strip()
commands=[]
head=run('source-revision',['git','rev-parse','HEAD'])
tree=run('source-git-tree',['git','rev-parse','HEAD^{tree}'])
versions={name:run(name+'-version',argv) for name,argv in {'python':['python3','--version'],'ruby':['ruby','-v'],'git':['git','--version'],'psych':['ruby','-rpsych','-e','puts Psych::VERSION']}.items()}
# Ruby Psych parses only workflow data; no product/test script is imported.
ruby='''require 'yaml'; require 'json'; ARGV.each { |p| puts JSON.generate({path:p,data:YAML.safe_load_file(p, permitted_classes: [], permitted_symbols: [], aliases:false)}) }'''
parsed=run('yaml-parse',['ruby','-rpsych','-e',ruby,str(source),str(OUT/'proposed-verify.yml')])
data=[json.loads(row)['data'] for row in parsed.splitlines()]
before,after=data
old=before['jobs'];new=after['jobs']
assert set(new)==set(old)|{'swift-capability-native'}
assert all(new[j]==old[j] for j in old if j!='swift')
assert new['swift']['runs-on']==new['swift-capability-native']['runs-on']==old['swift']['runs-on']=='macos-15'
assert new['swift']['timeout-minutes']==new['swift-capability-native']['timeout-minutes']==old['swift']['timeout-minutes']==30
assert new['swift']['env']==new['swift-capability-native']['env']==old['swift']['env']
core=new['swift']['steps'];cap=new['swift-capability-native']['steps'];oldsteps=old['swift']['steps']
assert core[:-1]==oldsteps[:13]+oldsteps[18:19]
assert cap[:2]==oldsteps[:2]
assert cap[2:]==oldsteps[13:18]
assert core[-1]['name']=='Preserve core Apple toolchain and owned VM receipts'
assert all('needs' not in new[j] for j in ['swift','swift-capability-native'])
rows=[]
for job_id,job in old.items():
 for index,step in enumerate(job['steps']):
  target='swift-capability-native' if job_id=='swift' and 13<=index<18 else job_id
  row={'original_job':job_id,'original_step_index':index,'name':step.get('name',step.get('uses')),'proposed_job':target,'retention':'unchanged step mapping and run payload','step_sha256':sha(json.dumps(step,sort_keys=True,separators=(',',':')).encode())}
  assert step in new[target]['steps']
  rows.append(row)
validation={'schema':1,'status':'passed-static-proposal-validation','checks':['Ruby Psych safe YAML parse of original and proposed workflow data','all original 4 job identifiers retained; one new macOS job','all three non-Swift jobs byte-equivalent as parsed YAML','every existing Swift step retained exactly once except intentional duplicated checkout and Apple probe','all run scripts/options/step timeouts/artifact paths retained exactly','both macOS jobs retain 30 minute timeout, macos-15 and exact Apple env','capability chain stays ordered and local to new job; no needs/artifact download added','one additional always core Apple/owned-VM receipt upload'],'existing_steps':len(rows),'new_job':'swift-capability-native','executed_product_tests':False,'native_runtime_capture_or_ui_used':False,'workflow_applied':False,'versions':versions}
(OUT/'proposal-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
(OUT/'coverage.json').write_text(json.dumps({'schema':1,'mapping':rows,'duplicated_prerequisites':['actions/checkout@v4 with fetch-depth:0','Verify and record pinned Apple toolchain'],'new_steps':['Preserve core Apple toolchain and owned VM receipts']},indent=2)+'\n')

# A finite source evidence set: no prohibited frozen inspectors/drivers are read.
paths=['AGENTS.md','.github/workflows/verify.yml','Package.swift','sdk/Package.swift','updates/Package.swift','capabilities/Package.swift','runtime-identity/Package.swift','cli/Package.swift','native/android/engine/Package.swift','runtime/Package.swift','activation/Package.swift','verification/runtime-review/Package.swift','experimental-capability-runtime/Package.swift','capability-activation/Package.swift','verification/capability-bridge-review/Package.swift','scripts/ci/verify-apple-toolchain.py','scripts/ci/check-android-binding.py','scripts/ci/check-sdk-package.py','scripts/ci/check-analyzer-framing.py','scripts/ci/check-analyzer-envelope.py','scripts/ci/tests/test_apple_toolchain.py','scripts/ci/tests/test_dependency_policy.py','runtime/build-vm.py','experimental-capability-runtime/build-vm.py','experimental-capability-runtime/build-tests/test_builder.py','experimental-capability-runtime/verification/with-loopback.py','verification/capability-installed-material/test_native_preimage.py','capabilities/tools/export-native-preimage.py','capabilities/tools/check-guest-transport-fixtures.py','cli/Sources/MixerCLI/main.swift','cli/Sources/MixerBuild/ProjectGenerator.swift','cli/Sources/MixerBuild/AppleProject.swift','vm/Cargo.toml','verification/github-delivery-android-owner-candidate5/ci-terminal.json','verification/github-delivery-android-owner-candidate5/ci-attempt1-cancellation/job.stdout','verification/github-delivery-android-owner-candidate5/ci-attempt1-cancellation/summary.json','verification/github-delivery-android-owner-candidate5/ci-attempt1-cancellation/logs-safe-capture.stdout','verification/github-delivery-environment-profile4/ci-snapshot-5.json']
manifest=[{'path':path,'bytes':(ROOT/path).stat().st_size,'sha256':sha((ROOT/path).read_bytes())} for path in sorted(paths)]
(OUT/'source-evidence.json').write_text(json.dumps({'schema':1,'source_revision':head,'source_git_tree':tree,'files':manifest,'finite_source_manifest_sha256':sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()),'scope':'review of named workflow, dependency declarations, invoked runner implementations, CLI path and existing CI receipts only; no product code execution'},indent=2)+'\n')

def duration(st,en):
 if not st or not en or st.startswith('0001') or en.startswith('0001'):return None
 return (datetime.datetime.fromisoformat(en.replace('Z','+00:00'))-datetime.datetime.fromisoformat(st.replace('Z','+00:00'))).total_seconds()
receipts=[]
for path in ['verification/github-delivery-android-owner-candidate5/ci-attempt1-cancellation/job.stdout','verification/github-delivery-android-owner-candidate5/ci-terminal.json']:
 d=json.loads((ROOT/path).read_text());j=d if 'steps' in d else next(j for j in d['jobs'] if j['name']=='swift')
 steps=[]
 for s in j['steps']:
  steps.append({'number':s['number'],'name':s['name'],'conclusion':s['conclusion'],'seconds':duration(s.get('startedAt',s.get('started_at')),s.get('completedAt',s.get('completed_at')))})
 receipts.append({'source':path,'job_conclusion':j['conclusion'],'job_seconds':duration(j.get('startedAt',j.get('started_at')),j.get('completedAt',j.get('completed_at'))),'steps':steps})
(OUT/'retained-timings.json').write_text(json.dumps({'schema':1,'receipts':receipts,'timing_claim':'observed historical step durations only; no future completion or new-job timing verification'},indent=2)+'\n')
(OUT/'commands.json').write_text(json.dumps({'schema':1,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'review_entry_point':['python3',str(OUT/'prepare-proposal.py')],'commands':commands,'earlier_interactive_read_commands':'Targeted cat/sed/rg/wc and Python standard-library JSON duration extraction; all read-only. No tests, product builds, CI network requests, reruns, cancellations or dispatches. Exact substantive parser/version/source commands are preserved above.'},indent=2)+'\n')
print(json.dumps({'source_revision':head,'source_git_tree':tree,'proposal_workflow_sha256':sha(candidate.encode()),'retained_original_steps':len(rows),'validation':validation['status']},indent=2))
