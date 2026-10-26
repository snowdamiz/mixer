#!/usr/bin/env python3
"""Validate and freeze proposal data only; never run repository product code."""
from pathlib import Path
from collections import Counter
import datetime,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
original=ROOT/'.github/workflows/verify.yml';original_copy=OUT/'original-verify.yml'
original_copy.write_bytes(original.read_bytes())
commands=[]
def run(label,argv):
 p=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 (OUT/(label+'.stdout')).write_bytes(p.stdout);(OUT/(label+'.stderr')).write_bytes(p.stderr)
 commands.append({'name':label,'argv':argv,'cwd':str(ROOT),'exit':p.returncode,'stdout_sha256':sha(p.stdout),'stderr_sha256':sha(p.stderr)})
 if p.returncode:raise RuntimeError(label)
 return p.stdout.decode()
ruby="require 'yaml'; require 'json'; ARGV.each { |p| puts JSON.generate(YAML.safe_load_file(p, permitted_classes: [], permitted_symbols: [], aliases:false)) }"
parsed=run('final-yaml-parse',['ruby','-rpsych','-e',ruby,str(original_copy),str(OUT/'proposed-verify.yml')])
old,new=[json.loads(line) for line in parsed.splitlines()]
checks=[]
def check(name,condition):
 if not condition:raise RuntimeError(name)
 checks.append({'check':name,'passed':True})
check('top-level workflow scope unchanged', {k:v for k,v in old.items() if k!='jobs'}=={k:v for k,v in new.items() if k!='jobs'})
check('exactly one new job',set(new['jobs'])==set(old['jobs'])|{'swift-capability-native'})
for job in ('android-owner-host','vm','services'):check(job+' complete job object unchanged',old['jobs'][job]==new['jobs'][job])
old_swift=old['jobs']['swift'];core=new['jobs']['swift'];cap=new['jobs']['swift-capability-native']
for key in ('runs-on','timeout-minutes','env'):
 check('both macOS '+key+' values unchanged',old_swift[key]==core[key]==cap[key])
check('core original job metadata unchanged', {k:v for k,v in old_swift.items() if k!='steps'}=={k:v for k,v in core.items() if k!='steps'})
check('new capability job original metadata duplicated', {k:v for k,v in old_swift.items() if k!='steps'}=={k:v for k,v in cap.items() if k!='steps'})
check('core retains ordered first 13 plus consumer step',core['steps'][:-1]==old_swift['steps'][:13]+old_swift['steps'][18:19])
check('capability retains ordered five-step chain',cap['steps'][2:]==old_swift['steps'][13:18])
check('duplicated checkout and Apple verification are exact original objects',cap['steps'][:2]==old_swift['steps'][:2])
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'))
old_counter=Counter(canonical(s) for s in old_swift['steps'])
new_steps=core['steps'][:-1]+cap['steps'][2:]
check('all Swift step objects conserved exactly once excluding duplicated two prerequisites and one new receipt upload',Counter(canonical(s) for s in new_steps)==old_counter)
check('all original 37 source-defined steps conserved',sum(len(j['steps']) for j in old['jobs'].values())==37)
check('one new artifact upload is always and 14-day retained',core['steps'][-1]['if']=='always()' and core['steps'][-1]['uses']=='actions/upload-artifact@v4' and core['steps'][-1]['with']['retention-days']==14)
check('original Android binding upload retains artifact paths and action configuration',cap['steps'][-1]==old_swift['steps'][17])
check('no inter-job needs or shared-runner assumptions introduced','needs' not in core and 'needs' not in cap)
check('no download/cache action introduced',not any(s.get('uses','').startswith(('actions/download-artifact','actions/cache')) for j in new['jobs'].values() for s in j['steps']))
source=json.loads((OUT/'source-evidence.json').read_text())
check('reviewed source evidence bytes unchanged',all(sha((ROOT/r['path']).read_bytes())==r['sha256'] for r in source['files']))
head=run('final-source-revision',['git','rev-parse','HEAD']).strip()
check('HEAD unchanged from reviewed base',head==source['source_revision'])
result={'schema':1,'status':'passed-static-partition-review','checks':checks,'original_steps':37,'original_swift_steps':19,'proposed_swift_core_steps':len(core['steps']),'proposed_capability_steps':len(cap['steps']),'product_tests_or_builds_executed':False,'original_workflow_sha256':sha(original_copy.read_bytes()),'proposed_workflow_sha256':sha((OUT/'proposed-verify.yml').read_bytes()),'source_revision':head,'source_git_tree':source['source_git_tree'],'validation_command':['python3',str(OUT/'finalize-validation.py')],'commands':commands}
(OUT/'final-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks_passed':len(checks),'all_original_steps':37,'proposal_sha256':result['proposed_workflow_sha256']},indent=2))
# The manifest lists every regular file already in this finite packet, excluding
# itself. No member is changed after this point by the reviewer.
rows=[]
for p in sorted(OUT.iterdir()):
 if p.name=='packet-manifest.json':continue
 if not p.is_file() or p.is_symlink():raise RuntimeError('unexpected packet member')
 rows.append({'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
manifest={'schema':1,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':head,'members':rows,'member_count':len(rows),'manifest_excludes_itself':True,'member_set_sha256':sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()),'read_only_review':True}
(OUT/'packet-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
