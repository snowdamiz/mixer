"""Independent exact-run failed-preflight audit. Data only; no subject import."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import types
import json
import hashlib
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = HERE / "local/actual-40854344723"
EXTRACTED = BASE / "extracted"
LOG = ROOT / "verification/android-view-api-focused-host-selection-2026-10-29/local/host-observations/focused-job.log"
METADATA = LOG.parent / "manual-resolution-001.json"


def own(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec", dont_inherit=True), module.__dict__)
    return module


guard = own(HERE / "guarded_inspector.py", "actual_failure_guard")
guard_record = guard.install_guards()
data = guard.load_data_module(HERE / "audit_data.py", "actual_failure_data")
report = {"schema": 1, "scope": "independent source-bound actual failed-preflight artifact/log audit; no subject import",
          "command": list(sys.orig_argv), "python": {"executable": sys.executable, "version": sys.version},
          "guard": guard_record, "subject_inspector_imports": 0, "reviewer_compiler_JVM_product_native_runs": 0,
          "additional_connector_or_consumer_requests": 0,
          "sources": [{"path": p.name, **data.identity(p.read_bytes())}
                      for p in (Path(__file__), HERE / "audit_data.py", HERE / "guarded_inspector.py")]}
try:
    binding = data.validate_binding(data.strict_json(data.read_regular(BASE / "binding.json", BASE)))
    raw = data.read_regular(BASE / "artifact.zip", BASE, maximum=4194304)
    files, inventory = data.inspect_zip(raw)
    data.need(inventory["archive"] == {"bytes": 108334, "sha256": "98fe0876073002377a76a2a721ab858b6dafe68165a5015e47ab8c597e58c294"}, "exact artifact")
    original_inventory = data.strict_json(data.read_regular(BASE / "archive-inventory.json", BASE))
    data.need(inventory == original_inventory, "ZIP inventory changed between phases")
    for row in inventory["members"]:
        data.need(data.identity(data.read_regular(EXTRACTED / row["path"], EXTRACTED)) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "raw/extracted identity disagreement")
    parsed = {name: data.strict_json(content) for name, content in files.items() if name.endswith(".json")}
    wp = "mixer/mixer/"
    output = "_temp/android-view-api-focused-40854344723-1/"
    expected_files = {output + name for name in ("receipt.json", "root-selection.json", "source-preflight.json")}
    expected_files.add("_temp/android-view-api-root-selection.json")
    reservation_name = "_temp/.mixer-view-api-custody-" + data.NONCE + ".reservation.json"
    expected_files.add(reservation_name)
    closed_sources = []
    for directory in (data.HOST, data.INSPECTOR):
        seal_name = wp + directory + "/seal.json"
        seal_bytes = files[seal_name]
        data.need(data.identity(seal_bytes)["sha256"] == data.PINS[directory + "/seal.json"], "uploaded seal pin")
        data.need(seal_bytes == data.read_regular(ROOT / directory / "seal.json", ROOT), "uploaded/frozen seal bytes")
        seal = parsed[seal_name]
        expected_files.add(seal_name)
        rows = []
        for row in seal["members"]:
            member = wp + directory + "/" + data.safe_name(row["path"])
            data.need(data.identity(files[member]) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "uploaded sealed member identity: " + member)
            data.need(files[member] == data.read_regular(ROOT / directory / row["path"], ROOT), "uploaded/frozen exact source bytes: " + member)
            expected_files.add(member)
            rows.append(row)
        closed_sources.append({"directory": directory, "sealed_members": len(rows), "seal": data.identity(seal_bytes)})
    data.need(set(files) == expected_files and len(files) == 35, "exact35 actual archive membership")
    manifest = parsed[wp + data.HOST + "/input-manifest.json"]
    frozen_rows = data.verify_rows(ROOT, manifest["members"])
    producer = data.strict_json(data.read_regular(ROOT / data.CANDIDATE / "manifest.json", ROOT))
    producer_rows = data.verify_rows(ROOT / data.CANDIDATE, producer["members"])
    product = {Path(row["path"]).name: {"bytes": row["bytes"], "sha256": row["sha256"]}
               for row in producer_rows if row["path"].startswith("source/")}
    data.need(len(frozen_rows) == 148 and len(producer_rows) == 115 and len(product) == 16
              and hashlib.sha256(data.canonical(product)).hexdigest() == data.TREE, "independent source148/candidate115/product16")
    product_paths = sorted("source/" + name for name in product)
    leaves = sorted(row["path"] for row in producer_rows if row["path"].startswith("tests/host-leaves/") and row["path"].endswith(".java"))
    data.need(len(leaves) == 86 and manifest["host_sources"] == sorted(product_paths + leaves + ["tests/ViewApiBoundaryTests.java"]), "exact host103")
    data.need(manifest["sdk_sources"] == sorted(product_paths + ["tests/cross-leaf/NativeBridge.java"]), "exact SDK17")
    observed_source = {"members": 148, "map_sha256": hashlib.sha256(data.canonical(manifest["members"])).hexdigest(),
                       "product_tree": data.TREE, "host_inputs": 103, "sdk_inputs": 17}
    receipt = parsed[output + "receipt.json"]
    data.need(parsed[output + "source-preflight.json"] == receipt["source_after"] == observed_source
              and receipt["source_unchanged"] is True, "source pre/final flight agreement")
    selection = parsed[output + "root-selection.json"]
    data.need(selection == parsed["_temp/android-view-api-root-selection.json"], "selection duplicate copies")
    template = data.strict_json(data.read_regular(ROOT / data.SELECTION / "host-selection-template.json", ROOT))
    template.update(github_sha=binding["delivered_head"], dispatch_selected=True)
    data.need(selection == template, "root selection differs beyond exact delivered head/selected flag")
    selection_hash = hashlib.sha256(data.canonical(selection)).hexdigest()
    data.need(receipt["selection"] == {"revision": binding["delivered_head"], "root_dispatch_nonce": data.NONCE,
              "run_attempt": 1, "run_id": "40854344723", "selection_sha256": selection_hash}, "receipt selection exact binding")
    reservation = parsed[reservation_name]
    data.need(reservation == {"schema": 1, "dispatch_nonce": data.NONCE, "github_sha": binding["delivered_head"],
              "run_id": "40854344723", "status": "reserved-once-no-restart", "total_children": 7}, "one-shot reservation exact binding")
    data.need(receipt["one_shot_reservation"] == {"path": "/home/runner/work/" + reservation_name,
              **data.identity(files[reservation_name]), "scope": "same runner temp filesystem only; retained forever for this session"}, "reservation byte custody")
    data.need(receipt["commands"] == [] and "attempted_commands" not in receipt, "any owned command attempt contradicts failure boundary")
    data.need(receipt["status"] == "refused-failure-retained" and receipt["runtime_accepted"] is False
              and receipt["errors"] == ["Refusal: official JDK runtime member changed: lib/ct.sym"], "exact failed-preflight boundary")
    data.need(receipt["native_ui_capture_phones"] is False and receipt["old_process_access_or_cleanup"] is False, "preserved resource holds")
    absent_fields = ["tools_before", "tools_after", "final_flight", "dex", "focused_groups", "frozen_finite_interruption_invocations"]
    data.need(all(name not in receipt for name in absent_fields), "no successful tool/focused/emission evidence may appear")
    profile = parsed[wp + data.HOST + "/tool-profile.json"]
    runtime_document = parsed[wp + data.HOST + "/jdk-runtime-members.json"]
    runtime_rows = runtime_document["members"] if type(runtime_document) is dict else runtime_document
    mismatch = [row for row in runtime_rows if row["path"] == "lib/ct.sym"]
    data.need(len(runtime_rows) == 74 and len(mismatch) == 1
              and data.identity(files[wp + data.HOST + "/jdk-runtime-members.json"])["sha256"] == profile["jdk_runtime_manifest_sha256"], "runtime74 expected member manifest")
    log_bytes = data.read_regular(LOG, ROOT, maximum=1048576)
    metadata_bytes = data.read_regular(METADATA, ROOT, maximum=1048576)
    data.need(data.identity(log_bytes) == {"bytes": 23598, "sha256": "b410162461294cba72cd424c95c8408905a97ce30f80cbdbb1bcc47937a17048"}, "root job log byte identity")
    data.need(data.identity(metadata_bytes)["sha256"] == "a651671119ab3349770dafd77fc7d06c67a18abaacf953fbf68c4abd62ae4904", "root metadata byte identity")
    metadata = data.strict_json(metadata_bytes)
    log = log_bytes.decode("utf-8", "strict")
    log_requirements = ["/usr/bin/python3 -I -B -S", "Process completed with exit code 1.",
                        "there will be 35 files uploaded", "98fe0876073002377a76a2a721ab858b6dafe68165a5015e47ab8c597e58c294",
                        "Final size is 108334 bytes. Artifact ID is 12888427668", binding["delivered_head"],
                        "focused admission failed; all evidence retained at /home/runner/work/_temp/android-view-api-focused-40854344723-1"]
    data.need(all(value in log for value in log_requirements), "root job log failure/upload binding")
    report.update(status="reviewed-actual-refused-initial-JDK-preflight-zero-owned-Java-children",
        exact_run_binding=binding, archive=inventory["archive"], archive_files=35, archive_total_uncompressed=inventory["total_bytes"],
        archive_member_map_sha256=inventory["member_map_sha256"], uploaded_sealed_sources=closed_sources,
        strict_JSON_documents=len(parsed), independently_rehashed_sources={"input_manifest": 148, "candidate": 115, "product": 16,
            "product_tree": data.TREE, "host_inputs": 103, "sdk_inputs": 17, "observed_source_preflight": observed_source},
        root_selection_canonical_sha256=selection_hash, reservation={"content": reservation, "identity": data.identity(files[reservation_name])},
        failure={"stage": "initial verify_tools(profile) JDK expected-file preflight", "exact_error": receipt["errors"][0],
            "expected_mismatched_member": mismatch[0], "actual_mismatched_bytes_or_hash_preserved": False,
            "interpretation": "The selected source reports exact JDK runtime file mismatch at lib/ct.sym. Actual provider file bytes/hash and actual Java versions are absent; cause/version/provenance is not independently established."},
        owned_commands={"attempted": [], "completed": [], "count": 0, "child_started": False,
            "unrun": data.COMMANDS, "custody_module_import_reached": False, "inspector_module_import_reached": False,
            "evidence": "Exact uploaded collector places initial verify_tools before plan/scratch/copies/custody/inspector/commands. Actual35 closed members contain only source-preflight/selection/failure receipt/reservation and frozen source packets."},
        absent_actual_evidence=["successful tool preflight snapshot", "actual version outputs", "plan", "scratch/copied inputs", "command/spawn/result/retirement records",
            "stdout/stderr EOF", "WNOWAIT/raw exact reap/ESRCH observations", "focused main/groups/assertion summary/interruption invocations", "class maps or bytes", "DEX bytes or inspection"],
        group_or_interruption_runtime_pass=False, actual_focused_group_count=0, actual_focused_assertion_count=None,
        actual_interruption_count=None, source_before_after_unchanged=True,
        source_output_origin_caveat="Source148 raw product members were not included by the upload; local frozen members were independently rehashed and paired with root exact delivered head/tree, matching uploaded manifest and runner source-pre/final reports. This is source-bound reported evidence, not independent kernel tracing or platform attestation.",
        root_log={"path": str(LOG), **data.identity(log_bytes)}, root_reduced_metadata={"path": str(METADATA), **data.identity(metadata_bytes)},
        provider_runtime_tool_qualification=False, native_ART_canonical_sourcepair_OTA_release_GA_qualification=False,
        prior_holds_untouched=True, retries_or_reruns_authorized=False,
        acquisition_caveat="One connector request and one consumer transfer; raw exact size/hash retained. Original consumer OSError at EOF bookkeeping preserved separately; no retry. Exact bytes reconciled before guarded audit.")
    data.need(data.identity(data.read_regular(BASE / "artifact.zip", BASE)) == inventory["archive"], "ZIP changed after actual audit")
    for row in inventory["members"]:
        data.need(data.identity(data.read_regular(EXTRACTED / row["path"], EXTRACTED)) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "extracted data changed after audit")
except BaseException as error:
    report.update(status="refused-independent-data-audit-retained", error=type(error).__name__ + ": " + str(error)[:2000])
(BASE / "failure-data-review-002.json").open("x").write(json.dumps(report, sort_keys=True, indent=2) + "\n")
print(json.dumps({k: report.get(k) for k in ("status", "failure", "owned_commands", "error")}))
if "error" in report:
    raise data.Refusal(report["error"])
