#!/usr/bin/env python3
"""Measure matched TaskCompletion turns on an already prepared Android emulator."""

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path

from matched_task import PAIRS, PRIOR, require, sha, spread


def read_sample(stdout, stderr, mode, expected):
    sample = json.loads(stdout)
    frames = [base64.b64decode(frame, validate=True) for frame in sample.pop("frames")]
    require([sha(frame) for frame in frames] == expected, f"{mode}: wrong document bytes")
    turns = sample["turnNS"]
    require(len(turns) == 3 and all(type(value) is int and value > 0 for value in turns),
            f"{mode}: expected three positive turn times")
    owned = mode.startswith("guest")
    require(sample["closed"] is owned, f"{mode}: unexpected VM closure")
    require(sample["refusals"] == (2 if mode.endswith("-control") else 0),
            f"{mode}: unexpected refusal count")
    if owned:
        require(len(sample["fuel"]) == 3 and all(type(value) is int and value > 0 for value in sample["fuel"]),
                f"{mode}: invalid guest fuel samples")
    if mode == "guest-control":
        require("TaskCompletion.swift:94:9" in sample["diagnostic"], "wrong guest source diagnostic")
    match = re.fullmatch(rb"peak-rss-kib=([1-9][0-9]*)\r?\n", stderr)
    require(match is not None, f"{mode}: missing wait4 memory reading or unexpected stderr")
    return {**sample, "peakRSSBytes": int(match[1]) * 1024}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owned-adb", type=Path, required=True,
                        help="launcher scoped to the exact private ADB socket and emulator serial")
    parser.add_argument("--avd", required=True)
    parser.add_argument("--device-directory", required=True,
                        help="absolute device path containing matched, rusage, task.wasm and lib/")
    args = parser.parse_args()
    directory = args.device_directory
    require(re.fullmatch(r"/data/local/tmp/[A-Za-z0-9_.-]+", directory)
            and directory.rsplit("/", 1)[1] not in {".", ".."}, "invalid fixture device path")
    adb = args.owned_adb.resolve(strict=True)

    def command(*argv):
        return subprocess.run([adb, "shell", *argv], capture_output=True, timeout=8, check=True)

    properties = {}
    for key, expected in (("ro.boot.qemu.avd_name", args.avd),
                          ("ro.build.version.sdk", "36"), ("ro.product.cpu.abi", "arm64-v8a"),
                          ("ro.kernel.qemu", "1"), ("ro.build.fingerprint", None)):
        reply = command("getprop", key).stdout.decode().strip()
        require(reply and (expected is None or reply == expected), f"emulator identity differs at {key}")
        properties[key] = reply
    expected_frames = [frame["sha256"] for frame in json.loads(PRIOR.read_bytes())["frames"]]

    def sample(mode):
        result = command("env", f"LD_LIBRARY_PATH={directory}/lib", f"{directory}/rusage",
                         f"{directory}/matched", mode, f"{directory}/task.wasm")
        return read_sample(result.stdout, result.stderr, mode, expected_frames)

    before = command("cat", "/proc/loadavg").stdout.decode().strip()
    controls = {mode: sample(mode) for mode in ("native-control", "guest-control")}
    samples = {"native": [], "guest": []}
    order = []
    for pair in range(PAIRS):
        sequence = ("native", "guest") if pair % 2 == 0 else ("guest", "native")
        for mode in sequence:
            samples[mode].append(sample(mode))
        order.extend(sequence)
    after = command("cat", "/proc/loadavg").stdout.decode().strip()
    summary = {
        mode: {
            "threeTurnElapsedNS": spread([sum(row["turnNS"]) for row in rows]),
            "turnElapsedNS": spread([elapsed for row in rows for elapsed in row["turnNS"]]),
            "wholeProcessPeakRSSBytes": spread([row["peakRSSBytes"] for row in rows]),
        }
        for mode, rows in samples.items()
    }
    print(json.dumps({"emulator": properties, "expectedFrames": expected_frames, "order": order,
                      "controls": controls, "samples": samples, "summary": summary,
                      "loadAverageBefore": before, "loadAverageAfter": after}, indent=2))


if __name__ == "__main__":
    main()
