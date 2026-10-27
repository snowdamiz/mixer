"""Record one pure host model/test attempt. Never imports producer scripts."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def main():
    if len(sys.argv) != 2 or not sys.argv[1] or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in sys.argv[1]):
        raise SystemExit("one lowercase unique attempt label required")
    if (HERE / "seal.json").exists():
        raise SystemExit("frozen packet: use check.py --read-only")
    attempt = HERE / "commands" / sys.argv[1]
    attempt.mkdir(parents=True, exist_ok=False)
    # Retain all exact executed model/test/runner preimages before launch.
    source_files = ("model.py", "test_model.py", "run_host.py")
    for name in source_files:
        (attempt / name).write_bytes((HERE / name).read_bytes())
    sources = [row(HERE / name) for name in source_files]
    inputs = []
    for stem in ("swift-guarded-snapshot-owned-binding-provider",
                 "swift-guarded-snapshot-scoped-binding-source",
                 "swift-guarded-snapshot-scoped-binding-independent"):
        packet = ROOT / "verification" / stem
        inputs.append(row(packet / "seal.json"))
        seal = json.loads((packet / "seal.json").read_bytes())
        inputs.extend(row(packet / member["path"]) for member in seal["members"])
    provider = ROOT / "verification/swift-guarded-snapshot-owned-binding-provider"
    for member in json.loads((provider / "proposed-source-custody.json").read_bytes()):
        inputs.append(row(ROOT / member["origin"]))
    host_path = ROOT / "verification/swift-guarded-snapshot-host-composition/host-support-manifest.json"
    inputs.append(row(host_path))
    for member in json.loads(host_path.read_bytes())["members"]:
        inputs.append(row(ROOT / "verification/swift-real-profile-loader-binding/host" / member["path"]))
    inputs.append(row(ROOT / "verification/swift-real-profile-loader-binding/source-preimages/genuine.wasm"))
    # Deduplicate actual paths only, without conflating content-identical files.
    inputs = sorted({value["path"]: value for value in inputs}.values(), key=lambda x: x["path"])
    write(attempt / "input-custody.json", inputs)
    executable = Path(sys.executable).resolve()
    argv = [str(executable), "-B", "-m", "unittest", "discover", "-s", str(HERE), "-p", "test_model.py", "-v"]
    environment = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "LC_ALL": "C"}
    plan = {"schema": 1, "argv": argv, "cwd": str(HERE), "environment": environment,
            "tool": {"path": str(executable), "bytes": executable.stat().st_size,
                     "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                     "version": sys.version}, "sources": sources,
            "input_members": len(inputs), "input_bytes": sum(x["bytes"] for x in inputs),
            "source_revision": "frozen input146 custody; no live Git query",
            "proposed_source146_tree": "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d",
            "scope": "pure host source/custody/state-model tests; no compiler/product/native/capture/OS handle effects",
            "timeout_seconds": 30, "production_root_or_funding_selected": False}
    write(attempt / "plan.json", plan)
    started = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=HERE, env=environment, capture_output=True,
                                timeout=30, check=False)
        stdout, stderr, code, timeout = result.stdout, result.stderr, result.returncode, False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code, timeout = error.stdout or b"", error.stderr or b"", None, True
    (attempt / "stdout").write_bytes(stdout)
    (attempt / "stderr").write_bytes(stderr)
    receipt = {"schema": 1, "argv": argv, "exit_code": code, "timed_out": timeout,
               "elapsed_seconds": time.monotonic() - started, "terminal": True,
               "stdout": row(attempt / "stdout"), "stderr": row(attempt / "stderr"),
               "source_preimages": sources,
               "compiler_invocations": 0, "product_or_loader_executable_launches": 0,
               "native_simulator_emulator_phone_UI_capture": False,
               "synthetic_model_grants_are_product_authority": False,
               "cleanup": "only Python host child reaped by subprocess.run; no native resources/scratch created; no global inventory",
               "scope": plan["scope"]}
    write(attempt / "receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True, indent=2))
    raise SystemExit(0 if code == 0 and not timeout else 1)


if __name__ == "__main__":
    main()
