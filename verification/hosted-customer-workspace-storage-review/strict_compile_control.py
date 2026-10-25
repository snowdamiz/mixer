#!/usr/bin/env python3
"""Expected-negative zero-diagnostic compile of the sealed original source."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
OWN = ROOT / "verification/hosted-customer-workspace-storage-review"
OUTPUT = OWN / "negative-warning-control"
ARCHIVE = OWN / "run-2"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUTPUT.mkdir(exist_ok=False)
    archived = json.loads((ARCHIVE / "receipt.json").read_text())
    nodes = ast.parse((OWN / "run.py").read_text()).body
    selected = {}
    for node in nodes:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"SOURCES", "EXTRA_SOURCES", "DEPS"}:
            selected[node.targets[0].id] = ast.literal_eval(node.value)
    sources = selected["SOURCES"] + selected["EXTRA_SOURCES"]
    for name in sources:
        if digest(ARCHIVE / "inputs" / name) != archived["input_sha256"][name]:
            raise RuntimeError("sealed source mismatch: " + name)
    dependencies = json.loads((ARCHIVE / "dependency-beams.json").read_text())
    for name, expected in dependencies.items():
        if digest(ROOT / name) != expected:
            raise RuntimeError("pinned dependency mismatch: " + name)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-workspace-warning-negative-"))
    env = dict(os.environ, ERL_FLAGS="+S 2:2")
    receipt = {"source_revision": archived["source_revision"], "sealed_source_tree_sha256": archived["source_tree_sha256"], "archive_receipt_sha256": digest(ARCHIVE / "receipt.json"), "dependency_manifest_sha256": archived["dependency_manifest_sha256"], "scope": "Expected-negative compile only of original archived workspace storage; no PostgreSQL or native startup", "started_unix": time.time(), "commands": [], "input_sha256": {name: archived["input_sha256"][name] for name in sources}, "collector_sha256": digest(Path(__file__))}
    script = OUTPUT / "compile.exs"
    script.write_text("""result = Kernel.ParallelCompiler.compile_to_path(System.argv(), System.fetch_env!("MIXER_WARNING_CONTROL_BEAMS"), return_diagnostics: true)
accepted = match?({:ok, _, %{compile_warnings: [], runtime_warnings: []}}, result)
IO.inspect(result, label: "structured_compiler_result", limit: :infinity, printable_limit: :infinity)
File.write!(System.fetch_env!("MIXER_WARNING_CONTROL_RESULT"), Jason.encode!(%{accepted: accepted, structured_result: inspect(result, limit: :infinity, printable_limit: :infinity)}))
System.halt(if accepted, do: 0, else: 1)
""")
    env["MIXER_WARNING_CONTROL_BEAMS"] = str(scratch)
    env["MIXER_WARNING_CONTROL_RESULT"] = str(OUTPUT / "compile-result.json")
    codepaths = [arg for dep in selected["DEPS"] for arg in ["-pa", str(ROOT / "hosted/_build/test/lib" / dep / "ebin")]]
    argv = ["elixir", *codepaths, str(script), *[str(ARCHIVE / "inputs" / name) for name in sources]]
    try:
        result = subprocess.run(argv, cwd=ARCHIVE / "inputs", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
        (OUTPUT / "compile.log").write_text(result.stdout)
        receipt["commands"].append({"argv": argv, "exit_code": result.returncode, "output": "compile.log"})
        structured = json.loads((OUTPUT / "compile-result.json").read_text())
        receipt["compile_result"] = structured
        receipt["expected_negative_observed"] = result.returncode == 1 and structured["accepted"] is False
        receipt["success"] = receipt["expected_negative_observed"]
    finally:
        shutil.rmtree(scratch)
        receipt["cleanup"] = {"scratch_removed": not scratch.exists(), "postgres_started": False}
        receipt["finished_unix"] = time.time()
        receipt["output_sha256"] = {name: digest(OUTPUT / name) for name in ["compile.exs", "compile.log", "compile-result.json"] if (OUTPUT / name).exists()}
        (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"success": receipt["success"], "expected_negative_observed": receipt["expected_negative_observed"], "cleanup": receipt["cleanup"]}, sort_keys=True))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
