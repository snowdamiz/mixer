"""Offline own-packet audit. This cannot accept real binding or any release."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    evidence=json.loads((HERE/"source-evidence.json").read_text())
    for row in evidence["files"]:
        data=(HERE/row["copy"]).read_bytes()
        assert len(data)==row["bytes"] and sha(data)==row["sha256"],row["path"]
    declarations=b"#![allow(dead_code)]\n"
    for part in evidence["actual_data_declarations"]["fragments"]:
        source=HERE/"inputs"/part["path"]
        a,b=part["first_line"],part["last_line"]
        declarations+=f"// Exact {part['path']}:{a}-{b}\n".encode()+b"".join(source.read_bytes().splitlines(keepends=True)[a-1:b])
    assert declarations==(HERE/"actual_data_records.rs").read_bytes()
    assert sha(declarations)==evidence["actual_data_declarations"]["sha256"]
    custody=json.loads((HERE/"input-custody.json").read_text())
    assert len(custody["packets"])==9 and len(custody["receipts"])==5
    assert sum(p["members_verified"] for p in custody["packets"])==6753
    assert sum(p["bytes_verified"] for p in custody["packets"])==662544207
    receipt=json.loads((HERE/"receipt.json").read_text())
    commands=json.loads((HERE/"command-receipts.json").read_text())
    assert len(commands)==receipt["commands"]==7
    for command in commands:
        assert command["exit_code"]==0 and command["terminally_waited"]
        for stream in ("stdout","stderr"):
            source=Path(command[stream]["path"])
            # Input receipt paths remain absolute for exact executed evidence.
            data=(HERE/"logs"/source.name).read_bytes()
            assert sha(data)==command[stream]["sha256"] and len(data)==command[stream]["bytes"]
    for mode in ("debug","optimized"):
        output=(HERE/"logs"/("typed-data-"+mode+".stdout")).read_text()
        assert "14 passed; 0 failed; 0 ignored" in output
    python=(HERE/"logs/context-contract.stderr").read_text()
    assert "Ran 12 tests" in python and "\nOK\n" in python
    assert receipt["scratch_removed"] and not receipt["real_binding_semantic_replay_native_OTA_GA_accepted"]
    for name,record in receipt["source_inputs"].items():
        assert sha((HERE/name).read_bytes())==record["sha256"]
    roster=json.loads((HERE/"migration-roster.json").read_text())
    assert 140+len(roster["proposed_new_distribution_sources"])==148
    assert 11+len(roster["proposed_new_host_support"])==17
    for category in ("proposed_new_distribution_sources","proposed_new_host_support"):
        paths=roster[category];assert len(set(paths))==len(paths)
        assert all(not Path(p).is_absolute() and ".." not in Path(p).parts for p in paths)
    result={"scope":"own closed data-contract packet only","captured_files_or_excerpts":len(evidence["files"]),"exact_actual_source_declarations_verified":True,"all_seven_recorded_host_commands_pass":True,"rust_data_methods_each_mode":14,"python_context_methods":12,"source_roster_proposal_arithmetic_verified":True,"real_exporter_loader_selection_context_admission_or_GA_accepted":False}
    (HERE/"audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))

if __name__=="__main__":main()
