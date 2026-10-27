import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(name,value):(ROOT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
commands=json.loads((ROOT/"command-receipts.json").read_bytes())["commands"]
assert len(commands)==14 and all(x["terminal_reaped"] for x in commands)
assert all(x["exit_code"]==x["expected_exit"] for x in commands)
for variant in ("old","corrected"):
    result=json.loads((ROOT/"replay"/variant/"replay/test-results.json").read_bytes())
    assert result["methods"]==26 and result["failures"]==result["errors"]==result["skips"]==0
    assert any(x.get("snapshot_leaf_mutations")==307 for x in result["observations"])
stdio=json.loads((ROOT/"logs/independent-stdio-close.stdout").read_bytes())
assert stdio["known_owned_stream_remains_open"] and stdio["snapshot"]["healthy_zero"] and stdio["raised_exception_is_stdio_fault"]
assert not stdio["primary_is_preserved_as_aggregate_primary"]
python=Path(os.path.realpath(sys.executable))
receipt={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"independent bounded correction/source/host evidence review", "disposition":"R01 and retained-wrapper R02 scoped positive; required terminal stdio correction; complete acceptance withheld", "input_seal_sha256":"57591c504fadfb0c22e44e37d6333cab53b8d62e39da14e97f0cdfd2fed455f1","input_members":476,"producer_source_tree_sha256":"3b78a8a719ab18856919ca5c201a403ccfb6223cbd012e6c1a39c5c11d3cacd6","source_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip(),"committed_tree":subprocess.check_output(["git","rev-parse","HEAD^{tree}"],cwd=REPO,text=True).strip(),"tool":{"python_executable":str(python),"python_sha256":sha(python),"python_version":sys.version,"platform":platform.platform()},"fresh_child_commands":14,"producer_methods_each":26,"snapshot_leaf_mutations_each":307,"fresh_independent_pass":5,"fresh_independent_required_failure":1,"raw_old_required_failures":3,"raw_corrected_R01_pass":True,"raw_corrected_R02_failure_error_outcomes_preserved":2,"retained_142_case_evidence_audited_not_freshly_executed":True,"all_bounded_children_terminal_reaped":True,"parent_owned_scratch_entries_final":0,"uncertain_case_nonzero_states_at_process_exit_preserved":True,"known_open_stdio_false_zero_observation_preserved":True,"actual_OS_close_ambiguity_resolution":False,"actual_Rust_binding_or_layout_work_lifetime_qualification":False,"native_UI_capture_process_inventory":False,"prohibited_hosted_read_import_execution":False,"canonical_original_packet_edits_commit_push_publication":False,"real_binding_native_OTA_GA_accepted":False}
dump("receipt.json",receipt)
members=[]
for path in sorted(ROOT.rglob("*")):
    if path.is_file() and path.name not in ("seal.json","seal.sha256"):
        assert not path.is_symlink() and "__pycache__" not in path.parts
        members.append({"path":str(path.relative_to(ROOT)),"bytes":path.stat().st_size,"sha256":sha(path)})
dump("seal.json",{"schema":1,"scope":"independent finite lifecycle correction review; one required terminal stdio failure retained","member_count":len(members),"members":members,"self_seal_metadata":{"path":"seal.sha256","bytes":76,"exact_content":"lowercase SHA256 of seal.json + two ASCII spaces + seal.json + LF"},"product_real_binding_native_OTA_GA_accepted":False})
digest=sha(ROOT/"seal.json")
(ROOT/"seal.sha256").write_text(digest+"  seal.json\n")
print(json.dumps({"member_count":len(members),"seal_sha256":digest,"independent_pass":5,"independent_required_failure":1,"producer_replay_methods_each":26},sort_keys=True))
