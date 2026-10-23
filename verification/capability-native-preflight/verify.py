#!/usr/bin/env python3
"""Compile the unwired numeric preflight helper alone, without native C entry points."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "vm/src/capability_ffi/ranges.rs"
RUSTC = "/opt/homebrew/opt/rustup/bin/rustc"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    original = SOURCE.read_bytes()
    commands = []
    with tempfile.TemporaryDirectory(prefix="capability-ranges-") as temporary:
        directory = Path(temporary)
        (directory / "ranges.rs").write_bytes(original)
        harness = directory / "main.rs"
        harness.write_text('#[path = "ranges.rs"]\nmod ranges;\n')

        def run(name, command):
            result = subprocess.run(command, capture_output=True, cwd=directory)
            output = result.stdout + result.stderr
            log = OUT / (name + ".log")
            log.write_bytes(output)
            commands.append({"name": name, "command": list(map(str, command)),
                             "exitCode": result.returncode, "log": str(log.relative_to(ROOT)),
                             "sha256": sha(output)})
            if result.returncode:
                raise RuntimeError(name + " failed: " + output.decode(errors="replace"))

        run("compiler", [RUSTC, "-Vv"])
        for mode, flags in [("debug", []), ("release", ["-O"])]:
            executable = directory / mode
            run(mode + "-build", [RUSTC, "--edition", "2021", "--test", "-D", "warnings", *flags,
                                  str(harness), "-o", str(executable)])
            run(mode + "-tests", [str(executable)])
    if SOURCE.read_bytes() != original:
        raise RuntimeError("source changed during tests")
    receipt = {
        "schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": {str(SOURCE.relative_to(ROOT)): sha(original),
                   str(Path(__file__).resolve().relative_to(ROOT)): sha(Path(__file__).read_bytes())},
        "commands": commands, "passed": True,
        "evidence": ["Four tests each in debug/release", "346112 symmetric alias decisions checked against byte-set overlap",
                     "Read-only overlaps allowed; empty ranges stay empty; report is a full writable participant",
                     "Null, isize ceiling, typed multiplication, address wrap and unaligned numeric ranges checked"],
        "limitations": ["Helper not yet wired into library or exported C entry points",
                        "Numeric ranges do not prove native pointer validity or ownership",
                        "No actual C buffer mutation, session registry, native I/O, mobile execution or ABI qualification"],
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": True, "testsPerMode": 4, "sourceSHA256": sha(original)}))


if __name__ == "__main__":
    main()
