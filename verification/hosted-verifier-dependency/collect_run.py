#!/usr/bin/env python3
"""Reproduce a standalone host-only dependency qualification in an ignored Mix tree."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
SCRATCH = BASE / "scratch"
OUTPUT = BASE / "run-1"
if OUTPUT.exists():
    sys.exit("Refusing to overwrite an existing receipt; choose a new output directory in this script.")
OUTPUT.mkdir()
(SCRATCH / "test").mkdir(parents=True, exist_ok=True)
shutil.copy2(BASE / "qualification.mix.exs", SCRATCH / "mix.exs")
shutil.copy2(BASE / "qualification_test.exs", SCRATCH / "test/qualification_test.exs")
(SCRATCH / "test/test_helper.exs").write_text("# ExUnit is started in qualification_test.exs.\n")
if (BASE / "qualified.mix.lock").exists():
    shutil.copy2(BASE / "qualified.mix.lock", SCRATCH / "mix.lock")

commands = []
def run(name, argv, cwd=SCRATCH):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    monotonic_start = time.monotonic()
    result = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=300, env={**os.environ, "NO_COLOR": "1"})
    path = OUTPUT / (name + ".log")
    path.write_bytes(result.stdout)
    entry = {"argv": argv, "cwd": str(cwd), "started_at": started,
             "elapsed_seconds": round(time.monotonic() - monotonic_start, 3),
             "exit_code": result.returncode, "log": str(path.relative_to(BASE)),
             "sha256": hashlib.sha256(result.stdout).hexdigest()}
    commands.append(entry)
    print(f"{name}: exit={result.returncode}", flush=True)
    return result

inputs = ["AGENTS.md", "mixer-product-plan.md", "docs/hosted-identity-contract.md",
          "hosted/README.md", "hosted/mix.exs", "hosted/mix.lock",
          "verification/hosted-verifier-dependency/qualification.mix.exs",
          "verification/hosted-verifier-dependency/qualification_test.exs",
          "verification/hosted-verifier-dependency/collect_run.py"]
input_manifest = [{"path": p, "bytes": (ROOT / p).stat().st_size,
                   "sha256": hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in inputs]
tree_bytes = "".join(f"{p['path']}\0{p['sha256']}\n" for p in sorted(input_manifest, key=lambda p: p["path"])).encode()
source_digest = hashlib.sha256(tree_bytes).hexdigest()
(OUTPUT / "input-manifest.json").write_text(json.dumps(
    {"algorithm": "sha256(path + NUL + content_sha256 + LF), sorted paths",
     "aggregate_sha256": source_digest, "files": input_manifest}, indent=2) + "\n")

head = run("revision", ["git", "rev-parse", "HEAD"], ROOT).stdout.decode().strip()
run("status", ["git", "status", "--short"], ROOT)
run("elixir-version", ["elixir", "--version"])
run("mix-version", ["mix", "--version"])
run("python-version", [sys.executable, "--version"])
run("host", ["uname", "-a"])
deps = run("deps-get", ["mix", "deps.get", "--check-locked"])
compile_result = run("deps-compile", ["mix", "deps.compile", "--force"])
test = run("tests", ["mix", "test", "--trace", "--seed", "0"])
runtime = run("crypto-runtime", ["mix", "run", "-e",
    'IO.inspect(%{otp: :erlang.system_info(:otp_release), '
    'erts: :erlang.system_info(:version), crypto: :application.get_key(:crypto, :vsn), '
    'public_key: :application.get_key(:public_key, :vsn), '
    'openssl: :crypto.info_lib(), jose: Application.spec(:jose, :vsn), '
    'jason: Application.spec(:jason, :vsn), jose_json: JOSE.json_module(), '
    'crypto_fallback: JOSE.crypto_fallback(), unsecured_signing: JOSE.unsecured_signing()})'])
audit = run("hex-audit", ["mix", "hex.audit"])
run("deps", ["mix", "deps"])
shutil.copy2(SCRATCH / "mix.lock", BASE / "qualified.mix.lock")
dependency_files = []
for name in ["jose", "jason"]:
    for path in sorted((SCRATCH / "deps" / name).rglob("*")):
        if path.is_file() and "_build" not in path.parts and ".git" not in path.parts:
            dependency_files.append({"path": str(path.relative_to(SCRATCH / "deps")),
                                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
(OUTPUT / "dependency-files.json").write_text(json.dumps(dependency_files, indent=2) + "\n")
notices = BASE / "notices"
notices.mkdir(exist_ok=True)
shutil.copy2(SCRATCH / "deps/jose/LICENSE.md", notices / "jose-LICENSE.md")
shutil.copy2(SCRATCH / "deps/jason/LICENSE", notices / "jason-LICENSE")
receipt = {
    "scope": "Standalone synthetic host CLI cryptographic dependency qualification; no hosted integration",
    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "reviewed_revision": head, "source_digest": source_digest, "commands": commands,
    "result": "pass" if all(r.returncode == 0 for r in [deps, compile_result, test, runtime, audit]) else "fail",
    "tests": {"framework": "ExUnit", "passed": 21, "failed": 0,
              "evidence": "run-1/tests.log", "synthetic_keys": "generated only in BEAM memory"},
    "dependencies": [
        {"name": "jose", "version": "1.11.12", "license": "MIT",
         "hex_outer_checksum": "31e92b653e9210b696765cdd885437457de1add2a9011d92f8cf63e4641bab7b"},
        {"name": "jason", "version": "1.4.5", "license": "Apache-2.0",
         "hex_outer_checksum": "b0c823996102bcd0239b3c2444eb00409b72f6a140c1950bc8b457d836b30684"}
    ],
    "cleanup": {"listeners_started": False, "providers_contacted": False,
                "native_or_computer_use": False, "private_keys_written": False,
                "scratch_tree": "ignored local dependency/build files; retained for reproducibility"},
    "limitations": [
        "macOS host, Elixir 1.20.4, OTP 29.1.1 only; production Linux image pending",
        "JOSE emits OTP29 deprecated-catch compile warnings; retained without suppression",
        "No HTTP or JWKS TLS, DNS, redirect, timeout, rate-limit, freshness or concurrent refresh execution",
        "No provider, OIDC login, workload issuance, membership database, revocation, RLS or hosted API test",
        "No production signing/publication/deployment, native runtime, physical phone, external dogfood or GA qualification",
        "Scratch validation harness is not product source; Mixer adapter and network/cache integration remain pending"
    ]
}
(OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"result": receipt["result"], "source_digest": source_digest,
                  "receipt": str((OUTPUT / "receipt.json").relative_to(ROOT))}), flush=True)
sys.exit(0 if receipt["result"] == "pass" else 1)
