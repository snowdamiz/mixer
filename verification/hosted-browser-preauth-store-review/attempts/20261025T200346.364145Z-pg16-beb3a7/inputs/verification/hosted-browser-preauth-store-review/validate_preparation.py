#!/usr/bin/env python3
"""Validate review preparation only. Never load or run the product candidate."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def main() -> None:
    packet = Path(__file__).resolve().parent
    root = packet.parents[1]
    plan = json.loads((packet / "adversity-plan.json").read_text())
    controls = plan["controls"]
    assert len(controls) == plan["control_count"] == 44
    assert len({case["id"] for case in controls}) == 44
    assert all(case["status"] == "pending_candidate_freeze" for case in controls)
    assert all(case["executed"] is False for case in controls)
    assert plan["candidate_accepted"] is False
    assert plan["candidate_implementation_sources_read"] is False
    assert plan["candidate_compiled_or_executed"] is False
    assert plan["postgres_started"] is False
    assert plan["native_ui_capture_started"] is False

    files = [
        root / "docs/hosted-browser-preauth-store-review.md",
        packet / "adversity-plan.json",
        packet / "synthetic_runtime_fixture.exs",
        Path(__file__).resolve(),
    ]
    for path in files:
        data = path.read_text()
        assert data.endswith("\n"), path
        assert not any(line.endswith((" ", "\t")) for line in data.splitlines()), path

    relative_fixture = "verification/hosted-browser-preauth-store-review/synthetic_runtime_fixture.exs"
    command = [
        "elixir",
        "-e",
        "path = hd(System.argv()); source = File.read!(path); "
        "Code.string_to_quoted!(source); "
        'true = IO.iodata_to_binary(Code.format_string!(source)) <> "\\n" == source; '
        'IO.puts("parse_and_format_only_no_evaluation")',
        relative_fixture,
    ]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    print(
        json.dumps(
            {
                "scope": "review_preparation_only",
                "pending_controls": len(controls),
                "candidate_tests_run": 0,
                "owned_postgres_started": 0,
                "native_ui_capture_started": 0,
                "fixture_validation": result.stdout.strip(),
                "fixture_command": command,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
