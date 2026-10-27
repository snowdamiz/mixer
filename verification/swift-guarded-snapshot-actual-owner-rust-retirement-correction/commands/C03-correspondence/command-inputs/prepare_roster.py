#!/usr/bin/env python3
"""Write a prospective exact argv roster; execute no tool/compiler/test."""
from pathlib import Path
import hashlib,json
from probes import PROBES
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TOOL=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
BUILD=HERE/'build'
SOURCE=HERE/'source'
def common():return [str(TOOL),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','overflow-checks=yes','-C','panic=unwind','--cfg','feature="experimental-swift-reactor"','--cfg','feature="experimental-swift-wasi"','--cfg','feature="experimental-stream-validation"','--cfg','feature="experimental-function-cache"','--cfg','mixer_bootstrap_one_fixture_v1']
commands=[{'id':'toolchain','kind':'version','argv':[str(TOOL),'-vV']}]
commands.append({'id':'production-MIR','kind':'compiler','argv':common()+['-C','opt-level=0','-Zmir-opt-level=0','--crate-type','rlib',str(SOURCE/'vm/src/lib.rs'),'-Zmir-include-spans=yes','--emit=metadata='+str(BUILD/'actual.rmeta')+',mir='+str(BUILD/'actual.mir')]})
for mode,opt in [('debug','0'),('opt2','2')]:
    commands.append({'id':'build-'+mode,'kind':'compiler','argv':common()+['--test','-C','opt-level='+opt,str(SOURCE/'vm/src/lib.rs'),'-o',str(BUILD/('tests-'+mode))]})
    commands.append({'id':'run-'+mode,'kind':'host','argv':[str(BUILD/('tests-'+mode)),'prepaid_actual_owner_v1','--test-threads=1','--nocapture']})
for name,(scope,fragment,diagnostics) in PROBES.items():
    base=HERE/'probes'/name
    commands.append({'id':name,'kind':'compiler-negative','source':str(base/'source'),'insertion_scope':scope,'fragment':fragment,'intended_diagnostics':diagnostics,'argv':common()+['-C','opt-level=0','--crate-type','rlib',str(base/'source/vm/src/lib.rs'),'--emit=metadata='+str(base/'negative.rmeta')]})
roster={'schema':1,'status':'prospective-awaiting-root-selection-and-single-compiler-lane-release','compiler_invocations':9,'host_runs':2,'version_queries':1,'simultaneous_compilers':1,'each_command_seconds_max':55,'child_deadline_seconds':51,'stdout_stderr_each_bytes_max':4194304,'layout_queries':0,'source146_tree':json.loads((HERE/'source-manifest.json').read_text())['tree_sha256'],'host11_tree':json.loads((HERE/'host-manifest.json').read_text())['tree_sha256'],'tool':{'path':str(TOOL),'bytes':TOOL.stat().st_size,'sha256':hashlib.sha256(TOOL.read_bytes()).hexdigest()},'environment':{'PATH':'/usr/bin:/bin','RUSTC_BOOTSTRAP':'1','SDKROOT':'/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','CARGO_MANIFEST_DIR':'per-command-source/vm','TMPDIR':str(BUILD),'LANG':'C','LC_ALL':'C','TZ':'UTC'},'commands':commands,'broad_matrix_or_blind_replays':False,'new_compiler_execution':False,'native_fixture_UI_capture':False,'old_prices_or_layouts_authoritative':False,'retries_selected':0}
(HERE/'proposed-command-roster.json').write_text(json.dumps(roster,indent=2)+'\n')
print(json.dumps({'compiler':9,'host':2,'version':1,'executed':0,'roster_sha256':hashlib.sha256((HERE/'proposed-command-roster.json').read_bytes()).hexdigest()}))
