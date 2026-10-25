"""Capture the final source and run only this lane's bounded, isolated review."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parent.parent
NODE = Path("/Users/andreyyurlov/.local/state/fnm_multishells/47185_1792819498381/bin/node")
BASE = "50f70a798fea43e1e77b1d95faa1bbda3fc029e0"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_json(name, value):
    (PACKET / name).write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def command(argv, name, cwd=ROOT):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, check=False)
    (PACKET / f"{name}.stdout").write_bytes(result.stdout)
    (PACKET / f"{name}.stderr").write_bytes(result.stderr)
    return {"argv": [str(arg) for arg in argv], "cwd": str(cwd), "exitCode": result.returncode,
            "stdout": f"{name}.stdout", "stdoutSha256": sha(result.stdout),
            "stderr": f"{name}.stderr", "stderrSha256": sha(result.stderr)}


if (PACKET / "source-snapshot").exists():
    raise SystemExit("Refusing to overwrite an existing review snapshot; retain prior attempt evidence.")

console_files = [path for path in (ROOT / "console/src").rglob("*") if path.is_file()]
console_files += [path for path in (ROOT / "console/public").rglob("*") if path.is_file()]
console_files += [ROOT / "console" / name for name in ["package.json", "package-lock.json", "index.html", "tsconfig.json", "vite.config.ts", "THIRD_PARTY.yml"]]
inputs = console_files + [ROOT / name for name in [
    "AGENTS.md", "mixer-product-plan.md", "hosted/lib/mixer_hosted/builds/lifecycle.ex",
    "docs/hosted-build-lifecycle.md", "docs/console-build-overview.md", "website/src/styles.css",
    "website/public/assets/flick-128.webp", "website/public/assets/favicon-32.png",
]]
manifest = {}
for source in sorted(set(inputs)):
    relative = source.relative_to(ROOT)
    data = source.read_bytes()
    destination = PACKET / "source-snapshot" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    manifest[str(relative)] = sha(data)
tree_digest = sha("".join(f"{path}\0{digest}\n" for path, digest in manifest.items()).encode())
save_json("source-manifest.json", {"baseRevision": BASE, "baseRevisionSource": "root message; no Git command used",
    "files": manifest, "treeDigest": tree_digest,
    "treeDigestMethod": "sha256 of sorted repository relative path + NUL + file sha256 + LF"})
commands = [command([str(NODE), "--version"], "node-version"), command(["python3", "--version"], "python-version")]
versions = {}
for package in ["solid-js", "@solidjs/router", "vite", "vite-plugin-solid", "typescript"]:
    path = ROOT / "console/node_modules" / package / "package.json"
    versions[package] = {"version": json.loads(path.read_text())["version"], "packageJsonSha256": sha(path.read_bytes())}
review = command([str(NODE), "--test", str(PACKET / "review-tests.mjs")], "review")
commands.append(review)
changed = [path for path, digest in manifest.items() if sha((ROOT / path).read_bytes()) != digest]
artifacts = {}
for output in ["compiled-component", "production-dist"]:
    for path in sorted((PACKET / output).rglob("*")):
        if path.is_file():
            artifacts[str(path.relative_to(PACKET))] = sha(path.read_bytes())
for name in ["review-tests.mjs", "run_review.py", "inspect_html.py", "typecheck.stdout", "typecheck.stderr"]:
    path = PACKET / name
    if path.exists():
        artifacts[name] = sha(path.read_bytes())
symlinks = [str(path.relative_to(PACKET)) for path in PACKET.rglob("*") if path.is_symlink()]
receipt = {"schema": 1, "review": "console-build-overview-independent-review", "recordedAt": datetime.now(timezone.utc).isoformat(),
    "outcome": "passed scoped source and host review" if review["exitCode"] == 0 and not changed and not symlinks else "failed review; see retained output",
    "baseRevision": BASE, "baseRevisionSource": "root message; no Git command used", "sourceTreeDigest": tree_digest,
    "sourceManifest": "source-manifest.json", "sourceChangedDuringRun": changed,
    "toolchain": {"nodeRequestedPath": str(NODE), "nodeRealPath": str(NODE.resolve()), "nodeExecutableSha256": sha(NODE.resolve().read_bytes()), "dependencies": versions},
    "commands": commands, "artifactSha256": artifacts,
    "scope": ["Exact per-platform full identity/common scope, all lifecycle states and worker uncertainty, immutable snapshots, UTF-8 text boundaries, missing/invalid input rejection, compiled Solid SSR hostile labels, read-only presentation, isolated strict console source typecheck, Vite production exclusion and exact website brand inputs."],
    "limitations": ["SSR and local production build only; no browser, reactive DOM transition, focus, screen reader, contrast or responsive-layout execution; root owns browser verification.",
        "No installed customer API/auth integration, Cloudflare hosting, actions, signing, distribution, native/device, customer/operational or GA acceptance.",
        "No producer whole-suite replay in this packet; independent controls use the actual captured domain and compiled Solid component. Producer and root own their suite receipts.",
        "Console tsconfig skipLibCheck=true leaves dependency declarations outside this source typecheck; existing dependency limitation remains unchanged."],
    "cleanup": {"temporaryDependencySymlinksRemaining": symlinks, "temporaryDependencySymlinkRemoved": not symlinks,
        "sharedNodeModulesModified": False, "serversStarted": 0, "browserSessionsStarted": 0, "nativeInstancesStarted": 0,
        "retainedArtifacts": "Owned immutable source snapshot, SSR bundle and production build retained as review evidence; no disposable temporary tree remains."}}
save_json("receipt.json", receipt)
print(json.dumps({"outcome": receipt["outcome"], "sourceTreeDigest": tree_digest, "exitCode": review["exitCode"], "sourceChangedDuringRun": changed, "symlinksRemaining": symlinks}, indent=2))
sys.exit(0 if review["exitCode"] == 0 and not changed and not symlinks else 1)
