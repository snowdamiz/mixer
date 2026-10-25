#!/usr/bin/env python3
"""Verify reviewed workspace bindings and focused integration wiring; no application execution."""
from pathlib import Path
import ast,datetime,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];BASE=Path(__file__).resolve().parent
out=BASE/'attempt-2';out.mkdir(exist_ok=False)
prior=json.loads((BASE/'attempt-1/acceptance.json').read_text())
current=json.loads((BASE/'attempt-1/current-source-manifest.json').read_text())
commands=[];bindings=0

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bind(files):
 global bindings
 for name,expected in files.items():
  assert sha(ROOT/name)==expected,name;bindings+=1

def run(label,argv):
 r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60)
 (out/(label+'.stdout')).write_bytes(r.stdout);(out/(label+'.stderr')).write_bytes(r.stderr)
 commands.append({'argv':argv,'exit_code':r.returncode,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest()})
 assert r.returncode==0,label

bind(current)
for item in prior['accepted_receipts']:assert sha(ROOT/item['path'])==item['sha256'],item['path']
seals=[]
for rel in ['verification/hosted-workspace-identity-session-review/seal.json','verification/hosted-customer-workspace-http/seal.json','verification/console-workspace-client-review/seal.json','verification/hosted-customer-workspace-http-integration/seal.json']:
 data=json.loads((ROOT/rel).read_text());files=data.get('files',data.get('owned_files',{}));assert files,rel;bind(files);seals.append({'path':rel,'sha256':sha(ROOT/rel),'file_count':len(files)})
ui=ROOT/'verification/console-workspace-directory-review/correction/source-manifest.json';ud=json.loads(ui.read_text());bind(ud['sources_sha256'])
for name,h in ud['sources_sha256'].items():
 if name.startswith(('console/src/','console/tests/')):current[name]=h
http=json.loads((ROOT/'verification/hosted-customer-workspace-http/summary.json').read_text());bind(http['live_product_source_hashes']);assert http['total_tests_passed']==54
run('python-version',['python3','--version']);run('elixir-version',['elixir','--version']);run('node-version',['node','--version'])
run('typescript-version',['node','console/node_modules/typescript/bin/tsc','--version'])
changed=[p for p in current if p.startswith(('hosted/lib/','hosted/test/','hosted/priv/')) and p.endswith(('.ex','.exs'))]
# Selected product files only; do not invoke the application's formatter glob.
run('format',['mix','format','--check-formatted',*sorted(changed)])
run('workflow-yaml',['ruby','-e','require "yaml"; v=YAML.safe_load_file(".github/workflows/hosted.yml"); abort "missing jobs" unless v["jobs"]["phoenix"]["steps"].is_a?(Array); puts "valid YAML"'])
# All shell steps parse; this is syntax verification, not execution of the shared harness.
script='require "yaml"; YAML.safe_load_file(".github/workflows/hosted.yml")["jobs"]["phoenix"]["steps"].each {|s| if s["run"]; IO.popen(["bash","-n"],"w") {|p| p.write(s["run"])}; abort "invalid shell" unless $?.success?; end }; puts "shell steps valid"'
run('workflow-shell',['ruby','-e',script])
helper=ROOT/'hosted/scripts/test-local.py';tree=ast.parse(helper.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='provision_customer_artifact_fixtures');rows=ast.literal_eval(next(n for n in fn.body if isinstance(n,ast.For)).iter)
for row in [('workspace','mixer_customer_workspace','MIXER_WORKSPACE_TEST_PORT'),('workspace_http','mixer_customer_workspace_http','MIXER_WORKSPACE_HTTP_TEST_PORT')]:assert rows.count(row)==1
(out/'current-source-manifest.json').write_text(json.dumps(current,indent=2)+'\n')
receipt={**prior,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'commands':commands,'sealed_file_bindings_verified':bindings,'review_seals':seals,'current_product_bindings':len(current),'current_source_manifest_sha256':sha(out/'current-source-manifest.json'),'scope':'Local customer workspace discovery/storage, HTTP/default identity/default Repo, actual Node client join and controlled website-branded UI. Counts overlap. Full login/App/session composition, browser/CORS/provider/production/native/GA remain pending.','qualification':'accepted local development slice; exact pushed CI pending','checks':{**prior['checks'],'review_seals_match':True,'selected_source_formatting':True,'workflow_yaml_and_shell_syntax':True,'shared_test_main_executed_locally':False,'new_browser_capture_or_native_run':False}}
(out/'acceptance.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'accepted':True,'bindings':bindings,'current':len(current),'receipt':str(out/'acceptance.json')}))
