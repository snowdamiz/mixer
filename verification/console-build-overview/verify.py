#!/usr/bin/env python3
"""Capture the bounded console checks without keeping disposable build output."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "console"
HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_entry(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(path.read_bytes()), "bytes": path.stat().st_size}


def command(args, log_name):
    result = subprocess.run(args, cwd=CONSOLE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    (HERE / log_name).write_bytes(result.stdout)
    return {"argv": args, "cwd": "console", "exitCode": result.returncode, "output": log_name,
            "outputSha256": digest(result.stdout)}


def main():
    inputs = sorted(set(
        list((CONSOLE / "src").rglob("*.ts")) + list((CONSOLE / "src").rglob("*.tsx")) +
        list((CONSOLE / "src").rglob("*.css")) + list((CONSOLE / "tests").glob("*")) + [
            CONSOLE / "package.json", CONSOLE / "package-lock.json", CONSOLE / "tsconfig.json",
            CONSOLE / "vite.config.ts", CONSOLE / "index.html", CONSOLE / "public/assets/flick-128.webp",
            CONSOLE / "public/favicon.svg", ROOT / "website/src/styles.css",
            ROOT / "AGENTS.md", ROOT / "mixer-product-plan.md", ROOT / "docs/hosted-build-lifecycle.md",
            ROOT / "hosted/lib/mixer_hosted/builds/lifecycle.ex", ROOT / "docs/console-build-overview.md",
            HERE / "verify.py", HERE / "text-boundaries.mjs", HERE / "text-boundaries.exs",
        ]))
    sources = [file_entry(path) for path in inputs if path.is_file()]
    source_digest = digest("".join(f'{entry["path"]}\0{entry["sha256"]}\n' for entry in sources).encode())
    tools = {"python": platform.python_version(), "os": platform.platform(), "machine": platform.machine()}
    for name, args in {"node": ["node", "--version"], "npm": ["npm", "--version"],
                       "typescript": ["./node_modules/.bin/tsc", "--version"],
                       "vite": ["./node_modules/.bin/vite", "--version"]}.items():
        tools[name] = subprocess.check_output(args, cwd=CONSOLE, text=True).strip()
    for name in ["solid-js", "@solidjs/router", "vite-plugin-solid"]:
        tools[name] = json.loads((CONSOLE / "node_modules" / name / "package.json").read_text())["version"]
    tools["elixir"] = subprocess.check_output(["elixir", "--version"], cwd=ROOT, text=True,
        env={**os.environ, "ERL_FLAGS": "+S 2:2"}).strip()
    (HERE / "sources.json").write_text(json.dumps({"digestFormat": "sha256 of sorted path NUL sha256 LF entries",
                                                "sourceTreeDigest": source_digest, "files": sources}, indent=2) + "\n")
    cache = CONSOLE / "node_modules/.cache"
    cache.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="mixer-build-overview-production-", dir=cache))
    output_files = []
    commands = []
    try:
        commands.append(command(["node", str(HERE / "text-boundaries.mjs")], "text-boundaries.log"))
        commands.append(command(["npm", "run", "typecheck"], "typecheck.log"))
        commands.append(command(["npm", "test"], "tests.log"))
        commands.append(command(["npm", "run", "build", "--", "--outDir", str(output)], "build.log"))
        output_files = [{"path": str(path.relative_to(output)), "sha256": digest(path.read_bytes()),
                         "bytes": path.stat().st_size} for path in sorted(output.rglob("*")) if path.is_file()]
    finally:
        shutil.rmtree(output)
    unchanged = all(path.is_file() and digest(path.read_bytes()) == entry["sha256"] for path, entry in
                    ((ROOT / item["path"], item) for item in sources))
    tests_output = (HERE / "tests.log").read_text()
    failed = any(item["exitCode"] != 0 for item in commands) or not unchanged
    receipt = {
        "schema": 1, "observedAt": datetime.now(timezone.utc).isoformat(),
        "inheritedBaseRevision": "50f70a798fea43e1e77b1d95faa1bbda3fc029e0",
        "revisionNote": "Base revision supplied by root; current working-tree files are bound by sources.json.",
        "sourceTreeDigest": source_digest, "sourceManifest": "sources.json", "sourceUnchangedDuringChecks": unchanged,
        "scope": "Producer host-only domain, compiled Solid SSR component, full console typecheck/tests, production build",
        "outcome": "passed producer checks; root browser/review acceptance pending" if not failed else "failed producer check",
        "tools": tools, "commands": commands,
        "tests": {"passed": int(re.search(r"^# pass (\d+)$", tests_output, re.MULTILINE)[1]),
                  "failed": int(re.search(r"^# fail (\d+)$", tests_output, re.MULTILINE)[1]),
                  "newDomainTests": 9, "newCompiledSolidViewTests": 6, "platformStatePairs": 64,
                  "crossLanguageTextBoundaryOutput": "text-boundaries.log"},
        "productionOutputs": output_files,
        "cleanup": {"temporaryProductionOutput": str(output.relative_to(ROOT)), "temporaryProductionOutputRemoved": not output.exists(),
                    "ownedCompiledViewTestDirectoriesRemaining": [str(path.relative_to(ROOT)) for path in cache.glob("mixer-build-overview-render-*")],
                    "serversStarted": 0, "browserTabsOpened": 0, "nativeInstancesStarted": 0},
        "supersededChecks": ["superseded-validation.json", "superseded-before-text-correction/receipt.json"],
        "limitations": [
            "No connected build API/authentication/authorization, real jobs, worker reconciliation, signing, distribution, release authority, billing or deployment.",
            "Read-only internal display view model; not a public Phoenix JSON contract.",
            "Browser runtime, responsive layout, selector/disclosure keyboard interaction, complete accessibility and root acceptance are separate checks.",
            "Existing skipLibCheck=true dependency declaration exception remains; owned application code is strict.",
            "No physical-device, native-runtime, FieldLog, hosted provider, operational or GA acceptance."
        ],
    }
    (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"outcome": receipt["outcome"], "tests": receipt["tests"], "sourceTreeDigest": source_digest,
                      "receipt": str((HERE / "receipt.json").relative_to(ROOT))}, indent=2))
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
