#!/usr/bin/env python3
"""Bounded offline validation of the six Console checkout input patterns."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
REVISION = "b231f3d405c06bfb348f193d46a348af0529bd84"
PATTERNS = ["/console/", "/website/src/styles.css", "/website/public/assets/flick-128.webp",
            "/website/public/assets/favicon-32.png", "/hosted/lib/mixer_hosted/authorization/scope.ex",
            "/hosted/.tool-versions"]
EXTERNAL_INPUTS = [entry.removeprefix("/") for entry in PATTERNS[1:]]
INSERTION = """        with:
          sparse-checkout-cone-mode: false
          sparse-checkout: |
            /console/
            /website/src/styles.css
            /website/public/assets/flick-128.webp
            /website/public/assets/favicon-32.png
            /hosted/lib/mixer_hosted/authorization/scope.ex
            /hosted/.tool-versions
"""


def write_json(name, value):
    (PACKET / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def child(scratch):
    started = time.monotonic()
    environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    commands = []

    def run(argv, cwd=ROOT, label=None):
        remaining = 52 - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("52-second inner deadline exhausted")
        result = subprocess.run(argv, cwd=cwd, env=environment, capture_output=True,
                                timeout=remaining, check=False)
        item = {"argv": [str(value) for value in argv], "cwd": str(cwd),
                "exit_code": result.returncode, "stdout": result.stdout.decode(errors="replace"),
                "stderr": result.stderr.decode(errors="replace")}
        commands.append(item)
        write_json("commands.json", commands)
        print(f"{label or argv[0]}: exit {result.returncode}", flush=True)
        if result.returncode:
            raise RuntimeError(item)
        return result.stdout

    workflow_path = ".github/workflows/console.yml"
    original = run(["git", "show", f"{REVISION}:{workflow_path}"], label="Baseline workflow read").decode()
    current = (ROOT / workflow_path).read_text()
    anchor = "      - uses: actions/checkout@v4\n"
    assert original.count(anchor) == 1
    assert current == original.replace(anchor, anchor + INSERTION), "Workflow changed beyond the checkout block"
    (PACKET / "console.yml.before").write_text(original)
    (PACKET / "console.yml.after").write_text(current)
    (PACKET / "sparse-patterns.txt").write_text("\n".join(PATTERNS) + "\n")
    head = run(["git", "rev-parse", "HEAD"], label="Current source revision").decode().strip()
    tree = run(["git", "rev-parse", f"{REVISION}^{{tree}}"], label="Baseline tree").decode().strip()
    git_version = run(["git", "--version"]).decode().strip()
    node_version = run(["node", "--version"]).decode().strip()
    entries = run(["git", "ls-tree", "-r", "-z", REVISION, "--", "console", *EXTERNAL_INPUTS],
                  label="Selected committed input list")
    files = []
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t")
        mode, kind, blob = metadata.decode().split()
        path = raw_path.decode()
        assert kind == "blob" and mode in ("100644", "100755"), f"Unexpected input mode: {path}"
        data = (ROOT / path).read_bytes()
        actual_blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        assert actual_blob == blob, f"Input differs from baseline commit: {path}"
        files.append({"path": path, "mode": mode, "git_blob_sha1": blob,
                      "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    assert sorted(path["path"] for path in files if not path["path"].startswith("console/")) == sorted(EXTERNAL_INPUTS)
    material = "".join(f"{file['sha256']}  {file['path']}\n" for file in files)
    manifest = {"source_revision": REVISION, "source_tree": tree, "observed_head": head,
                "patterns": PATTERNS, "digest_format": "sha256 of concatenated sha256-two-spaces-path-LF in Git path order",
                "selected_tree_sha256": hashlib.sha256(material.encode()).hexdigest(),
                "file_count": len(files), "total_input_bytes": sum(file["size_bytes"] for file in files),
                "files": files}
    write_json("input-manifest.json", manifest)
    package = json.loads((ROOT / "console/package.json").read_text())
    lock = json.loads((ROOT / "console/package-lock.json").read_text())
    assert lock["lockfileVersion"] == 3
    assert lock["packages"][""]["dependencies"] == package["dependencies"]
    assert lock["packages"][""]["devDependencies"] == package["devDependencies"]
    for location, record in lock["packages"].items():
        if not location:
            continue
        assert location.startswith("node_modules/") and not record.get("link")
        assert record.get("resolved", "").startswith("https://registry.npmjs.org/"), location
    optional_root_configs = [".npmrc", "package.json", "package-lock.json", "pnpm-workspace.yaml",
                             "babel.config.js", "babel.config.cjs", "babel.config.mjs", "babel.config.json",
                             ".babelrc", ".babelrc.json", ".babelrc.js", ".babelrc.cjs", ".browserslistrc",
                             ".postcssrc", ".postcssrc.json", ".postcssrc.yaml", ".postcssrc.yml",
                             ".postcssrc.js", ".postcssrc.cjs", ".postcssrc.mjs", ".postcssrc.ts",
                             "postcss.config.js", "postcss.config.cjs", "postcss.config.mjs",
                             "postcss.config.ts", "postcss.config.cts", "postcss.config.mts"]
    root_config_entries = run(["git", "ls-tree", "--name-only", REVISION, "--", *optional_root_configs],
                              label="Optional ancestor configuration input check")
    assert root_config_entries == b"", "A root configuration needs explicit closure review"
    audit = run(["node", str(PACKET / "source-audit.mjs"), str(ROOT), str(PACKET / "input-manifest.json")],
                label="Source AST parsing and input call inventory")
    (PACKET / "source-audit.json").write_bytes(audit)
    audit_data = json.loads(audit)
    objects = Path(run(["git", "rev-parse", "--path-format=absolute", "--git-path", "objects"],
                       label="Read-only source object directory").decode().strip())
    repository = scratch / "repository"
    run(["git", "init", "--quiet", "--initial-branch=sparse-check-only", str(repository)], label="Initialize isolated repository")
    (repository / ".git/objects/info/alternates").write_text(str(objects) + "\n")
    run(["git", "config", "core.sparseCheckout", "true"], cwd=repository)
    run(["git", "config", "core.sparseCheckoutCone", "false"], cwd=repository)
    (repository / ".git/info/sparse-checkout").write_text("\n".join(PATTERNS) + "\n")
    run(["git", "read-tree", "--reset", "-u", REVISION], cwd=repository, label="Offline sparse materialization")
    run(["git", "update-ref", "--no-deref", "HEAD", REVISION], cwd=repository,
        label="Set detached revision in isolated repository only")
    assert run(["git", "rev-parse", "HEAD"], cwd=repository / "console",
               label="Exact revision remains available from console directory").decode().strip() == REVISION
    index = run(["git", "ls-files", "-t", "-z", "--", "console", *EXTERNAL_INPUTS], cwd=repository,
                label="Selected isolated sparse index enumeration")
    selected = [entry[2:].decode() for entry in index.split(b"\0") if entry.startswith(b"H ")]
    assert sorted(selected) == sorted(file["path"] for file in files), "Sparse selection differs from input manifest"
    for file in files:
        actual = (repository / file["path"]).read_bytes()
        assert hashlib.sha256(actual).hexdigest() == file["sha256"], file["path"]
    # Enumerate the small materialized filesystem only, excluding the isolated Git metadata.
    materialized = []
    for directory, directories, filenames in os.walk(repository):
        if Path(directory) == repository:
            directories.remove(".git")
        materialized.extend(str((Path(directory) / filename).relative_to(repository)) for filename in filenames)
    assert sorted(materialized) == sorted(file["path"] for file in files), "Sparse checkout materialized an omitted path"
    diff = run(["git", "diff", "--", workflow_path], label="Owned workflow diff")
    (PACKET / "workflow.patch").write_bytes(diff)
    write_json("validation.json", {
        "result": "passed-source-and-offline-materialization-only",
        "owned_pid": os.getpid(), "owned_pgid": os.getpgrp(), "elapsed_seconds": round(time.monotonic() - started, 3),
        "tools": {"python": platform.python_version(), "git": git_version, "node": node_version,
                  "source_parser": audit_data["parser"], "platform": platform.platform()},
        "source_revision": REVISION, "source_tree": tree, "selected_tree_sha256": manifest["selected_tree_sha256"],
        "workflow_sha256": hashlib.sha256(current.encode()).hexdigest(),
        "verification_source_sha256": {name: hashlib.sha256((PACKET / name).read_bytes()).hexdigest()
                                       for name in ["validate.py", "source-audit.mjs"]},
        "checks": {"workflow_checkout_only_change": "passed", "selected_inputs_match_committed_bytes": "passed",
                   "lockfile_has_no_local_or_linked_packages": "passed", "source_ast_import_closure": "passed",
                   "isolated_offline_git_sparse_materialization": "passed", "selected_files_match_sha256": "passed",
                   "omitted_paths_absent": "passed", "revision_available_from_console_directory": "passed"},
        "source_files_parsed": audit_data["parsedFiles"], "selected_files": len(files),
        "selected_input_bytes": manifest["total_input_bytes"],
        "not_run": ["npm ci", "TypeScript compiler/typecheck", "npm test", "Elixir", "Vite build",
                    "GitHub Actions checkout/setup/runtime", "browser/UI/capture/native devices"],
        "limitations": ["Source parsing and exact local sparse materialization do not prove CI runtime success or checkout timing.",
                        "Parser call inventory supplements manual input review; computed runtime inputs require that review.",
                        "CI network, action behavior and Ubuntu runtime remain for the next pushed workflow run."]})
    print(f"PASS: {len(files)} selected files ({manifest['total_input_bytes']} bytes), {audit_data['parsedFiles']} parsed source files", flush=True)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        child(Path(sys.argv[2]))
        return
    scratch = Path(tempfile.mkdtemp(prefix="mixer-console-sparse-"))
    started = time.monotonic()
    command = [sys.executable, str(Path(__file__).resolve()), "--child", str(scratch)]
    process = None
    timed_out = False
    with (PACKET / "validation.stdout").open("wb") as out, (PACKET / "validation.stderr").open("wb") as err:
        try:
            process = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=err, start_new_session=True)
            try:
                process.wait(timeout=55)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        finally:
            shutil.rmtree(scratch)
    receipt = {"argv": command, "cwd": str(ROOT), "owned_pid": process.pid, "owned_pgid": process.pid,
               "deadline_seconds": 55, "elapsed_seconds": round(time.monotonic() - started, 3),
               "exit_code": process.returncode, "timed_out": timed_out,
               "cleanup": {"scratch": str(scratch), "removed": not scratch.exists(),
                           "source_repository_index_mutated": False, "network_fetch": False,
                           "native_or_capture_process_started": False}}
    write_json("runner-receipt.json", receipt)
    print((PACKET / "validation.stdout").read_text(), end="")
    print((PACKET / "validation.stderr").read_text(), end="", file=sys.stderr)
    if timed_out or process.returncode:
        raise SystemExit(process.returncode or 1)


if __name__ == "__main__":
    main()
