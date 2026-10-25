#!/usr/bin/env python3
"""Independent standalone collector with immutable run directories and no Mix app."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path("verification/hosted-customer-artifact-event-review")
PRODUCER = Path("verification/hosted-customer-artifact-event/run-3")
SOURCE = "hosted/lib/mixer_hosted/audit/customer_artifact_event.ex"
TEST = "hosted/test/mixer_hosted/audit/customer_artifact_event_test.exs"
DOC = "docs/hosted-customer-artifact-event.md"
EXPECTED = {
    SOURCE: "0b3ac571d7e008acf12f12fb148ba55cb80b712634180346a6547930b1768913",
    TEST: "6cbe0d238c1b54747c0bda05fbfd42f639c30233e944c3c3ef1ad422ebcf8de4",
    DOC: "0318a66c362fa1b010c80cbba8412310d6cc889c418b3289dac3a29af1214d31",
}
SOURCES = [
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/snapshot.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_cbor.ex",
    "hosted/lib/mixer_hosted/audit/upload_event.ex", SOURCE,
]
REGRESSIONS = [TEST, "hosted/test/mixer_hosted/protocol/artifact_cbor_test.exs",
               "hosted/test/mixer_hosted/audit/upload_event_test.exs"]
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--producer-run", default=str(PRODUCER))
    parser.add_argument("--source-sha256", default=EXPECTED[SOURCE])
    parser.add_argument("--test-sha256", default=EXPECTED[TEST])
    parser.add_argument("--doc-sha256", default=EXPECTED[DOC])
    args = parser.parse_args()
    producer = (ROOT / args.producer_run).resolve()
    producer.relative_to(ROOT / "verification/hosted-customer-artifact-event")
    expected_identities = {SOURCE: args.source_sha256, TEST: args.test_sha256, DOC: args.doc_sha256}
    output = (ROOT / args.output).resolve()
    output.relative_to(ROOT / PACKET)
    output.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-customer-event-independent-review-"))
    receipt = {"started_unix": time.time(), "platform": platform.platform(), "commands": [],
        "scope": "independent pure bounded v2 customer artifact event codec; v1/CBOR regressions; no authority, transaction, PostgreSQL, network/provider, native, customer, dogfood or GA qualification",
        "provenance": "producer run-3 base revision plus exact frozen selected source; no Git executed",
        "scratch": str(scratch), "collector": "standalone BEAM process registered as :mixer_customer_artifact_event_review_collector; no distribution or application start"}
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")

    def run(name, command):
        try:
            result = subprocess.run(list(map(str, command)), cwd=ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90, text=True)
            text, status = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error:
            text = (error.stdout or b"").decode(errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
            text += "\nCOLLECTOR TIMEOUT\n"
            status = 124
        output.joinpath(name + ".log").write_text(text)
        receipt["commands"].append({"name": name, "argv": list(map(str, command)),
            "cwd": str(ROOT), "exit_code": status, "output": name + ".log"})
        if status:
            raise RuntimeError(name + " failed; retained output " + name + ".log")

    try:
        producer_receipt = json.loads((producer / "receipt.json").read_text())
        if producer_receipt.get("result") != "passed":
            raise RuntimeError("producer packet is not a passed receipt")
        receipt["source_revision"] = producer_receipt["source_revision"]
        receipt["producer_packet"] = str(producer.relative_to(ROOT))
        receipt["producer_receipt_sha256"] = sha(producer / "receipt.json")
        frozen = output / "inputs"
        frozen.mkdir()
        names = set(SOURCES + REGRESSIONS + [DOC, "AGENTS.md", "PLAN.md", "hosted/mix.lock",
            "docs/hosted-customer-artifact-transaction-contract.md",
            "hosted/test/fixtures/audit/coherent-vectors.json", "hosted/test/fixtures/audit/retained-chains.json",
            "services/protocol/testdata/signed-release-v3.json",
            "verification/hosted-customer-artifact-event/golden_event.hex",
            "verification/hosted-customer-artifact-event/golden_hashes.txt"])
        manifests = {}
        for name in sorted(names):
            original = producer / "inputs" / name
            expected = producer_receipt["input_sha256"][name]
            if sha(original) != expected:
                raise RuntimeError("producer snapshot mutated: " + name)
            if name in expected_identities and (expected != expected_identities[name] or sha(ROOT / name) != expected):
                raise RuntimeError("coordinated source identity mismatch: " + name)
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
            manifests[name] = sha(target)
        # Preserve and compare live v1/CBOR regression sources; their API and bytes
        # are protected by both exact source identity and frozen executable tests.
        unchanged = ["hosted/lib/mixer_hosted/audit/upload_event.ex",
                     "hosted/test/mixer_hosted/audit/upload_event_test.exs",
                     "hosted/lib/mixer_hosted/protocol/artifact_cbor.ex",
                     "hosted/test/mixer_hosted/protocol/artifact_cbor_test.exs"]
        receipt["v1_cbor_live_matches_producer"] = {name: sha(ROOT / name) == manifests[name] for name in unchanged}
        if not all(receipt["v1_cbor_live_matches_producer"].values()):
            raise RuntimeError("live v1 or CBOR changed since producer")
        for name in ["run.py", "oracle.py", "adversarial_test.exs"]:
            target = frozen / PACKET / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / PACKET / name, target)
            manifests[str(PACKET / name)] = sha(target)
        receipt["input_sha256"] = manifests
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifests, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        dependencies = json.loads((producer / "dependency-beams.json").read_text())
        actual = {}
        codepaths = []
        for dep in DEPS:
            path = ROOT / "hosted/_build/test/lib" / dep / "ebin"
            target = scratch / "dependencies" / dep / "ebin"
            shutil.copytree(path, target)
            codepaths.extend(["-pa", str(target)])
            for file in sorted(target.iterdir()):
                if file.is_file():
                    actual[str(Path("hosted/_build/test/lib") / dep / "ebin" / file.name)] = sha(file)
        output.joinpath("dependency-beams.json").write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n")
        receipt["dependency_manifest_sha256"] = sha(output / "dependency-beams.json")
        if actual != dependencies:
            raise RuntimeError("general-purpose dependency BEAM identity differs from producer")
        run("elixir-version", ["elixir", "--version"])
        run("python-version", ["python3", "--version"])
        run("review-test-format", ["elixir", "-e",
            'p = hd(System.argv()); if File.read!(p) != IO.iodata_to_binary(Code.format_string!(File.read!(p))) <> "\\n", do: raise("review format mismatch")',
            frozen / PACKET / "adversarial_test.exs"])
        run("independent-oracle", ["python3", frozen / PACKET / "oracle.py", output / "oracle.json"])
        env["MIXER_REVIEW_ORACLE"] = str(output / "oracle.json")
        beams = scratch / "beams"
        beams.mkdir()
        run("compile", ["elixirc", "--warnings-as-errors", *codepaths, "-o", beams, *[frozen / name for name in SOURCES]])
        runner = output / "standalone_collector.exs"
        tests = [frozen / name for name in REGRESSIONS] + [frozen / PACKET / "adversarial_test.exs"]
        runner.write_text('Process.register(self(), :mixer_customer_artifact_event_review_collector)\n'
            'IO.puts("collector=mixer_customer_artifact_event_review_collector distribution=#{Node.alive?()}")\n'
            'ExUnit.start(autorun: false, seed: 0, max_cases: 2)\n'
            '{:ok, _, _} = Kernel.ParallelCompiler.compile([' + ','.join(json.dumps(str(path)) for path in tests) + '], warnings_as_errors: true, return_diagnostics: true)\n'
            'result = ExUnit.run()\nSystem.halt(if result.failures == 0, do: 0, else: 1)\n')
        run("tests", ["elixir", *codepaths, "-pa", beams, runner])
        receipt["result"] = "passed"
    except Exception as error:
        receipt["result"] = "failed"
        receipt["failure"] = str(error)
    finally:
        shutil.rmtree(scratch)
        receipt["cleanup"] = {"owned_scratch_removed": not scratch.exists(),
            "postgres_started": False, "native_instances_started": False,
            "network_provider_operations": False, "other_project_processes_changed": False}
        receipt["finished_unix"] = time.time()
        output.joinpath("receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": receipt["result"], "receipt": str(output / "receipt.json")}))
    raise SystemExit(0 if receipt["result"] == "passed" else 1)


if __name__ == "__main__":
    main()
