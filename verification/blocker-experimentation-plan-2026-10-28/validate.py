#!/usr/bin/env python3
"""Validate this planning slice; does not compile or execute product/native code."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import platform
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = json.loads((OUT / "baseline.json").read_text())
checks = []
commands = []


def check(name, condition):
    checks.append({"name": name, "passed": bool(condition)})


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def run(name, argv, timeout=120):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=timeout)
    (OUT / (name + ".stdout")).write_bytes(result.stdout)
    (OUT / (name + ".stderr")).write_bytes(result.stderr)
    commands.append({"argv": argv, "cwd": str(ROOT), "started_at_utc": started,
                     "exit_code": result.returncode, "stdout": name + ".stdout",
                     "stderr": name + ".stderr", "timeout_seconds": timeout})
    check(name, result.returncode == 0)
    return result


w = json.loads((ROOT / "work-graph.json").read_text())
g = json.loads((ROOT / "gates/ga.json").read_text())
m = json.loads((ROOT / "dogfood/receipts/milestones.json").read_text())
plan = (ROOT / "mixer-product-plan.md").read_text()
adr_path = "docs/adrs/0002-empirical-budgets-and-blocker-experiments.md"
adr = (ROOT / adr_path).read_text()
check("W01-W18 retained", [x["id"] for x in w["packages"]] == [f"W{i:02}" for i in range(1, 19)])
check("G01-G38 retained", [x["id"] for x in g["gates"]] == [f"G{i:02}" for i in range(1, 39)])
check("D0-D8 retained", [x["id"] for x in m["milestones"]] == [f"D{i}" for i in range(9)])
check("entire package array unchanged", digest(w["packages"]) == BASE["packages_digest"])
check("entire gate array unchanged", digest(g["gates"]) == BASE["gates_digest"])
check("entire dogfood file unchanged", digest(m) == BASE["milestones_digest"])
check("current native policy unchanged", w["verificationPolicy"]["currentNativeTesting"] == BASE["native_policy"])
check("native runtime stays paused", w["verificationPolicy"]["currentNativeTesting"]["status"] == "paused")
a = w["agentConfiguration"]
check("controller unchanged", a["controller"] == BASE["controller"])
check("ordinary delegate unchanged", a["delegates"] == BASE["delegates"])
check("Astra model and effort explicit", a["escalation"]["model"] == "gpt-6-astra" and a["escalation"]["reasoningEffort"] == "xhigh")
check("Astra fresh context explicit", a["escalation"]["context"] == "fresh; fork_turns none")
p = w["executionPolicy"]
check("two competing hypotheses required", p["campaignRules"]["competingHypothesesMinimum"] == 2)
check("failed-approach threshold explicit", p["campaignRules"]["distinctFailedApproachesBeforeEscalation"] == 2)
check("preparation threshold explicit", p["campaignRules"]["preparationOnlyCyclesBeforeEscalation"] == 2)
c = p["initialVmCampaign"]
check("VM campaign planned only", c["state"] == "planned" and "no experiment executed" in c["qualification"])
check("finite full-run count", c["maxFullWorkloadAttempts"] == 5)
check("independent capacity/work variants", [(x["residents"], x["cacheWork"]) for x in c["variants"][:4]] == [(64, 64000000), (64, 128000000), (128, 64000000), (256, 64000000)])
check("conditional combined variant", c["variants"][4]["name"] == "combined-if-justified")
check("new product plan sections", "### 20.3 Calibrate experimental limits" in plan and "### 24.4 Aggressive blocker experiments" in plan)
check("experiment versus production distinction", "Such selection does not alter public/installed production policy" in plan)
check("no recursive review requirement", "do not create a recursive acceptance chain by default" in plan)
check("native work independent of full VM", "Native shared-app work can advance independently of VM execution" in plan)
check("main scope index corrected", "mixer-product-plan.md        # binding product scope" in plan)
check("stale plan-only objective removed", "The immediate deliverable is this detailed implementation plan" not in plan)
check("same-owner full corpus and counters", "two corpus" in adr and "one initialized owner" in adr and "cumulative" in adr)
check("bounded comparison preserves independent limits", all(s in adr for s in ["16-MiB cache", "8-MiB entry", "64 active pins", "48-MiB guest", "256-MiB combined", "existing deadlines"]))
check("experiment reuses baseline harness", "Reuse the original bounded baseline harness" in adr)
check("no hidden accounting reduction", "Do not lower" in adr and "accounting charges" in adr)
check("memory metrics kept distinct", "peak RSS" in adr and "logical allocation/reservation" in adr)
check("security and process holds retained", all(s in adr for s in ["local-custody", "UnitA", "security denials", "No prohibited action is retried"]))
check("AGENTS includes Astra escalation", "gpt-6-astra" in (ROOT / "AGENTS.md").read_text())
for f in ["PLAN.md", "STATUS.md"]:
    check(f + " links selected policy", adr_path in (ROOT / f).read_text())
check("gate policy cannot promote diagnostics", "do not pass a GA gate" in g["executionPolicy"]["promotionRule"])

paths = ["AGENTS.md", "mixer-product-plan.md", "PLAN.md", "STATUS.md",
         "work-graph.json", "gates/ga.json", adr_path]
for relative in paths:
    if not relative.endswith(".md"):
        continue
    text = (ROOT / relative).read_text()
    check(relative + " balanced code fences", sum(line.startswith("```") for line in text.splitlines()) % 2 == 0)
for target in re.findall(r"\]\(([^)]+)\)", adr):
    if "://" not in target:
        check("ADR link " + target, ((ROOT / adr_path).parent / target.split("#")[0]).exists())

# Semantic checks above are backed by the existing manifest/acceptance guardrail.
run("policy", ["python3", "-B", "scripts/check-policy.py"])
run("diff-check", ["git", "diff", "--check", "--", *paths])
run("git-version", ["git", "--version"])
run("python-version", ["python3", "--version"])
changed = subprocess.check_output(["git", "diff", "--name-only", "--", "vm/src",
                                  "native/android/app", "cli/Sources", "console/src"], cwd=ROOT, text=True)
check("no product-engine edits in this planning slice", changed == "")
unrelated = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
             for path in BASE["unrelated_dirty_inputs"]}
check("other lanes dirty sources unchanged", unrelated == BASE["unrelated_dirty_inputs"])

result = {"status": "passed" if all(x["passed"] for x in checks) else "failed",
          "scope": "planning integrity only; no VM experiment, product compile, native/UI/capture, release or GA qualification",
          "checks": checks, "commands": commands}
(OUT / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
artifacts = paths + [str(x.relative_to(ROOT)) for x in OUT.iterdir()
                     if x.is_file() and x.name not in {"receipt.json", "delivery.json"}]
hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(set(artifacts))}
tree = hashlib.sha256("".join(p + "\0" + h + "\n" for p, h in hashes.items()).encode()).hexdigest()
receipt = {"schema": 1, "client_date": "2026-10-28",
           "completed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "status": result["status"], "scope": result["scope"],
           "baseline_revision": BASE["revision"],
           "current_revision_before_delivery": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
           "source_tree_digest": tree, "digest_scope": "sorted path NUL SHA256 newline; receipt/delivery excluded",
           "files_sha256": hashes, "python_runtime": platform.python_version(),
           "passed_checks": sum(x["passed"] for x in checks), "total_checks": len(checks),
           "package_states": dict(collections.Counter(x["state"] for x in w["packages"])),
           "gate_states": dict(collections.Counter(x["status"] for x in g["gates"])),
           "commands_and_outputs": "validation.json", "reviews": "reviews.md",
           "pending": ["VM campaign execution", "native/UI/capture resume", "physical phones", "production profile changes", "all original product gates"]}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": result["status"], "passed": receipt["passed_checks"],
                  "total": len(checks), "failures": [x["name"] for x in checks if not x["passed"]],
                  "source_tree_digest": tree}, indent=2))
raise SystemExit(result["status"] != "passed")
