#!/usr/bin/env python3
"""Prepare source proposals and tool identities; never execute Erlang/Elixir/Mix."""
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT / "verification/hosted-dependency-advisory-review"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path):
    return {"path": str(path), "resolved_path": str(path.resolve()),
            "sha256": digest(path), "size_bytes": path.stat().st_size}


def prior_seal():
    entries = []
    for line in (PRIOR / "seal.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        actual = digest(PRIOR / name)
        assert actual == expected, name
        entries.append({"path": name, "sha256": actual})
    return {"seal_sha256": digest(PRIOR / "seal.sha256"), "entries": entries}


def main():
    frozen = prior_seal()
    names = ["hosted/mix.exs", "hosted/mix.lock", "THIRD_PARTY.yml", "hosted/.tool-versions",
             "hosted/test/mixer_hosted/billing/raw_webhook_capture_test.exs",
             "hosted/test/mixer_hosted/identity/access_token_verifier_test.exs",
             "hosted/test/mixer_hosted_web/customer_artifact_transport_test.exs",
             "hosted/test/mixer_hosted_web/customer_workspace_transport_test.exs",
             "hosted/test/mixer_hosted_web/customer_artifact_http_integration_test.exs",
             "hosted/test/mixer_hosted_web/customer_workspace_http_integration_test.exs",
             "hosted/test/test_helper.exs", ".github/workflows/hosted.yml",
             "hosted/lib/mixer_hosted/browser_auth/store.ex"]
    inputs = {name: record(ROOT / name) for name in names}
    original_mix = (ROOT / "hosted/mix.exs").read_text()
    original_third = (ROOT / "THIRD_PARTY.yml").read_text()
    proposed_mix = original_mix.replace('{:bandit, "== 1.13.1"}', '{:bandit, "== 1.14.0"}')
    proposed_mix = proposed_mix.replace('{:jose, "== 1.11.12"}', '{:jose, "== 1.11.13"}')
    assert original_mix.count('{:bandit, "== 1.13.1"}') == 1
    assert original_mix.count('{:jose, "== 1.11.12"}') == 1
    proposed_third = original_third
    for package, old, new in [("bandit", "1.13.1", "1.14.0"), ("jose", "1.11.12", "1.11.13")]:
        start = proposed_third.index("  - name: Hex " + package + "\n")
        end = proposed_third.index("  - name:", start + 1)
        block = proposed_third[start:end]
        assert block.count('version: "' + old + '"') == 1
        replacement = block.replace('version: "' + old + '"', 'version: "' + new + '"')
        lines = replacement.splitlines(keepends=True)
        assert sum("inventory_receipt:" in line for line in lines) == 1
        replacement = "".join(
            "    inventory_receipt: verification/hosted-dependency-advisory-correction/dependencies.json\n"
            if "inventory_receipt:" in line else line for line in lines)
        proposed_third = proposed_third[:start] + replacement + proposed_third[end:]

    for subdirectory in ["inputs", "proposal"]:
        (HERE / subdirectory).mkdir(exist_ok=False)
    for name in ["mix.exs", "mix.lock"]:
        shutil.copyfile(ROOT / "hosted" / name, HERE / "inputs" / name)
    shutil.copyfile(ROOT / "THIRD_PARTY.yml", HERE / "inputs/THIRD_PARTY.yml")
    (HERE / "proposal/mix.exs").write_text(proposed_mix)
    (HERE / "proposal/THIRD_PARTY.yml").write_text(proposed_third)
    patches = []
    for path, original, proposed in [("hosted/mix.exs", original_mix, proposed_mix),
                                     ("THIRD_PARTY.yml", original_third, proposed_third)]:
        patches.extend(difflib.unified_diff(original.splitlines(keepends=True),
                                          proposed.splitlines(keepends=True),
                                          fromfile="a/" + path, tofile="b/" + path))
    (HERE / "proposal.patch").write_text("".join(patches))

    scratch = HERE / "source-only-scratch"
    scratch.mkdir(mode=0o700, exist_ok=False)
    shutil.copyfile(ROOT / "hosted/mix.lock", scratch / "mix.lock")
    (scratch / "mix.exs").write_text(proposed_mix)
    scratch_inputs = {name: record(scratch / name) for name in ["mix.exs", "mix.lock"]}
    assert digest(scratch / "mix.lock") == inputs["hosted/mix.lock"]["sha256"]
    # Only these two source-only preparation files were created; no VM exists.
    for name in ["mix.exs", "mix.lock"]:
        (scratch / name).unlink()
    scratch.rmdir()

    elixir = Path("/opt/homebrew/Cellar/elixir/1.20.4")
    otp = Path("/opt/homebrew/Cellar/erlang/29.1.1_2")
    hex_archive = Path("/Users/andreyyurlov/.mix/archives/hex-2.5.1")
    files = [elixir / "bin/mix", elixir / "bin/elixir",
             elixir / "lib/elixir/lib/mix/ebin/mix.app",
             elixir / "lib/elixir/lib/elixir/ebin/elixir.app",
             otp / "bin/erl", otp / "lib/erlang/releases/29/OTP_VERSION",
             otp / "lib/erlang/releases/start_erl.data",
             otp / "lib/erlang/erts-17.1/bin/beam.smp",
             otp / "lib/erlang/erts-17.1/bin/erlexec"]
    files.extend(elixir / "lib/elixir/lib/mix/ebin" / name for name in [
        "Elixir.Mix.Tasks.Deps.Get.beam", "Elixir.Mix.Tasks.Deps.Unlock.beam",
        "Elixir.Mix.Dep.Fetcher.beam", "Elixir.Mix.Dep.Lock.beam"])
    tools = [record(path) for path in files]
    archive_files = {str(path.relative_to(hex_archive)): record(path)
                     for path in sorted(hex_archive.rglob("*")) if path.is_file()}
    archive_digest = hashlib.sha256(json.dumps(archive_files, sort_keys=True,
                                               separators=(",", ":")).encode()).hexdigest()
    assert '{vsn,"1.20.4"}' in (elixir / "lib/elixir/lib/mix/ebin/mix.app").read_text()
    assert '{vsn,"2.5.1"}' in (hex_archive / "hex-2.5.1/ebin/hex.app").read_text()
    assert (otp / "lib/erlang/releases/29/OTP_VERSION").read_text().strip() == "29.1.1"
    for name, item in inputs.items():
        assert digest(ROOT / name) == item["sha256"], name
    assert prior_seal() == frozen
    receipt = {
        "schema": "mixer.hosted-dependency-advisory-correction.preparation.v1",
        "prepared_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "command": ["python3", "-B", "verification/hosted-dependency-advisory-correction/prepare.py"],
        "python": sys.version,
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
        "selected_inputs": inputs, "tool_files": tools,
        "installed_hex_archive": {"root": str(hex_archive), "version_from_app_manifest": "2.5.1",
                                  "aggregate_sha256": archive_digest, "files": archive_files},
        "tools_not_executed": "All Elixir/OTP/Mix/Hex identities are filesystem observations, not runtime version receipts.",
        "source_only_scratch": {"recorded_inputs": scratch_inputs, "removed": not scratch.exists(),
                                "runtime_started": False, "process_group_created": False},
        "prior_advisory_packet": frozen, "prior_packet_unchanged": True,
        "canonical_inputs_unchanged": True,
        "lock_generation": "pending root release; no proposed lock/checksums invented",
        "dependencies_json": "pending real Mix resolution; proposed THIRD_PARTY receipt links are not yet acceptance evidence",
        "validation_scope": "Exact two-pin source replacements, inventory link proposal, static tool identities, original lock custody and prior sealed packet integrity. No runtime/compilation/install/resolution/tests.",
    }
    (HERE / "preparation-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": "source_preparation_pass", "canonical_inputs_unchanged": True,
                      "prior_packet_unchanged": True, "source_only_scratch_removed": True,
                      "local_hex_manifest_version": "2.5.1", "runtime_executed": False,
                      "proposed_lock": None}, indent=2))


if __name__ == "__main__":
    main()
