#!/usr/bin/env python3
"""Exercise the actual ordinary GuestFrame body with deterministic framework callbacks."""

import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("activity", type=Path)
    parser.add_argument("--jdk", type=Path, required=True)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    activity = args.activity.read_text()
    panel = activity.split("private static final class ChecklistPanel {", 1)[1]

    def extract(start, end):
        return start + panel.split(start, 1)[1].split(end, 1)[0]

    frame = extract("        private final class GuestFrame extends LinearLayout {", "\n        }\n    }\n}") + "\n        }"
    close = extract("        void close(Runnable completion)", "        private String installation()")
    enable = extract("        private boolean enableGuest(long facade", "        @SuppressWarnings")
    done = extract("            done.setOnClickListener(view -> close(", "\n")
    test = Path(__file__).with_name("GuestFrameChecks.java").read_text()
    test = test.replace("    // PRODUCTION GUEST FRAME", close + enable + frame)
    test = test.replace("        // PRODUCTION DONE WIRING", done)
    if args.baseline:
        test = test.replace("        check.foregroundChanged();\n", "")
    with tempfile.TemporaryDirectory(prefix="fieldlog-guest-frame-") as work:
        source = Path(work) / "GuestFrameChecks.java"
        source.write_text(test)
        subprocess.run([args.jdk / "bin/javac", "--release", "17", "-d", work, source], check=True, timeout=30)
        result = subprocess.run(
            [args.jdk / "bin/java", f"-DnoBuffer={str(args.baseline).lower()}", "-cp", work, "GuestFrameChecks"], timeout=15, text=True, capture_output=True
        )
        if args.baseline:
            expected = "AssertionError: draw without a committed buffer called the display witness"
            if result.returncode != 1 or expected not in result.stderr:
                raise SystemExit(f"Unexpected baseline result ({result.returncode})\n{result.stdout}{result.stderr}")
            print(f"REPRODUCED {expected}")
        else:
            print(result.stdout, end="")
            if result.returncode:
                raise SystemExit(result.stderr)


if __name__ == "__main__":
    main()
