#!/usr/bin/env python3
"""Read-only controller/input/primary-OTP source audit; no producer import."""
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PACKET = REPO / "verification/hosted-dependency-advisory-correction"
RESOLUTION = PACKET / "resolution-v2"
OTP = Path("/opt/homebrew/Cellar/erlang/29.1.1_2/lib/erlang/lib/kernel-11.0.4/src")


def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            assert time.monotonic() - START < 55
            data = stream.read(262144)
            if not data:
                return result.hexdigest()
            result.update(data)


def pairs(values):
    result = {}
    for key, value in values:
        assert key not in result
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def seal(path):
    values = []
    for line in path.read_text().splitlines():
        expected, relative = line.split("  ", 1)
        assert len(expected) == 64 and not Path(relative).is_absolute() and ".." not in Path(relative).parts
        assert sha(path.parent / relative) == expected
        values.append(relative)
    assert len(values) == len(set(values))
    return values


def main():
    assert sha(RESOLUTION / "controller.py") == "f4369b8fa608521da8e95a301c85966aae34fa5303f122a2edc1eccae83cc556"
    assert sha(RESOLUTION / "resolution-plan-v2.json") == "c0cd50892185a8e0614486c1e3f478c997ba7a8c7405935dcdf361d72e71df1c"
    successor_members = seal(RESOLUTION / "seal.sha256")
    assert len(successor_members) == 5
    original_members = seal(PACKET / "preparation-seal.sha256")
    assert len(original_members) == 16
    plan = read(RESOLUTION / "resolution-plan-v2.json")
    preparation = read(PACKET / "preparation-receipt.json")
    for relative, expected in plan["packet_inputs"].items():
        assert sha(PACKET / relative) == expected
    assert len(plan["packet_inputs"]) == 17
    for relative, pin in preparation["selected_inputs"].items():
        assert sha(REPO / relative) == pin["sha256"]
    for pin in preparation["tool_files"]:
        assert sha(Path(pin["path"])) == pin["sha256"]
    archive = preparation["installed_hex_archive"]
    for relative, pin in archive["files"].items():
        assert sha(Path(archive["root"]) / relative) == pin["sha256"]
    prior = REPO / "verification/hosted-dependency-advisory-review"
    assert sha(prior / "seal.sha256") == preparation["prior_advisory_packet"]["seal_sha256"]
    for pin in preparation["prior_advisory_packet"]["entries"]:
        assert sha(prior / pin["path"]) == pin["sha256"]
    expected_commands = [
        [plan["tools"]["elixir"], "--version"],
        [plan["tools"]["mix"], "--version"],
        [plan["tools"]["mix"], "deps.unlock", "bandit", "jose"],
        [plan["tools"]["mix"], "deps.get", "--only", "prod"],
        [plan["tools"]["mix"], "deps.get", "--only", "prod", "--check-locked"]]
    assert [value["argv"] for value in plan["commands"]] == expected_commands
    assert plan["commands"][-1]["environment_override"] == {"HEX_OFFLINE": "1"}
    assert all(plan["environment"][value] == "0" for value in ("HEX_UNSAFE_HTTPS", "HEX_UNSAFE_REGISTRY", "HEX_NO_VERIFY_REPO_ORIGIN"))
    assert plan["absolute_phase_cutoffs_seconds"] == {"work": 40, "cleanup": 46, "posthash_and_scratch_deletion": 52, "receipt": 55}
    source = (RESOLUTION / "controller.py").read_text()
    ast.parse(source, filename="controller.py")
    assert "os.WEXITED | os.WNOHANG | os.WNOWAIT" in source
    lock = (PACKET / "inputs/mix.lock").read_text()
    versions = dict(re.findall(r'^  "([a-z0-9_]+)": \{:hex, :[a-z0-9_]+, "([0-9.]+)"', lock, re.M))
    assert len(versions) == 21 and versions["bandit"] == "1.13.1" and versions["jose"] == "1.11.12"
    before = (PACKET / "inputs/mix.exs").read_text()
    assert (PACKET / "proposal/mix.exs").read_text() == before.replace('{:bandit, "== 1.13.1"}', '{:bandit, "== 1.14.0"}').replace('{:jose, "== 1.11.12"}', '{:jose, "== 1.11.13"}')
    primary = []
    ranges = {"inet_config.erl": [[35,84],[184,197],[432,456]], "inet.erl": [[2588,2604],[3757,3815]], "inet_gethost_native.erl": [[412,429]], "inet_res.erl": [[28,40],[1092,1124]]}
    for name, regions in ranges.items():
        path = OTP / name
        lines = path.read_text().splitlines()
        primary.append({"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size, "ranges": regions, "excerpts": [{"first": first, "last": last, "text": "\n".join(lines[first-1:last])} for first,last in regions]})
    assert "inet_db:set_lookup([native])" in (OTP / "inet_config.erl").read_text()
    assert 'os:getenv("ERL_INETRC")' in (OTP / "inet_config.erl").read_text()
    assert "open_port({spawn_executable, Prog}, Opts)" in (OTP / "inet_gethost_native.erl").read_text()
    result = {"schema":1,"status":"source-custody-passed-cancel-and-resolver-corrections-required-before-release","created_at":datetime.now(timezone.utc).isoformat(),"command":"python3 -B verification/hosted-dependency-advisory-correction-independent/review-1/audit_sources.py","python":sys.version,"review_script_sha256":sha(Path(__file__)),"controller_sha256":sha(RESOLUTION/'controller.py'),"plan_sha256":sha(RESOLUTION/'resolution-plan-v2.json'),"source_revision":preparation['source_revision'],"verified":{"successor_seal_members":5,"original_seal_members":16,"original_packet_inputs":17,"canonical_source_pins":len(preparation['selected_inputs']),"selected_tool_files":len(preparation['tool_files']),"copied_Hex_archive_source_files":len(archive['files']),"prior_advisory_entries":len(preparation['prior_advisory_packet']['entries']),"exact_sequential_commands":5,"original_lock_entries":21,"proposal_only_two_exact_mix_pins":True,"controller_AST_parse_only":True},"primary_local_OTP_sources":primary,"findings":[{"id":"R01","priority":"P2","issue":"late cancellation can coexist with successful resolved status"},{"id":"R02","priority":"P2","issue":"default native name resolution may launch unaccounted inet_gethost port helper; pin private built-in DNS/file inetrc"}],"HOME_scope":"Unchanged shell HOME is root-selected; private Mix/Hex/cache/project paths are verified. Use explicit scratch BEAM -home if needed instead of changing shell HOME.","recommend_runtime_release":False,"controller_imported_or_executed":False,"Mix_compiler_product_DNS_process_probe_native_or_provider_invocations":0,"elapsed_seconds":round(time.monotonic()-START,6),"scope":"Source-only resolution controller and primary OTP review; no generated lock, dependency upgrade or behavior pass."}
    (OUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k != "primary_local_OTP_sources"}, indent=2))


if __name__ == "__main__":
    main()
