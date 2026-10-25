#!/usr/bin/env python3
"""Verify the bounded website-token contrast correction without starting a UI."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
assert not (OUT / "receipt.json").exists()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
    return sum(c * w for c, w in zip(linear, (.2126, .7152, .0722)))


def contrast(foreground, background):
    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + .05) / (dark + .05)


baseline_path = ROOT / "verification/console-brand-current-check/receipt.json"
baseline = json.loads(baseline_path.read_text())["checkedSourceFiles"]
inputs = {name: sha(ROOT / name) for name in baseline}
assert [name for name, value in inputs.items() if value != baseline[name]] == ["console/src/styles.css"]
styles = (ROOT / "console/src/styles.css").read_text()
tokens = dict(re.findall(r"(--[\w-]+):([^;}]+)", (ROOT / "console/src/brand.css").read_text()))
rows = []
for selector, previous, background in [("rail-caption", "#787c73", tokens["--paper"]),
                                       ("app-footer", "#878b80", "#fdfcf9")]:
    block = re.search(r"\." + selector + r" \{([^}]+)\}", styles).group(1)
    assert "color: var(--muted);" in block
    current = contrast(tokens["--muted"], background)
    assert current >= 4.5
    rows.append({"selector": "." + selector, "previous": previous, "foreground": tokens["--muted"],
                 "background": background, "previousContrast": contrast(previous, background),
                 "currentContrast": current, "normalTextMinimum": 4.5})
commands = []
for label, argv in [("tests", ["npm", "test"]), ("build", ["npm", "run", "build"])]:
    result = subprocess.run(argv, cwd=ROOT / "console", capture_output=True, timeout=180)
    (OUT / (label + ".stdout")).write_bytes(result.stdout)
    (OUT / (label + ".stderr")).write_bytes(result.stderr)
    commands.append({"argv": argv, "cwd": "console", "exitCode": result.returncode,
                     "stdoutSHA256": sha(OUT / (label + ".stdout")), "stderrSHA256": sha(OUT / (label + ".stderr"))})
    assert result.returncode == 0, label
assert inputs == {name: sha(ROOT / name) for name in baseline}
receipt = {
    "schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "baseRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "sourceFiles": inputs, "verifierSHA256": sha(Path(__file__)),
    "node": subprocess.check_output(["node", "--version"], text=True).strip(),
    "npm": subprocess.check_output(["npm", "--version"], text=True).strip(),
    "python": subprocess.check_output(["python3", "--version"], text=True).strip(),
    "commands": commands, "contrast": rows, "sourceChanges": ["console/src/styles.css"],
    "scope": "Two text colors now use the existing website muted token; exact brand parity and existing console tests/typecheck/production build pass. No layout or interaction changes.",
    "visualEvidence": "Saved desktop/mobile screenshots reviewed before repair; no new screenshot or browser run while computer use is paused. Previous images show the original, lighter captions.",
    "limitations": ["Not a complete accessibility audit.", "Live customer API/auth/workflows and deployment remain pending."],
    "cleanup": {"browserStarted": False, "nativeStarted": False, "serverStarted": False}
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": "passed", "contrast": rows, "commandsPassed": len(commands)}))
