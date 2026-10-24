#!/usr/bin/env python3
"""Run an independent frozen-source verifier review without shared build writes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", default="run-1")
    options = parser.parse_args()
    output = HERE / options.run_name
    output.mkdir(exist_ok=False)
    frozen = json.loads((ROOT / "verification/hosted-token-verifier/source-manifest.json").read_text())
    for entry in frozen["files"]:
        assert sha(ROOT / entry["path"]) == entry["sha256"], entry["path"]
    product_files = [entry for entry in frozen["files"] if entry["path"].startswith("hosted/lib/")]
    product_digest = hashlib.sha256("".join(
        f'{entry["sha256"]}  {entry["path"]}\n' for entry in product_files
    ).encode()).hexdigest()
    write_json(output / "source-manifest.json", {
        "producer_manifest": frozen,
        "product_files": product_files,
        "product_aggregate_sha256": product_digest,
        "aggregate_encoding": "sha256 over sorted file-sha256 + two spaces + relative path + LF",
    })
    inputs = ["AGENTS.md", "docs/hosted-identity-contract.md", "docs/hosted-verifier-dependency.md",
              "verification/hosted-verifier-dependency/root-selection.json", "hosted/mix.exs",
              "hosted/mix.lock", "hosted/config/config.exs",
              str((HERE / "independent_test.exs").relative_to(ROOT)),
              str((HERE / "run.py").relative_to(ROOT))]
    write_json(output / "input-manifest.json", {p: sha(ROOT / p) for p in inputs})
    with tarfile.open(output / "product-source.tar.gz", "w:gz") as archive:
        for entry in product_files:
            archive.add(ROOT / entry["path"], arcname=entry["path"])
    commands = []
    scratch = Path(tempfile.mkdtemp(prefix="mixer-independent-token-review-", dir="/private/tmp"))
    receipt = {"schema": 1, "reviewer": "/root/hosted_token_verifier_review",
               "model": "gpt-6.1-sol", "reasoning_effort": "xhigh", "started_at": now(),
               "host": {"system": platform.system(), "machine": platform.machine(),
                        "platform": platform.platform()}, "scratch": str(scratch),
               "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "product_aggregate_sha256": product_digest,
               "producer_aggregate_sha256": frozen["aggregate_sha256"],
               "test_suite": "independently authored; producer tests excluded", "commands": commands,
               "limitations": ["Pure helper and trust constructor only; no configured authenticate/2 adapter",
                   "No HTTP, transport/cache, provider issuance, active trust replacement, revocation or membership policy",
                   "macOS host synthetic crypto only; no Linux deployment, native runtime or physical device",
                   "No production or GA acceptance; root owns final acceptance"],
               "private_keys": "Generated only in memory by the ExUnit process; no files or printed key values",
               "result": "incomplete"}
    env = dict(os.environ, MIX_ENV="test", MIX_BUILD_PATH=str(scratch / "_build"))

    def command(argv, name, cwd=scratch):
        started = now()
        monotonic = time.monotonic()
        with (output / name).open("w") as stream:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
        entry = {"argv": argv, "cwd": str(cwd), "env": {"MIX_ENV": env["MIX_ENV"], "MIX_BUILD_PATH": env["MIX_BUILD_PATH"]},
                 "started_at": started, "elapsed_seconds": round(time.monotonic() - monotonic, 3),
                 "exit_code": result.returncode, "log": name, "sha256": sha(output / name)}
        commands.append(entry)
        print(json.dumps(entry), flush=True)
        return result.returncode

    try:
        (scratch / "lib").mkdir()
        (scratch / "test").mkdir()
        (scratch / "config").mkdir()
        for entry in product_files:
            shutil.copy2(ROOT / entry["path"], scratch / "lib" / Path(entry["path"]).name)
        shutil.copy2(HERE / "independent_test.exs", scratch / "test" / "independent_test.exs")
        (scratch / "test/test_helper.exs").write_text("ExUnit.start()\n")
        (scratch / "mix.exs").write_text('''defmodule IndependentReview.MixProject do
  use Mix.Project
  def project, do: [app: :independent_verifier_review, version: "0.0.0", elixir: "== 1.20.4",
    deps: [{:jason, path: "deps/jason", env: :prod}, {:jose, path: "deps/jose", env: :prod}]]
  def application, do: [extra_applications: [:crypto, :public_key, :jason, :jose]]
end
''')
        (scratch / "config/config.exs").write_text('''import Config
config :jose, json_module: :jose_json_jason, unsecured_signing: false, crypto_fallback: false
''')
        (output / "harness.mix.exs").write_bytes((scratch / "mix.exs").read_bytes())
        (output / "harness.config.exs").write_bytes((scratch / "config/config.exs").read_bytes())
        dep_manifest = {}
        for dependency in ["jason", "jose"]:
            source = ROOT / "hosted/deps" / dependency
            dep_manifest[dependency] = {str(p.relative_to(source)): sha(p)
                for p in sorted(source.rglob("*")) if p.is_file()}
            shutil.copytree(source, scratch / "deps" / dependency)
        write_json(output / "dependency-source-manifest.json", dep_manifest)
        command(["elixir", "--version"], "elixir-version.log")
        command(["mix", "--version"], "mix-version.log")
        code = command(["mix", "deps.compile"], "deps-compile.log")
        if code == 0:
            code = command(["mix", "test", "--no-start", "--trace", "--seed", "0"], "tests.log")
        for entry in frozen["files"]:
            assert sha(ROOT / entry["path"]) == entry["sha256"], f'Changed during review: {entry["path"]}'
        receipt["source_unchanged_after_test"] = True
        receipt["result"] = "pass" if code == 0 else "fail"
    finally:
        # subprocess.run has waited for each owned BEAM process; no listeners or
        # native runtimes are started. Remove only this uniquely owned scratch.
        shutil.rmtree(scratch)
        receipt["cleanup"] = {"scratch_removed": not scratch.exists(),
                              "owned_processes": "all subprocess.run children exited; no daemon/listener/native runtime started"}
        receipt["completed_at"] = now()
        receipt["artifacts"] = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
        write_json(output / "receipt.json", receipt)
    raise SystemExit(0 if receipt["result"] == "pass" else 1)


if __name__ == "__main__":
    main()
