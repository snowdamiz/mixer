"""Record this packet's finite host controls and freeze all owned evidence."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCES = ("schema.py", "prototype.py", "consumer.py", "test_preparation.py", "run_evidence.py", "protocol-types.rs", "contract.md", "test-plan.md", "dependencies.json", "README.md")
INPUTS = (
    "AGENTS.md", "PLAN.md", "STATUS.md", "mixer-product-plan.md",
    "verification/swift-profile-header-preparation/proposed-contract.md",
    "verification/swift-profile-header-preparation/test-plan.md",
    "verification/swift-profile-header-preparation/contract.json",
    "verification/swift-semantic-adapter-root-review/profile-header-selected-amendments.md",
    "verification/swift-semantic-adapter-root-review/initial-profile-component-acceptance.json",
    "verification/swift-semantic-adapter-root-review/initial-profile-foundation-configuration-amendment.md",
    "verification/swift-semantic-adapter-root-review/initial-profile-source-action-scope-amendment.md",
    "verification/swift-initial-profile-construction-protocol/contract.md",
    "verification/swift-initial-profile-construction-implementation/source/vm/src/experimental/swift.rs",
    "verification/swift-initial-profile-construction-implementation/source/vm/src/experimental/metadata.rs",
    "verification/swift-initial-profile-construction-implementation/source/vm/src/experimental/account.rs",
    "verification/swift-initial-profile-construction-implementation/source/vm/src/experimental/policy.rs",
    "verification/swift-initial-profile-construction-implementation/source/vm/src/experimental/descriptors.rs",
    "verification/swift-initial-profile-construction-implementation/source/vm/src/experimental_wasi/descriptor.rs",
    "verification/swift-initial-profile-construction-implementation/source/vm/src/experimental_swift_reactor/control.rs",
    "verification/swift-initial-profile-construction-implementation/source/vm/src/experimental_swift_reactor/diagnostic_profile.rs",
    "verification/swift-initial-profile-construction-implementation/source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs",
    "verification/swift-initial-profile-construction-implementation/source/vm/src/experimental_swift_reactor/cache/initial_profile_v1/header.rs",
)


def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        buffer = bytearray(4096)
        while (n := file.readinto(buffer)):
            h.update(memoryview(buffer)[:n])
    return h.hexdigest()


def dump(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def main():
    historical = ROOT / "history" / "initial-21-methods"
    if not historical.exists() and (ROOT / "test-results.json").exists():
        historical.mkdir(parents=True)
        for name in ("host-tests.stdout", "host-tests.stderr", "test-results.json"):
            shutil.copyfile(ROOT / name, historical / name)
    inputs = []
    for name in INPUTS:
        source = REPO / name
        target = ROOT / "inputs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        inputs.append({"path": name, "bytes": target.stat().st_size, "sha256": sha_file(target)})
    accepted = next(x for x in inputs if x["path"].endswith("/initial-profile-component-acceptance.json"))
    if accepted["sha256"] != "77287c9659d8033450571f0a1aef4ccb02eacc513999cd6fdaa34f7746431a71":
        raise RuntimeError("predecessor acceptance changed; review required")
    dump("input-custody.json", {"schema": 1, "files": inputs, "copied_only_selected_inputs": True, "existing_scripts_replayed": False})
    caps = (131072, 131072, 67108864, 65536, 67108864, 262144, 16777216, 2560000)
    blocks = sum((n + 4095) // 4096 for n in caps)
    parent_blocks = 2 * blocks + 625 + 2 * 626 + 2 * 625
    parent_payload = 2 * sum(caps) + 2560000 + 2 * 2560512 + 2 * 2560000
    budget = {"schema": 1, "scope": "finite fixture composer explicit API calls/requested bytes; not VM/CPU/heap/RSS allowance", "input_byte_caps_in_slot_order": list(caps), "parent_buffer":4096, "child_buffer":4096, "header_bytes":512, "body_bytes":2560000, "profile_bytes":2560512, "per_block_attempts":32, "parent_exact_eof_passes":21, "parent_read_calls_max":32 * (parent_blocks + 21), "parent_read_requested_bytes_max":32 * (parent_payload + 21), "parent_write_calls_max":32 * 626, "parent_write_requested_bytes_max":32 * 2560512, "child_read_calls_max":32 * (626 + 625 + 625 + 3), "child_read_requested_bytes_max":32 * (2560512 + 2 * 2560000 + 3), "input_output_guards_max":9, "path_components_per_guard_max":64, "visible_retained_descriptors_max":9 * 65, "owned_child_stdio_descriptors":2, "complete_profile_and_subrange_hashes_each":2, "pre_post_hashes_per_input":2, "parent_digest_payload_inventory_conservative":24 * 32, "hash_hex_payload_inventory_conservative":24 * 64, "stdio_read_payload_max":2 * 512, "additional_real_transport_result_receipt_inputs_included":False, "actual_internal_retries_cpu_elapsed_heap_bound":False, "capacity_or_vm_limit_changed":False}
    dump("budget.json", budget)
    source_entries = [{"path": name, "bytes": (ROOT / name).stat().st_size, "sha256": sha_file(ROOT / name)} for name in sorted(SOURCES)]
    preimage = b"retained-profile-preparation-source-v1\n" + b"".join((x["path"] + "\0" + str(x["bytes"]) + "\0" + x["sha256"] + "\n").encode() for x in source_entries)
    command = [sys.executable, "-B", "test_preparation.py"]
    started = time.monotonic()
    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (ROOT / "host-tests.stdout").open("wb") as out, (ROOT / "host-tests.stderr").open("wb") as err:
        result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err, timeout=60, env={**os.environ, "PYTHONDONTWRITEBYTECODE":"1"})
    tests = json.loads((ROOT / "test-results.json").read_text())
    receipt = {"schema":1,"at":at,"scope":"synthetic finite host preparation only","command":command,"cwd":str(ROOT),"exit_code":result.returncode,"elapsed_seconds":time.monotonic()-started,"tool":{"python_executable":os.path.realpath(sys.executable),"python_sha256":sha_file(Path(os.path.realpath(sys.executable))),"python_version":sys.version,"platform":platform.platform()},"git":{"head":git("rev-parse","HEAD"),"committed_tree":git("rev-parse","HEAD^{tree}"),"selected_working_sources_are_new_uncommitted_packet":True},"source_tree_sha256":hashlib.sha256(preimage).hexdigest(),"source_tree_preimage":"retained-profile-preparation-source-v1 LF then sorted listed path NUL decimal bytes NUL lowercase sha256 LF; SOURCES list order as retained","source_entries":source_entries,"stdout_sha256":sha_file(ROOT / "host-tests.stdout"),"stderr_sha256":sha_file(ROOT / "host-tests.stderr"),"tests":tests,"native_ui_capture_processes_started":False,"process_inventory_performed":False,"canonical_product_changed":False,"commit_or_push_performed":False,"actual_rust_snapshot_exporter_tested":False,"real_context_or_binding_accepted":False,"cleanup":{"owned_retained_descriptors_final":tests["owned_descriptor_registry_final"],"owned_stdio_contexts_final":tests["owned_stdio_registry_final"],"child_quarantines_final":tests["owned_child_quarantines_final"],"owned_scratch_entries_final":tests["owned_scratch_entries_final"],"fixed_successful_children_terminal_reaped":True,"stuck_os_reap_quarantine_branch":"source-only; no stuck child created"}}
    dump("receipt.json", receipt)
    if result.returncode != 0:
        return result.returncode
    members = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name not in ("seal.json", "seal.sha256") and "__pycache__" not in path.parts:
            members.append({"path":str(path.relative_to(ROOT)),"bytes":path.stat().st_size,"sha256":sha_file(path)})
    dump("seal.json", {"schema":1,"scope":"preparation proposal and synthetic finite host witnesses; no product selection","members":members,"member_count":len(members),"native_runtime_real_binding_ota_ga_accepted":False})
    (ROOT / "seal.sha256").write_text(sha_file(ROOT / "seal.json") + "  seal.json\n")
    print(json.dumps({"methods":tests["methods"],"failures":tests["failures"],"errors":tests["errors"],"members":len(members),"seal_sha256":sha_file(ROOT / "seal.json"),"source_tree_sha256":receipt["source_tree_sha256"],"cleanup":receipt["cleanup"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
