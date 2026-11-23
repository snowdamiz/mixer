"""Prepare an isolated F11 source export from the pinned Stage recipes."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PIN = "2843fdb54ccb062826e2a0fcbede91e2d0380d81"
TREE = "1476beb195a551c8a1f10c5e031649d66d6802d7"


def checked_replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected one source anchor: {old!r}")
    return text.replace(old, new)


def main(stage, fieldlog, work):
    original = stage / "tests/integration"
    vertical = original / "fieldlog-d8-f11-vertical-private"
    action = original / "fieldlog-d8-f11-action-private"
    def git(*args):
        return subprocess.check_output(["git", "-C", stage, *args])
    if git("rev-parse", PIN).decode().strip() != PIN or git("rev-parse", PIN + "^{tree}").decode().strip() != TREE:
        raise ValueError("Incorrect Stage revision or tree")
    for folder in (vertical, action, original / "fieldlog-d8-f11-signed"):
        for file in folder.iterdir():
            if file.is_file() and file.read_bytes() != git("show", f"{PIN}:{file.relative_to(stage)}"):
                raise ValueError(f"Stage recipe bytes differ: {file}")
    script = (vertical / "worker.sh").read_text().split("\nphase cargo\n")[0]
    import shlex
    script = checked_replace(script, 'recipe="$(cd "$(dirname "$0")" && pwd -P)"',
                             f"recipe={shlex.quote(str(vertical))}")
    script = checked_replace(script, 'mkdir "$work"/{source,lib,guest,tmp,pair-recipe,cargo}',
                             'mkdir "$work"/{source,lib,guest,tmp,pair-recipe}')
    script = script[:script.index('cargo_cache=')] + script[script.index('test "$(stage_git rev-parse'):]
    script = checked_replace(script, "phase dependencies", 'phase action-compose\n'
        f'python3 -B {shlex.quote(str(action / "compose.py"))} source "$source" '
        f'{shlex.quote(str(action))} "$work" "$app" "$recipe"\nphase dependencies')
    script_path = work / "prepare.sh"
    script_path.write_text(script)
    f04 = work / "f04"
    f04.mkdir()
    f04_patch = "tests/integration/fieldlog-d8-f04-signed/task-retry-replay.patch"
    (f04 / "task-retry-replay.patch").write_bytes(git("show", f"b9d227c81c:{f04_patch}"))
    subprocess.run(["/bin/bash", script_path, stage, fieldlog, f04, original / "fieldlog-d8-f11-signed", work],
                   check=True, env={**os.environ, "GIT_ALLOW_PROTOCOL": "file", "GIT_TERMINAL_PROMPT": "0"})

    toolchain = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
    guest = work / "guest"
    subprocess.run([toolchain / "clang", "--target=wasm32-unknown-none", "-Oz", "-ffreestanding",
                    "-fno-builtin", "-I", guest, "-Dvalid", "-c", vertical / "Guest.c", "-o", guest / "valid.o"], check=True)
    wasm = guest / "historical.wasm"
    subprocess.run([toolchain / "wasm-ld", "--no-entry", "--gc-sections", "--strip-all", "-z", "stack-size=16384",
                    "--max-memory=65536", *["--export=mixer_guest_" + name for name in
                      ("ui_start_v1", "ui_hydrate_v1", "ui_event_v1", "capability_ready_v1")],
                    guest / "valid.o", "-o", wasm], check=True)
    if hashlib.sha256(wasm.read_bytes()).hexdigest() != "b3def2b5d11c0a350d33a44ff0cd55f4a7e97f6979e547c49ab13bde696d4fe5":
        raise ValueError("Historical signed F11 payload digest differs")


if __name__ == "__main__":
    main(*[Path(arg).resolve(strict=True) for arg in sys.argv[1:]])
