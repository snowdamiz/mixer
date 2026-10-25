"""Independent arithmetic/history audit; no producer imports or workload execution."""
import datetime
import hashlib
import json
import pathlib
import struct

ROOT=pathlib.Path(__file__).resolve().parents[2]
OWN=pathlib.Path(__file__).resolve().parent
SNAP=OWN/"snapshots/run-2/verification/swift-ordered-retention-analyzer-library"
MAX=(1<<64)-1

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def footer_observation(raw):
    """Only closed header/footer grammar. Never checks stored event semantics."""
    if len(raw)<1024 or (len(raw)-1024)%128: return False
    head=struct.unpack("<64Q",raw[:512]);end=struct.unpack("<64Q",raw[-512:])
    if head[:5]!=(int.from_bytes(b"MIXORDR1","little"),1,512,128,512): return False
    if not 1<=head[5]<=4194304 or head[6:9]!=(80000,64,512): return False
    if head[9]>=64 or head[9]&33!=33 or any(head[10:16]+head[32:64]): return False
    if end[0]!=int.from_bytes(b"MIXOEND1","little") or end[1]!=1: return False
    if end[2]>(head[5]) or end[2]!=(len(raw)-1024)//128 or end[5]!=end[2]: return False
    if end[2]+end[4]>MAX or end[2]+end[4]!=end[3]: return False
    if end[35]!=head[5] or end[34]>4194336 or end[10]<end[6] or end[11]<end[7]: return False
    if end[15]>=64 or end[33]>5 or end[31]>5 or end[32]>1: return False
    if any(end[44:64]) or end[36:44]!=head[16:24]: return False
    if end[12]==0:
        if (end[13],end[14],end[32])!=(0,MAX,0): return False
    elif not (1<=end[12]<=21 and 1<=end[13]<=24 and 1<=end[14]<=6 and end[32]==1): return False
    if end[9] not in (0,1): return False
    if end[15]!=head[9] or end[33]!=5: return False
    if end[9]==0 and end[4]!=0: return False
    if end[9]==1 and not (end[2]==head[5] and end[3]>end[2] and end[4]>0): return False
    return True

history=[]
for sidecar in sorted((SNAP/"inputs/historical").glob("*.sidecar.json")):
    historical=json.loads(sidecar.read_bytes())
    assert historical["status"]=="invalid" and historical["failure"]==15
    stream=sidecar.with_name(sidecar.name.replace(".sidecar.json",".bin"))
    observed=footer_observation(stream.read_bytes())
    history.append({"historical_sidecar":{"path":str(sidecar.relative_to(ROOT)),"sha256":sha(sidecar),"status":"invalid","failure":15,"unchanged":True},
                    "new_framing_observation":{"scope":"closed header/footer grammar only; event records and semantic prefix not validated","stream_sha256":sha(stream),"footer_grammar_observed":observed,"storedPrefixValidated":False,"fullReplayAccepted":False,"diagnostic_input_valid":False}})
assert len(history)==17
assert sum(row["new_framing_observation"]["footer_grammar_observed"] for row in history)==10

inventory=json.loads((SNAP/"logical-inventory.json").read_bytes())
expected={"wire":3072,"candidate":2048,"io":4096,"metadata":4096,"setup":12288,"control":8192,"report":8192}
assert inventory["reservations"]==expected
assert inventory["named_role_upper_total"]==14248
assert len(inventory["phases"])==22
for group,reservation in expected.items(): assert inventory["named_role_upper_by_group"][group]<=reservation
assert sum(expected.values())==41984 and 65536-sum(expected.values())==23552
assert sum(inventory["named_role_upper_by_group"].values())==14248

# These source reads were reviewed against all declarations, not inferred from
# test counts or a syntax-only recognizer. Reader/file helpers have their full
# role unions in dedicated I/O and metadata groups; other chains use control.
coverage={
 "error_and_outcomes":["error","ReplayOutcome::fixture_framing_observed","ReplayOutcome::stored_prefix_validated","ReplayOutcome::full_replay_accepted"],
 "arena":["Arena::new","Arena::new_with","Arena::range","Arena::get64","Arena::put64","Arena::get32","Arena::put32"],
 "budget":["Budget::new","Budget::replay","Budget::setup","Budget::io","Budget::report","Budget::used"],
 "files_and_transport":["Stamp::len","file_stamp","InputFile for File::stamp","InputFile for File::position","OutputFile for File::stamp","OutputFile for File::position","bounded_read","eof","Reader::new","Reader::take","Reader::words"],
 "framing_and_report":["fixture_context","profile","header","full_identity","record_fields","Framing::new","Framing::coordinate","footer","walk","initial","stable","output_safety","write_report","analyze_fixture","observe_inputs","analyze_core"]}
result={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "producer_source_sha256":sha(SNAP/"src/analyzer.rs"),"producer_inventory_sha256":sha(SNAP/"logical-inventory.json"),
 "source_review_complete_for_selected_foundation":True,"declaration_coverage":coverage,
 "inventory":{"source_matches_named_roles":True,"groups":inventory["named_role_upper_by_group"],"named_role_upper_total":14248,"reserved_total":41984,"unassigned_margin_unused":23552,"phases":22,
 "complete_roles_reviewed":["four retained caller File objects and four entry borrows","Vec/Arena allocation, reserve Results, allocator error, produced/returned/wrapper/caller moves","every complete Metadata, Stamp, IO error/Result and helper return/caller place","all fixed raw/decoded/header/row/report arrays and literal/iterator temporaries","all Region/Option/Range/access checks and nested Budget/error/get-put helper chains","profile/context/stream lexical phases plus final metadata checks","fixed Outcome/Error and complete public/core/caller Result/return moves","arena-backed report and complete partial-write/error/final-metadata owners"],
 "qualification":"conservative named logical source inventory only; excludes opaque stdlib/allocator/kernel internals, optimizer copies, physical stack/TLS/RSS and test harness"},
 "upper_step_arithmetic":{"arena_init":1048576,"all_setup_cap":65536,"profile_rows":640000,"maximum_framing_records":4194304*22,"reserved_input_attempts":263584,"entire_report_reserve":3000000,"conservative_total":1048576+65536+640000+4194304*22+263584+3000000,"ceiling":268435456,"meaning":"bounded framing only, no semantic/FSM metrics work"},
 "historical_sidecars":history,"historical_sidecars_invalid_failure15":17,"new_footer_grammar_refused":7,"new_footer_grammar_only_observed":10,
 "storedPrefixValidated":False,"fullReplayAccepted":False,"producer_modified":False,"workload_or_native_execution":False}
(OWN/"inventory-and-history-review.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps({"passed":True,"reviewed_declarations":sum(map(len,coverage.values())),"inventory_phases":22,"named_role_upper":14248,"historical_sidecars_invalid_failure15":17,"new_footer_grammar_only_observed":10,"new_footer_grammar_refused":7,"step_upper":result["upper_step_arithmetic"]["conservative_total"]}))
