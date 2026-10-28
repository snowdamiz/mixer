#!/usr/bin/env python3
"""Read-only retained-receipt/byte review; no producer import or runtime probe."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PACKET = REPO / "verification/hosted-dependency-advisory-correction"
V4 = PACKET / "resolution-v4"
ATTEMPT = V4 / "attempts/fe41774456c8435e841b30f9b48cb7ec"
ROOT_RELEASE = REPO / "verification/console-session-and-checkout-root-review/hosted-dependency-resolution-v4-release.json"
PLAN_SHA = "150cee180b4cfe30a7dc293b9f041308cd0c06ec4cb69b65a200f77a1bf300c4"
CONTROLLER_SHA = "e04b71aaab35d748acc6aa87f933699262fe33a24c4400006c64c22a9da3e411"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while raw := source.read(262144):
            assert time.monotonic() - START < 55
            digest.update(raw)
    return digest.hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result
        result[key] = value
    return result


def read(path):
    assert path.stat().st_size <= 1048576
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def sealed(path, expected, count):
    assert sha(path) == expected
    names = []
    for line in path.read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert sha(path.parent / name) == digest
        names.append(name)
    assert len(names) == len(set(names)) == count


def lock_lines(path):
    lines = path.read_bytes().splitlines(keepends=True)
    assert lines[0] == b"%{\n" and lines[-1] == b"}\n" and len(lines) == 23
    result = {}
    pattern = rb'  "([a-z0-9_]+)": \{:hex, :([a-z0-9_]+), "([0-9.]+)", "([a-f0-9]{64})", (.*), "hexpm", "([a-f0-9]{64})"\},\n'
    for line in lines[1:-1]:
        match = re.fullmatch(pattern, line)
        assert match and match[1] == match[2] and match[1].decode() not in result
        result[match[1].decode()] = {"raw": line, "version": match[3].decode(),
            "inner_checksum": match[4].decode(), "requirements_and_build_tools": match[5],
            "outer_checksum": match[6].decode(), "entry_sha256": hashlib.sha256(line).hexdigest()}
    assert len(result) == 21
    return result


def main():
    assert sha(ROOT_RELEASE) == "b457145519fd441cad164ffbed74c54121c826104a824c961b59ab1420382eab"
    release = read(ROOT_RELEASE)
    plan = read(V4 / "resolution-plan-v4.json")
    assert sha(V4 / "resolution-plan-v4.json") == PLAN_SHA
    assert sha(V4 / "controller.py") == CONTROLLER_SHA
    sealed(V4 / "seal.sha256", "fae9e276517ea6c197d6be35ed4b0a87c7ef7c1df4d1fb6ce3af04ffb1bfbe0d", 6)
    sealed(PACKET / "resolution-v3/seal.sha256", "87585b5b9817e1840162d0d792bbfbb7af485d3b1c6fa75773087c46bc4e3eb0", 6)
    sealed(PACKET / "resolution-v2/seal.sha256", "234e19f6e0367d9f90f33205f78b2972ecf22619a8b04b23e848e0ac3b57aadd", 5)
    sealed(PACKET / "preparation-seal.sha256", "26d5a93adf36bfb18acf8b986bbbeb285103a599e57a1944e25775c8002d96d7", 16)
    assert release["argv"][1:] == ["-B", "verification/hosted-dependency-advisory-correction/resolution-v4/controller.py", "--root-release", "--plan-sha256", PLAN_SHA]
    assert release["canonical_edits_released"] is False and release["product_tests_or_app_released"] is False
    assert type(release["automatic_retries"]) is int and release["automatic_retries"] == 0
    assert type(release["wall_seconds"]) is int and release["wall_seconds"] == 55
    for key in ["plan", "controller", "seal", "independent_review"]:
        pin = release[key]
        path = REPO / pin["path"]
        assert path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"]
    preparation = read(PACKET / "preparation-receipt.json")
    for name, expected in plan["packet_inputs"].items():
        assert sha(PACKET / name) == expected
    for pin in plan["additional_pinned_sources"]:
        assert sha(Path(pin["path"])) == pin["sha256"]
    for name, pin in preparation["selected_inputs"].items():
        assert sha(REPO / name) == pin["sha256"]
    for pin in preparation["tool_files"]:
        assert sha(Path(pin["path"])) == pin["sha256"]
    archive = preparation["installed_hex_archive"]
    for name, pin in archive["files"].items():
        assert sha(Path(archive["root"]) / name) == pin["sha256"]
    prior_dir = REPO / "verification/hosted-dependency-advisory-review"
    prior = preparation["prior_advisory_packet"]
    assert sha(prior_dir / "seal.sha256") == prior["seal_sha256"]
    for pin in prior["entries"]:
        assert sha(prior_dir / pin["path"]) == pin["sha256"]
    receipt = read(ATTEMPT / "receipt.json")
    inventory = read(ATTEMPT / "lock-inventory.json")
    assert receipt["status"] == "resolved_two_pins_only" and receipt["errors"] == []
    assert receipt["source_revision"] == preparation["source_revision"] and receipt["source_tree"] == preparation["source_tree"]
    assert receipt["controller_sha256"] == CONTROLLER_SHA and receipt["plan_sha256"] == PLAN_SHA
    assert receipt["preparation_receipt_sha256"] == plan["packet_inputs"]["preparation-receipt.json"]
    assert receipt["groups_closed"] is True and receipt["scratch_removed"] is True
    assert receipt["canonical_and_prior_packet_unchanged"] is True
    assert receipt["cancelled_through_cutoff"] is False and receipt.get("cancelled", False) is False
    assert receipt["stop_signals_pending_at_cutoff_snapshot"] == [] and receipt.get("handled_stop_signals", []) == []
    assert receipt["attempt"] == str(ATTEMPT) and receipt["scratch"] == str(ATTEMPT / "scratch")
    assert not (ATTEMPT / "scratch").exists()
    assert receipt["environment"] == {key: value.replace("${OPERATION_SCRATCH}", str(ATTEMPT / "scratch")) for key, value in plan["environment"].items()}
    assert receipt["resolver_policy"] == {"ERL_INETRC": str(ATTEMPT / "scratch/inetrc"), "lookup": ["dns", "file"], "native_fallback": False, "sha256": plan["packet_inputs"]["resolution-v4/inetrc"]}
    assert receipt["phase_offsets_seconds"] == {"cleanup":46,"posthash":52,"receipt":55,"work":40}
    hashes_finished = receipt["all_output_and_source_hashing_finished_elapsed_seconds"]
    cutoff = receipt["signal_observation_cutoff_elapsed_seconds"]
    ended = receipt["ended_elapsed_seconds"]
    assert 0 < hashes_finished <= cutoff <= ended < 52 < 55
    expected_names = {"receipt.json", "actual-mix.lock", "lock-inventory.json"}
    expected_names.update(command["name"] + suffix for command in plan["commands"] for suffix in [".stdout", ".stderr"])
    assert stat.S_ISDIR(ATTEMPT.lstat().st_mode)
    assert {path.name for path in ATTEMPT.iterdir()} == expected_names
    execution_files = []
    for path in sorted(ATTEMPT.iterdir()):
        assert stat.S_ISREG(path.lstat().st_mode)
        execution_files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha(path)})
    assert set(receipt["retained_output_hashes"]) == expected_names - {"receipt.json"}
    for name, pin in receipt["retained_output_hashes"].items():
        assert sha(ATTEMPT / name) == pin
    assert receipt["groups"] == receipt["commands"] and len(receipt["commands"]) == 5
    pids, previous_end = [], 0
    for command, observed in zip(plan["commands"], receipt["commands"]):
        assert observed["name"] == command["name"] and observed["argv"] == command["argv"]
        assert observed["custody_confirmed"] is True and observed["closed"] is True
        assert type(observed["returncode"]) is int and observed["returncode"] == 0
        assert observed["pid"] == observed["pgid"] == observed["sid"] and type(observed["pid"]) is int
        pids.append(observed["pid"])
        witness = observed["WNOWAIT_exit_observed"]
        assert witness["pid"] == observed["pid"] and witness["status"] == 0 and witness["code"] == 1
        assert previous_end <= observed["start_elapsed_seconds"] <= witness["elapsed_seconds"] <= observed["cleanup_elapsed_seconds"] <= observed["end_elapsed_seconds"] < 40
        previous_end = observed["end_elapsed_seconds"]
        assert observed["reap_path"] == "WNOWAIT-exited: reap without signals, then observe group absence"
        assert not observed.get("signals") and not observed.get("cleanup_refused") and not observed.get("cleanup_error")
        assert observed["scratch_size"]["bytes"] <= 268435456 and observed["scratch_size"]["entries"] <= 10000
        for stream in ["stdout", "stderr"]:
            pin = observed[stream]
            assert pin["path"] == command["name"] + "." + stream
            path = ATTEMPT / pin["path"]
            assert path.stat().st_size == pin["bytes"] <= 262144 and sha(path) == pin["sha256"]
            if stream == "stderr":
                assert pin["bytes"] == 0
    assert len(set(pids)) == 5
    assert len(receipt["syscall_trace"]) <= 32
    assert not any(call["call"] == "os.killpg(abort_unreaped_running_group)" for call in receipt["syscall_trace"])
    assert receipt["scratch_size"]["bytes"] <= 268435456 and receipt["scratch_size"]["entries"] <= 10000
    before = lock_lines(PACKET / "inputs/mix.lock")
    after = lock_lines(ATTEMPT / "actual-mix.lock")
    assert before.keys() == after.keys()
    changed = sorted(name for name in before if before[name]["raw"] != after[name]["raw"])
    assert changed == ["bandit", "jose"]
    official = {entry["package"]: entry for entry in read(prior_dir / "upgrade-candidates.json")}
    targets = {"bandit":"1.14.0", "jose":"1.11.13"}
    for name, version in targets.items():
        assert after[name]["version"] == official[name]["version"] == version
        assert after[name]["outer_checksum"] == official[name]["metadata"]["checksum"]
        assert after[name]["requirements_and_build_tools"] == before[name]["requirements_and_build_tools"]
    assert inventory == receipt["lock_inventory"] and inventory["verified"] is True
    assert inventory["entry_count"] == 21 and inventory["unchanged_other_entries"] == 19
    assert inventory["changed"] == changed
    expected_entries = {name:{key:value for key,value in entry.items() if key not in {"raw","requirements_and_build_tools"}} for name,entry in after.items()}
    assert inventory["entries"] == expected_entries
    unchanged = {name:{"before":before[name]["entry_sha256"],"after":after[name]["entry_sha256"]} for name in before if name not in targets}
    assert len(unchanged) == 19 and inventory["unchanged_other_entry_hashes"] == unchanged
    assert all(value["before"] == value["after"] for value in unchanged.values())
    assert inventory["official_candidate_outer_checksums"] == {name:official[name]["metadata"]["checksum"] for name in targets}
    assert receipt["retained_lock_sha256"] == sha(ATTEMPT / "actual-mix.lock") == "1eada39dcaf4863d02d39f51e218d2bad8908b36a0cba47ff2d16037b7bcf837"
    assert "Elixir 1.20.4" in (ATTEMPT / "elixir-tool-version.stdout").read_text()
    assert "Mix 1.20.4" in (ATTEMPT / "mix-tool-version.stdout").read_text()
    assert all("Erlang/OTP 29" in (ATTEMPT / name).read_text() for name in ["elixir-tool-version.stdout", "mix-tool-version.stdout"])
    resolve_text = (ATTEMPT / "resolve-and-fetch-private-dependencies.stdout").read_text()
    offline_text = (ATTEMPT / "offline-locked-recheck.stdout").read_text()
    assert "New:\n  bandit 1.14.0\n  jose 1.11.13\nUnchanged:\n" in resolve_text
    assert "All dependencies have been fetched" in offline_text
    assert str(ATTEMPT / "scratch/mix-home/elixir/1-20-otp-29/rebar3") in resolve_text
    result = {"schema":1,"status":"independent-terminal-resolution-review-passed-for-integration-and-ordinary-CI",
        "created_at":datetime.now(timezone.utc).isoformat(),"python":sys.version,
        "command":"python3 -B verification/hosted-dependency-advisory-correction-independent/runtime-review-1/audit_terminal.py",
        "script_sha256":sha(Path(__file__)),"root_release_sha256":sha(ROOT_RELEASE),
        "controller_sha256":CONTROLLER_SHA,"plan_sha256":PLAN_SHA,
        "receipt_sha256":sha(ATTEMPT / "receipt.json"),"actual_mix_lock_sha256":sha(ATTEMPT / "actual-mix.lock"),
        "lock_inventory_sha256":sha(ATTEMPT / "lock-inventory.json"),"execution_files":execution_files,
        "source_revision":receipt["source_revision"],"source_tree":receipt["source_tree"],
        "terminal_elapsed_seconds":ended,"leader_PIDs_recorded_reaped_groups_closed":pids,
        "nonzero_cleanup_signals":0,"scratch_absent_by_readonly_filesystem_check":True,
        "generated_lock_entries":21,"changed_packages":targets,"complete_other_entries_byte_identical":19,
        "target_outer_checksums_match_saved_official_Hex_metadata":True,
        "tools_observed":{"elixir":"1.20.4","mix":"1.20.4","OTP":"29 / erts-17.1","Hex_selected_pinned":"2.5.1"},
        "private_rebar3_download_staging_visible_in_deps_get_stdout":True,
        "sourcebound_assertions":"Success after unchanged offline lock check, verified private inetrc/project before every child, unchanged inputs/tools/archive/packet and scratch cleanup; no process probe repeated.",
        "verified_pin_counts":{"packet":len(plan["packet_inputs"]),"additional":len(plan["additional_pinned_sources"]),"canonical":len(preparation["selected_inputs"]),"tools":len(preparation["tool_files"]),"Hex_archive":len(archive["files"]),"advisory":len(prior["entries"])},
        "findings":[],"recommend_root_apply_two_versions_actual_lock_and_dependency_inventory":True,
        "recommend_ordinary_remote_CI":True,"integration_or_product_test_or_GA_pass":False,
        "independent_controller_replay_or_runtime_process_DNS_probe_invocations":0,
        "limitations":"Retained source-bound receipt review; no independent live process probe, network/TLS transcript, actual cancellation/EPERM fault injection, product compilation/test, CI or HTTP2 qualification.",
        "elapsed_seconds":round(time.monotonic()-START,6)}
    (OUT / "audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({key:value for key,value in result.items() if key != "execution_files"},indent=2))


if __name__ == "__main__":
    main()
