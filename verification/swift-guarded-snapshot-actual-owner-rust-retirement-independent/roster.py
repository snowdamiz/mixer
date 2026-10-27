"""Offline exact selected roster. No tool/compiler/runtime execution."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN=ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction'
TOOL=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
SOURCE=HERE/'source';BUILD=HERE/'build'
common=[str(TOOL),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','overflow-checks=yes','-C','panic=unwind','--cfg','feature="experimental-swift-reactor"','--cfg','feature="experimental-swift-wasi"','--cfg','feature="experimental-stream-validation"','--cfg','feature="experimental-function-cache"','--cfg','mixer_bootstrap_one_fixture_v1']
commands=[]
for mode,opt in [('debug','0'),('opt2','2')]:
    commands.append(dict(id='build-debug-corrected' if mode=='debug' else 'build-'+mode,kind='compiler',argv=common+['--test','-C','opt-level='+opt,str(SOURCE/'vm/src/lib.rs'),'-o',str(BUILD/('tests-'+mode))]))
    commands.append(dict(id='run-'+mode,kind='host',argv=[str(BUILD/('tests-'+mode)),'prepaid_actual_owner_v1','--test-threads=1','--nocapture']))
roster=dict(schema=1,status='root-released-two-builds-two-filtered-runs',root_authorization='Root message 2026-10-27: Compiler lane RELEASED; 2 test builds Debug,opt2 +2 filtered host runs; <=55s each; no extra commands without selection.',
    compiler=3,remaining_compiler=2,historical_failed_compiler='commands/build-debug/receipt.json',replacement_authorization='Root explicitly selected exactly one replacement Debug after documented harness-only parenthesis correction; no other compiler retries.',host=2,version_queries=0,production_MIR_recompiles=0,negative_recompiles=0,native_fixture_UI_capture=False,
    frozen_seal_sha256='46d811b1264770604106b061386e6eba01ea07e55590240eff722c36af4bcaa0',
    source146_tree=json.loads((HERE/'tested-source-manifest.json').read_text())['tree_sha256'],frozen_source146_tree='c3a33b76eef6bf9ad86ef1cb0320e94bcefa5a0609ec1a30872a9d83371bd0db',
    host11_tree='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2',
    harness=dict(fragment_sha256=hashlib.sha256((HERE/'independent.inc.rs').read_bytes()).hexdigest(),vectors_sha256=hashlib.sha256((HERE/'vectors.inc.rs').read_bytes()).hexdigest(),patch_sha256=hashlib.sha256((HERE/'independent-only.patch').read_bytes()).hexdigest(),
        producer_methods_unchanged=25,independent_methods=6,expected_methods_per_run=31,filter='prepaid_actual_owner_v1',
        frozen_binary=51,frozen_provenance=230,provenance_optional_shapes=2,frozen_read_schedules=12,facade_escape_helper='compiled only; actual opaque File facade types, no File construction or execution'),
    toolchain=json.loads((FROZEN/'toolchain.json').read_text()),
    environment={'PATH':'/usr/bin:/bin','RUSTC_BOOTSTRAP':'1','SDKROOT':'/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk','CARGO_MANIFEST_DIR':str(SOURCE/'vm'),'TMPDIR':str(BUILD),'LANG':'C','LC_ALL':'C','TZ':'UTC'},
    seconds_max=55,child_deadline_seconds=51,stdout_stderr_each_bytes_max=4194304,simultaneous_compilers=1,commands=commands)
(HERE/'proposed-command-roster.json').write_text(json.dumps(roster,indent=2,sort_keys=True)+'\n')
print(json.dumps({'source146_tree':roster['source146_tree'],'harness':roster['harness'],'roster_sha256':hashlib.sha256((HERE/'proposed-command-roster.json').read_bytes()).hexdigest()}))
