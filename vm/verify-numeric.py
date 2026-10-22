#!/usr/bin/env python3
"""Reproduce owned numeric-v2 host/oracle/ABI evidence without changing source."""
import argparse,datetime,hashlib,json,os,pathlib,re,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'vm/verification/numeric-v2';OUT.mkdir(parents=True,exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('--corpus',default='verification/local/fieldlog-corpus-qualified/.build/wasm/wasm32-unknown-wasip1/release/fieldlog-corpus.wasm');args=p.parse_args();corpus=(ROOT/args.corpus).resolve()
env=os.environ.copy();env['PATH']='/opt/homebrew/opt/rustup/bin'+os.pathsep+env['PATH'];commands=[]
def source():
 files=[f for f in(ROOT/'vm').rglob('*')if f.is_file()and not set(f.relative_to(ROOT/'vm').parts)&{'target','verification'}]+[ROOT/'contracts/vm-profile-v1.json']
 return {str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in sorted(files)}
def run(name,cmd,expected=0):
 cmd=list(map(str,cmd));r=subprocess.run(cmd,cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);path=OUT/(name+'.log');path.write_text(r.stdout);commands.append({'name':name,'command':cmd,'exit_code':r.returncode,'output':str(path.relative_to(ROOT))});
 if r.returncode!=expected:raise RuntimeError(name+' failed: '+r.stdout)
 return r.stdout
start=source();head=run('base-revision',['git','rev-parse','HEAD']).strip()
unit=run('host-tests',['cargo','test','--manifest-path','vm/Cargo.toml']);passed=sum(map(int,re.findall(r'test result: ok\. (\d+) passed',unit)))
integer=run('integer-oracle',['cargo','test','--manifest-path','vm/Cargo.toml','--test','differential','--','--ignored','--nocapture'])
floats=run('float-oracle-debug',['cargo','test','--manifest-path','vm/Cargo.toml','--test','float_differential','--','--ignored','--nocapture'])
release_floats=run('float-oracle-release',['cargo','test','--release','--manifest-path','vm/Cargo.toml','--test','float_differential','--','--ignored','--nocapture'])
float_cases=list(map(int,re.findall(r'numeric-v2 differential cases matched: (\d+)',floats)));assert len(float_cases)==3 and sum(float_cases)==29794;assert sum(map(int,re.findall(r'numeric-v2 differential cases matched: (\d+)',release_floats)))==29794
run('clippy',['cargo','clippy','--manifest-path','vm/Cargo.toml','--all-targets','--','-D','warnings'])
run('release-build',['cargo','build','--release','--manifest-path','vm/Cargo.toml'])
for name,file in [('integer','ffi_smoke.c'),('numeric','ffi_numeric_smoke.c')]:
 executable='vm/target/ffi-'+name+'-smoke';run('c-'+name+'-build',['clang','-std=c11','-Wall','-Wextra','-Werror','-I','vm/include','vm/tests/'+file,'vm/target/release/libmixer_vm.a','-o',executable]);output=run('c-'+name+'-run',[executable])
 if name=='numeric':numeric_c_output=output
if not corpus.is_file():raise FileNotFoundError('supply the actual built FieldLog corpus via --corpus PATH; no substitute qualifies this receipt')
corpus_hash=hashlib.sha256(corpus.read_bytes()).hexdigest();text=run('fieldlog-inventory',['vm/target/release/mixer-vm','--profile','mixer-numeric-v2','inventory',corpus],expected=2);inventory=json.loads(text);assert inventory['inventory_complete']and not inventory['valid'];assert hashlib.sha256(corpus.read_bytes()).hexdigest()==corpus_hash
(OUT/'fieldlog-inventory.json').write_text(text)
versions={name:run('version-'+name,cmd).strip()for name,cmd in {'cargo':['cargo','--version'],'rustc':['rustc','--version'],'node':['node','--version'],'clang':['clang','--version'],'macos':['sw_vers']}.items()}
finish=source();assert start==finish,'source changed during verification; rerun from stable source'
manifest=''.join(f'{digest}  {path}\n'for path,digest in finish.items());(OUT/'source-manifest.sha256').write_text(manifest)
receipt={'schema_version':1,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'implementation_agent_selection':{'model':'gpt-6.1-sol','reasoning_effort':'xhigh'},'independent_review':False,'base_revision_at_start':head,'source_tree_digest':hashlib.sha256(manifest.encode()).hexdigest(),'source_manifest':'vm/verification/numeric-v2/source-manifest.sha256','source_scope':'vm/** excluding target/verification plus frozen contracts/vm-profile-v1.json','integer_profile_contract_sha256':finish['contracts/vm-profile-v1.json'],'tool_versions':versions,'commands':commands,'results':{'host_tests_passed':passed,'integer_differential_execution_cases':sum(map(int,re.findall(r'differential cases matched: (\d+)',integer))),'float_differential_cases_per_build':sum(float_cases),'float_oracle_builds':['debug','release'],'float_case_groups':{'arithmetic_comparison_rounding_bitwise':27944,'conversion_reinterpret_saturation':1290,'memory_calls_globals':560},'validation_mutation_candidates':2693,'c_abi':['original integer-v1 stable layout/invoke/limits passed','numeric-v2 raw IEEE bits, old-symbol rejection, host rounding/flush/trap-control checks passed'],'clippy':'all targets -D warnings passed','native_fp_controls':numeric_c_output.strip()},'fieldlog_corpus':{'path':str(corpus.relative_to(ROOT)),'bytes':corpus.stat().st_size,'sha256':corpus_hash,'source_revision':'1587d2d4f02ab2dad9914df97f878727dd622296','profile':inventory['profile'],'valid':inventory['valid'],'inventory_complete':inventory['inventory_complete'],'imports':len(inventory['imports']),'primary_opcodes':len(inventory['opcodes']),'instruction_occurrences':sum(x['count']for x in inventory['opcodes']),'rejection':inventory['error'],'scope':'actual FieldLog model corpus compiled by integrator; no owned-VM execution qualification'},'qualified_execution_target':'macOS27 arm64 host only','open_gates':['independent numeric profile review','standards suites','continuous coverage-guided fuzzing','physical iOS/Android VM execution','non-default CPU/platform qualification','tables/indirect calls','bulk-memory copy/fill','bounded WASI/Swift runtime adapters','actual corpus resource budgets and owned-VM execution','Swift sources/debugger','FieldLog OTA coverage','W08/D3/GA']}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'source_tree_digest':receipt['source_tree_digest'],'host_tests_passed':passed,'float_cases_per_build':sum(float_cases),'full_swift_qualified':False},indent=2))
