"""Copy only verified frozen members; no source/oracle edits or producer builder."""
import difflib
import json
from pathlib import Path
from verify_inputs import ROOT, REPO, verify, sha, dump


if __name__ == "__main__":
    packets = verify()
    correction = REPO / packets["correction"]["path"]
    original = REPO / packets["original_independent"]["path"]
    copies = []
    def copy(source, target):
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        target.write_bytes(data)
        copies.append({"source": str(source.relative_to(REPO)), "copy": str(target.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)})
    for variant in ("old", "new"):
        for name in ("prototype.py", "schema.py", "consumer.py", "test_preparation.py"):
            copy(correction / variant / "replay/corrected/replay" / name, ROOT / variant / "replay/corrected/replay" / name)
    for name in ("boundary_case.py", "mixed_child_case.py"):
        copy(original / name, ROOT / name)
    copy(original / "boundary_case.py", ROOT / "old-independent/boundary_case.py")
    copy(correction / "old/replay/corrected/replay/prototype.py", ROOT / "old-independent/new/replay/corrected/replay/prototype.py")
    copy(correction / "boundary_case.py", ROOT / "producer_boundary_case.py")
    old = (ROOT / "old/replay/corrected/replay/prototype.py").read_bytes()
    new = (ROOT / "new/replay/corrected/replay/prototype.py").read_bytes()
    assert sha(old) == "54d8b967b996ff273039824fffa6042e9ca9ef383079ce1427aadf45f23114a1"
    assert sha(new) == "af8d04f4940bca83c341d72970ef088852e27919305cda7aa7d53396ea2d2ccf"
    needle = b'        raise Refusal("stdio-read-attempts","stdio-access")\n'
    assert old.count(needle) == 1
    assert new == old.replace(needle, b'        if remaining==0:return b"".join(parts)\n' + needle)
    for name in ("schema.py", "consumer.py", "test_preparation.py"):
        assert (ROOT / "old/replay/corrected/replay" / name).read_bytes() == (ROOT / "new/replay/corrected/replay" / name).read_bytes()
    patch = "".join(difflib.unified_diff(old.decode().splitlines(True), new.decode().splitlines(True), fromfile="old/prototype.py", tofile="new/prototype.py"))
    (ROOT / "independently-computed.patch").write_text(patch)
    commands = json.loads((correction / "commands.json").read_text())
    assert len(commands) == 90
    for command in commands:
        assert not command["timeout"] and command["terminal_reaped"] and command["exit"] == command["expected_exit"]
        for stream in ("stdout", "stderr"):
            value = command[stream]
            data = (correction / value["path"]).read_bytes()
            assert len(data) == value["bytes"] and sha(data) == value["sha256"]
    result = json.loads((correction / "results.json").read_text())
    assert len(result["boundary"]) == 32 and len(result["stdio"]) == 57
    assert sum(not x["required_behavior_pass"] for x in result["boundary"]) == 3
    assert all(x["required_behavior_pass"] for x in result["boundary"] if x["variant"] == "new")
    dump(ROOT / "source-custody.json", {"schema": 1, "copies": copies, "single_line_delta_verified": True, "test_bodies_and_oracles_byte_identical": True})
    dump(ROOT / "retained-evidence-audit.json", {"schema": 1, "correction_commands_stream_hashes_and_terminal_dispositions_verified": 90, "old_required_R03_failures_retained": 3, "new_boundary_cases_audited": 16, "stdio_cases_audited": 57, "stdio_healthy_zero": 5, "stdio_unresolved": 52, "classification": "retained evidence audit, not independent fresh execution"})
    dump(ROOT / "initial-custody-assumption.json", {"schema": 1, "earlier_tool_only_custody_attempt": "all201 member lengths/hashes verified, then an undeclared seal.sha256 lookup raised FileNotFoundError", "cause": "reviewer initially assumed previous packet's76-byte selfseal-sidecar convention", "correction": "root201 seal declares201 members,member_bytes757707 and no selfseal sidecar; exact layout201members plus seal.json verifies", "product_or_packet_failure": False, "source_imported_before_corrected_custody": False})
    print(json.dumps({"verified_copies": len(copies), "single_line_delta_verified": True, "retained_commands_audited": 90}, sort_keys=True))
