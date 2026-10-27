#!/usr/bin/env python3
"""Prepare the root-review command roster; never execute a compiler or product."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;R=P.parents[1];S=P/'source';B=P/'build'
T=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
def sha(v):return hashlib.sha256(v).hexdigest()
def row(p):
    raw=p.read_bytes();return {'path':str(p.relative_to(R)) if p.is_relative_to(R) else str(p),'bytes':len(raw),'sha256':sha(raw)}
def common():
    return [str(T),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','overflow-checks=yes','-C','panic=unwind',
      '--cfg','feature="experimental-swift-reactor"','--cfg','feature="experimental-swift-wasi"','--cfg','feature="experimental-stream-validation"',
      '--cfg','feature="experimental-function-cache"','--cfg','mixer_bootstrap_one_fixture_v1']
commands=[{'id':'toolchain','kind':'version','argv':[str(T),'-vV']}]
commands.append({'id':'production-MIR','kind':'compiler','argv':common()+['-C','opt-level=0','-Zmir-opt-level=0','--crate-type','rlib',str(S/'vm/src/lib.rs'),'-Zmir-include-spans=yes','--emit=metadata='+str(B/'actual.rmeta')+',mir='+str(B/'actual.mir')]})
for mode,opt in [('debug','0'),('opt2','2')]:
    commands.append({'id':'build-'+mode,'kind':'compiler','argv':common()+['--test','-C','opt-level='+opt,str(S/'vm/src/lib.rs'),'-o',str(B/('tests-'+mode))]})
    commands.append({'id':'run-'+mode,'kind':'host','argv':[str(B/('tests-'+mode)),'prepaid_actual_owner_v1','trusted_local_host_account_entry_v1::host_account_v1::tests','--test-threads=1','--nocapture'],
      'scope':'Actual production generic guard/acquisition/correlation/retirement/validator host tests, unchanged child-account guard suite, and Pending selector test only; no native File acquisition or actual VM fixture/runtime.'})
for probe in json.loads((P/'probe-roster.json').read_text())['probes']:
    commands.append({'id':probe['id'],'kind':'compiler-negative','probe':row(P/probe['fragment']),'intended_diagnostics':probe['intended_diagnostics'],
      'paired_control':probe['paired_control'],'scope_limit':probe['limitation'],
      'environment_additions':{'MIXER_IR02_PROBE_PATH_V1':str(P/probe['fragment'])},
      'argv':common()+['--cfg','mixer_ir02_probe_'+probe['scope']+'_v1','-C','opt-level=0','--crate-type','rlib',str(S/'vm/src/lib.rs'),
        '--emit=metadata='+str(B/(probe['id']+'.rmeta'))]})
assert sum(c['kind'].startswith('compiler') for c in commands)==21
assert sum(c['kind']=='host' for c in commands)==2
assert sum(c['kind']=='version' for c in commands)==1
roster={'schema':1,'status':'immutable-proposal-awaiting-root-review-and-single-compiler-lane-release',
  'compiler_invocations':21,'production_metadata_complete_MIR':1,'test_binary_builds':2,'negative_compiler_probes':18,'host_runs':2,'version_queries':1,
  'simultaneous_compilers':1,'each_command_seconds_max':55,'child_deadline_seconds':51,'stdout_stderr_each_bytes_max':4194304,'layout_queries':0,
  'source146_tree':json.loads((P/'source-manifest.json').read_text())['tree_sha256'],'source_manifest':row(P/'source-manifest.json'),
  'host11_tree':json.loads((P/'host-manifest.json').read_text())['tree_sha256'],'host_manifest':row(P/'host-manifest.json'),
  'root_selection':row(R/'verification/swift-semantic-adapter-root-review/guarded-snapshot-root-result-lifetime-selection.json'),
  'contract_seal':row(R/'verification/swift-guarded-snapshot-root-result-lifetime-contract/seal.json'),
  'frozen_correction_seal':row(R/'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction/seal.json'),
  'tool':row(T),'tool_version_query_pending':True,
  'environment':{'PATH':'/usr/bin:/bin','RUSTC_BOOTSTRAP':'1','SDKROOT':'/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',
    'CARGO_MANIFEST_DIR':str(S/'vm'),'TMPDIR':str(B),'LANG':'C','LC_ALL':'C','TZ':'UTC'},
  'cwd':str(R),'commands':commands,'compiled_source_copy_count':1,'probe_injection':'One cfg-only immutable external fragment per negative invocation; no copied source tree, no production fragment cfg.',
  'retries_selected':0,'new_compiler_execution':False,'host_product_execution':False,'native_File_or_VM_fixture_execution':False,'UI_capture_simulator_phone_network':False,
  'new_source_MIR_layout_prices_accepted':False,'forgotten_root_funding_shutdown_full_ownership_joint_retirement_accepted':False}
(P/'proposed-command-roster.json').write_text(json.dumps(roster,indent=2)+'\n')
print(json.dumps({'compiler':21,'host':2,'version':1,'executed':0,'roster_sha256':sha((P/'proposed-command-roster.json').read_bytes())}))
