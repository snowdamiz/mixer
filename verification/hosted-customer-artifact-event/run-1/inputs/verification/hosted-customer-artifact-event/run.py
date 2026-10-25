#!/usr/bin/env python3
"""Frozen named ordinary sources, pinned dependency BEAMs, no Mix application."""
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
PACKET = "verification/hosted-customer-artifact-event"
SOURCE = "hosted/lib/mixer_hosted/audit/customer_artifact_event.ex"
TEST = "hosted/test/mixer_hosted/audit/customer_artifact_event_test.exs"
SOURCES = [
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/snapshot.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_cbor.ex",
    "hosted/lib/mixer_hosted/audit/upload_event.ex",
    SOURCE,
]
TESTS = [TEST, "hosted/test/mixer_hosted/protocol/artifact_cbor_test.exs",
         "hosted/test/mixer_hosted/audit/upload_event_test.exs"]
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.relative_to(ROOT / PACKET)
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
    receipt = {"source_revision": args.source_revision,
               "revision_provenance": "root-supplied base HEAD; exact selected tree frozen below; no Git executed",
               "platform": platform.platform(), "scope": "pure host codec and retained v1/ArtifactCBOR regression only; no PostgreSQL/provider/native/customer/GA acceptance",
               "commands": [], "started_unix": time.time(), "cleanup": {}}
    scratch = Path(tempfile.mkdtemp(prefix="mixer-customer-audit-codec-"))
    receipt["scratch"] = str(scratch)

    def run(name, command, *, cwd=ROOT):
        result = subprocess.run([str(x) for x in command], cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=90, text=True)
        output.joinpath(name + ".log").write_text(result.stdout)
        receipt["commands"].append({"name": name, "argv": list(map(str, command)),
                                    "cwd": str(cwd), "exit_code": result.returncode, "output": name + ".log"})
        if result.returncode:
            raise RuntimeError(f"{name} failed ({result.returncode}); see preserved log")

    try:
        inputs = SOURCES + TESTS + ["hosted/mix.lock", "docs/hosted-customer-artifact-event.md",
            "docs/hosted-customer-artifact-transaction-contract.md", "AGENTS.md", "PLAN.md",
            PACKET + "/run.py", PACKET + "/oracle.py", PACKET + "/golden_event.hex", PACKET + "/golden_hashes.txt",
            "hosted/test/fixtures/audit/retained-chains.json", "hosted/test/fixtures/audit/coherent-vectors.json"]
        manifest = {}
        frozen = output / "inputs"
        for name in sorted(inputs):
            source = ROOT / name
            target = frozen / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest[name] = digest(source)
        receipt["input_sha256"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        paths = [ROOT / "hosted/_build/test/lib" / dep / "ebin" for dep in DEPS]
        dependencies = {}
        for path in paths:
            if not path.is_dir():
                raise RuntimeError("missing pinned dependency BEAM directory")
            for file in sorted(path.iterdir()):
                if file.is_file():
                    dependencies[str(file.relative_to(ROOT))] = digest(file)
        output.joinpath("dependency-beams.json").write_text(json.dumps(dependencies, sort_keys=True, indent=2) + "\n")
        receipt["dependency_manifest_sha256"] = digest(output / "dependency-beams.json")
        run("elixir-version", ["elixir", "--version"])
        run("python-version", ["python3", "--version"])
        run("oracle", ["python3", frozen / PACKET / "oracle.py"])
        for name in ["golden_event.hex", "golden_hashes.txt"]:
            if digest(frozen / PACKET / name) != manifest[PACKET + "/" + name]:
                raise RuntimeError("independent oracle does not reproduce retained golden")
        codepaths = [arg for path in paths for arg in ["-pa", str(path)]]
        format_code = 'Enum.each(System.argv(), fn f -> if File.read!(f) != IO.iodata_to_binary(Code.format_string!(File.read!(f))) <> "\\n", do: raise("format mismatch: " <> f) end)'
        run("format", ["elixir", "-e", format_code, str(frozen / SOURCE), str(frozen / TEST)])
        beams = scratch / "beams"
        beams.mkdir()
        run("compile", ["elixirc", "--warnings-as-errors", *codepaths, "-o", beams, *[frozen / source for source in SOURCES]])
        runner = scratch / "run.exs"
        runner.write_text('ExUnit.start(autorun: false, seed: 0, max_cases: 2)\n' +
            '{:ok, _, _} = Kernel.ParallelCompiler.compile(' +
            '[' + ','.join(json.dumps(str(frozen / test)) for test in TESTS) + '], warnings_as_errors: true)\n' +
            'result = ExUnit.run()\nSystem.halt(if result.failures == 0, do: 0, else: 1)\n')
        run("tests", ["elixir", *codepaths, "-pa", beams, runner])
        receipt["result"] = "passed"
    except Exception as error:
        receipt["result"] = "failed"
        receipt["failure"] = str(error)
    finally:
        shutil.rmtree(scratch)
        receipt["cleanup"] = {"scratch_removed": not scratch.exists(), "postgres_started": False,
                              "native_instances_started": False}
        receipt["finished_unix"] = time.time()
        output.joinpath("receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"result": receipt["result"], "receipt": str(output / "receipt.json")}, sort_keys=True))
    raise SystemExit(0 if receipt["result"] == "passed" else 1)


if __name__ == "__main__":
    main()
