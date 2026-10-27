#!/usr/bin/env python3
"""Apply and verify only the six dispatcher files using the installed formatter."""

from pathlib import Path
import datetime
import hashlib
import json
import os
import signal
import subprocess
import time


PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
BEFORE = json.loads((PACKET / "source-before.json").read_text())
FILES = BEFORE["canonical_files"]
EXPECTED = [
    "hosted/lib/mixer_hosted_web/browser_workspace_dispatcher.ex",
    "hosted/lib/mixer_hosted_web/browser_workspace_dispatcher/capture_adapter.ex",
    "hosted/lib/mixer_hosted_web/browser_workspace_dispatcher/request.ex",
    "hosted/test/mixer_hosted_web/browser_workspace_dispatcher_capture_adapter_test.exs",
    "hosted/test/mixer_hosted_web/browser_workspace_dispatcher_request_test.exs",
    "hosted/test/mixer_hosted_web/browser_workspace_dispatcher_test.exs",
]
assert FILES == EXPECTED
COMMANDS = []


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    return {name: digest(ROOT / name) for name in FILES}


def tree_digest(values):
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def run(label, argv, cwd=ROOT):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    start = time.monotonic()
    process = subprocess.Popen(
        argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    stdout_path = PACKET / "commands" / f"{label}.stdout"
    stderr_path = PACKET / "commands" / f"{label}.stderr"
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    row = {
        "label": label, "argv": list(map(str, argv)), "cwd": str(cwd),
        "started": started, "elapsed_seconds": round(time.monotonic() - start, 6),
        "pid": process.pid, "owned_process_group": process.pid,
        "exit_code": process.returncode, "timed_out": timed_out,
        "stdout": str(stdout_path.relative_to(PACKET)),
        "stderr": str(stderr_path.relative_to(PACKET)),
        "stdout_sha256": digest(stdout_path), "stderr_sha256": digest(stderr_path),
        "direct_child_reaped": process.returncode is not None,
    }
    COMMANDS.append(row)
    (PACKET / "commands" / f"{label}.json").write_text(json.dumps(row, indent=2) + "\n")
    if process.returncode != 0 or timed_out:
        raise RuntimeError(f"{label} failed; see its captured output")
    return stdout.decode()


status = "failed"
failure = None
try:
    assert manifest() == BEFORE["sha256"], "canonical preimages changed before formatter"
    assert {
        name: digest(ROOT / name) for name in BEFORE["protected_sha256"]
    } == BEFORE["protected_sha256"], "protected inputs changed before formatter"
    prefix = ["/usr/bin/env", "ERL_FLAGS=+S 2:2 +A 1"]
    run("elixir-version", prefix + ["/opt/homebrew/bin/elixir", "--version"])
    run("mix-version", prefix + ["/opt/homebrew/bin/mix", "--version"])
    relative_files = [str(Path(name).relative_to("hosted")) for name in FILES]
    formatter = prefix + ["/opt/homebrew/bin/mix", "format", "--dot-formatter", ".formatter.exs"]
    run("format-six-files", formatter + relative_files, ROOT / "hosted")
    run("check-formatted-six-files", formatter + ["--check-formatted"] + relative_files, ROOT / "hosted")
    output = run(
        "normalized-ast-equivalence",
        prefix + ["/opt/homebrew/bin/elixir", str(PACKET / "ast_equivalence.exs"),
                  str(ROOT), str(PACKET / "before")] + FILES,
    )
    ast_rows = []
    for line in output.splitlines():
        name, before_hash, after_hash, result = line.split("\t")
        assert result == "equal" and before_hash == after_hash
        ast_rows.append({"path": name, "before_sha256": before_hash,
                         "after_sha256": after_hash, "normalized_ast_equal": True})
    assert [row["path"] for row in ast_rows] == FILES
    (PACKET / "ast-equivalence.json").write_text(json.dumps({
        "status": "passed", "normalization": "Remove AST metadata lists with Macro.prewalk; preserve all forms, arguments and literals; exact === comparison.",
        "scope": "Syntax and parsed program equivalence only; no modules compiled or evaluated.",
        "rows": ast_rows,
    }, indent=2) + "\n")
    run("git-diff-check-six-files", ["git", "diff", "--check", "--"] + FILES)
    run("canonical-diff", ["git", "diff", "--"] + FILES)
    assert {
        name: digest(ROOT / name) for name in BEFORE["protected_sha256"]
    } == BEFORE["protected_sha256"], "protected inputs changed after formatter"
    status = "passed"
except BaseException as error:
    failure = repr(error)
    raise
finally:
    after = manifest()
    changed = [name for name in FILES if after[name] != BEFORE["sha256"][name]]
    source_after = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "sha256": after, "tree_digest_sha256": tree_digest(after),
        "changed_canonical_files": changed,
        "protected_sha256": {name: digest(ROOT / name) for name in BEFORE["protected_sha256"]},
        "formatter_config_sha256": digest(ROOT / "hosted/.formatter.exs"),
    }
    (PACKET / "source-after.json").write_text(json.dumps(source_after, indent=2) + "\n")
    receipt = {
        "status": status, "failure": failure,
        "scope": "Formatting-only correction of the six dispatcher product/test files from d04fd5cc; explicit installed Elixir formatter inputs; syntax/normalized AST equivalence and formatter check.",
        "source_revision": BEFORE["head"],
        "before_tree_digest_sha256": BEFORE["tree_digest_sha256"],
        "after_tree_digest_sha256": source_after["tree_digest_sha256"],
        "changed_canonical_files": changed, "commands": COMMANDS,
        "protected_inputs_unchanged": source_after["protected_sha256"] == BEFORE["protected_sha256"],
        "formatter_config_unchanged": source_after["formatter_config_sha256"] == BEFORE["formatter_config"]["sha256"],
        "cleanup": {"all_direct_command_children_reaped": all(row["direct_child_reaped"] for row in COMMANDS),
                    "owned_native_instances_started": 0, "owned_services_started": 0,
                    "persistent_scratch_created": False, "global_process_inventory_performed": False},
        "limitations": ["No behavioral tests rerun for whitespace-only formatting.",
                        "No application startup, Repo/PG harness, compile, dependency fetch or mutation, CI rerun, callback work, or native runtime/UI/capture commands.",
                        "Remote original Phoenix run failed before compile/tests; new remote CI remains pending delivery.",
                        "Phones disconnected; native simulator/emulator runtime and computer use remain paused; no GA or release qualification claimed."],
    }
    (PACKET / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": status, "changed_canonical_files": changed,
                      "after_tree_digest_sha256": source_after["tree_digest_sha256"],
                      "receipt": str(PACKET / "receipt.json")}))
