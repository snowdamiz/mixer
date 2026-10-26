from pathlib import Path
import datetime,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
PACKET=Path(__file__).resolve().parent

def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
proposal=json.loads((PACKET/'candidate-proposal.json').read_text())
for relative,expected in proposal['files'].items():assert identity((ROOT/relative).read_bytes())==expected,relative
host=json.loads((PACKET/'host-source-freeze.json').read_text())
for relative,expected in host['files'].items():assert identity((ROOT/relative).read_bytes())==expected,relative
for attempt in ['host-attempt-1','host-attempt-2','host-attempt-3']:
    attempt_path=PACKET/attempt;frozen=json.loads((attempt_path/'source-freeze.json').read_text())
    for relative,expected in frozen['files'].items():assert identity((attempt_path/'inputs'/relative).read_bytes())==expected,(attempt,relative)
profile=PACKET/'profile-qualification-2'
frozen=json.loads((profile/'source-freeze.json').read_text())
for relative,expected in frozen['files'].items():assert identity((profile/'source'/relative).read_bytes())==expected,relative
assert json.loads((profile/'receipt.json').read_text())['status']=='passed-host-profile2-qualification'
assert json.loads((PACKET/'cross-compilation-1/receipt.json').read_text())['status']=='passed-direct-cross-compilation-only'
owned=set(proposal['files'])|set(host['files'])|{'docs/android-environment-observer-lifecycle.md'}
command=['git','diff','--check','--',*sorted(owned)]
r=subprocess.run(command,cwd=ROOT,capture_output=True)
(PACKET/'edited-whitespace.stdout').write_bytes(r.stdout);(PACKET/'edited-whitespace.stderr').write_bytes(r.stderr)
assert r.returncode==0
revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,check=True)
(PACKET/'final-context.stdout').write_bytes(revision.stdout);(PACKET/'final-context.stderr').write_bytes(revision.stderr)
receipts={name:identity((PACKET/name).read_bytes()) for name in ['candidate-proposal.json','candidate-profile-2.json','host-source-freeze.json','host-attempt-1/receipt.json','host-attempt-2/receipt.json','host-attempt-3/receipt.json','profile-qualification-1/receipt.json','profile-qualification-2/receipt.json','cross-compilation-1/receipt.json']}
value={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':[sys.executable,*sys.argv],
    'python_version':sys.version,'context_revision':revision.stdout.decode().strip(),
    'status':'bounded-implementation-host-profile-and-cross-compilation-complete-pending-independent-review',
    'scope':'Actual private Observer repair and explicit fixed source profile2 migration; host leaves and actual CLI/source admission plus compile-only native outputs',
    'source_profile_id':'mixer.android-source-pair.2','candidate_proposal_sha256':receipts['candidate-proposal.json']['sha256'],
    'candidate_product_profile_sources_unchanged_after_admission':True,'all_42_mapped_sources_verified':True,
    'host_cases':161,'swift_admission_test_functions':10,'python_admission_tests':9,'ordinary_shared_app_host_tests':4,'ordinary_app_native_session_host_tests':3,
    'cross_compilation':{'java_sources':14,'class_files':160,'d8_min_api':28,'sdk_api':'37.0','swift_android':'6.3.3','ndk':'r27d','ABI':'arm64-v8a'},
    'preserved_failures':['host-attempt-1 registered JDK17 discovery unavailable before compilation','profile-qualification-1 Swift6.3.3 host manifest crash against macOS27 SDK before tests'],
    'receipts':receipts,'implementation_accepted_by_root':False,'native_runtime_or_capture_started_or_queried':False,
    'public_V2_routing_selected':False,'production_or_signing_or_GA_qualified':False,'new_dependencies':[],
    'checks':[{'command':command,'exit':r.returncode,'stdout':identity(r.stdout),'stderr':identity(r.stderr)},
              {'command':['git','rev-parse','HEAD'],'exit':revision.returncode,'stdout':identity(revision.stdout),'stderr':identity(revision.stderr)}],
    'cleanup':{'owned_scratch_removed':True,'owned_children_reaped':True,'native_or_capture_instances_created':False,'other_projects_processes_queried_or_changed':False},
    'pending':['Independent review and root acceptance/delivery','Native runtime matrix during pause','Private effect runner and public V2 root integration','API28-35 and unsupported accessibility/resources/fonts','Saved-state continuity','Final physical-phone matrix','Immutable published FieldLog packages from separate repository','Signing/store/customer/operational and accountable GA acceptance']}
save(PACKET/'receipt.json',value)
(PACKET/'documentation.md').write_bytes((ROOT/'docs/android-environment-observer-lifecycle.md').read_bytes())
files={}
for p in sorted(PACKET.rglob('*')):
    if p.is_file() and p.name not in ['manifest.json']:
        assert not p.is_symlink(),p
        files[p.relative_to(PACKET).as_posix()]=identity(p.read_bytes())
save(PACKET/'manifest.json',{'schema':1,'files':files,'members':len(files),'bytes':sum(v['bytes'] for v in files.values())})
print(json.dumps({'receipt':identity((PACKET/'receipt.json').read_bytes()),'manifest':identity((PACKET/'manifest.json').read_bytes()),'members':len(files),'bytes':sum(v['bytes'] for v in files.values())},sort_keys=True))
