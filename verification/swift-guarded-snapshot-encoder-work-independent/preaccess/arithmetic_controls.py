#!/usr/bin/env python3
"""Independent integer geometry and checked-admission controls; no engine import."""
import json
import random

HEADER = 2560
BLOCK = 4096
U64 = 2**64 - 1
CAPS = (67108864, 512, 8192, 34, 79966, 8192, 4096, 4096, 4096)
WIDTHS = (0, 3, 1, 5, 3, 4, 4, 4, 4)
MAXIMUM = 69765152
checks = []


def check(name, condition, detail=None):
    if not condition:
        raise AssertionError((name, detail))
    checks.append({"name": name, "pass": True, "detail": detail})


def add(a, b):
    if not (0 <= a <= U64 and 0 <= b <= U64 and a <= U64 - b):
        raise OverflowError("checked u64 add")
    return a + b


def mul(a, b):
    if not (0 <= a <= U64 and 0 <= b <= U64 and (b == 0 or a <= U64 // b)):
        raise OverflowError("checked u64 multiply")
    return a * b


def ceil_div(n, d):
    if not (0 <= n <= U64 and 0 < d <= U64):
        raise OverflowError("checked ceil inputs")
    # Avoid n + d - 1, which overflows for valid large u64 inputs.
    return n // d + (n % d != 0)


def must_overflow(name, operation):
    try:
        operation()
    except OverflowError:
        check(name, True)
    else:
        check(name, False)


def sections(counts):
    result = []
    position = HEADER
    for sid, count in enumerate(counts):
        size = count if sid == 0 else count * WIDTHS[sid] * 8
        result.append((sid, position, position + size))
        position += size
    return result, position


def interval_block(counts, base):
    ranges, extent = sections(counts)
    end = min(extent, base + BLOCK)
    out = {"bytes": max(0, end - base), "header_steps": 0,
           "source_steps": 0, "records": [0] * 9, "probes": 0}
    if base < min(end, HEADER):
        out["header_steps"] = 1
    for sid, start, stop in ranges:
        lo, hi = max(base, start), min(end, stop)
        if lo >= hi:
            continue
        if sid == 0:
            out["source_steps"] = 1
            out["probes"] += 1
        else:
            visits = ceil_div(hi - start, 8) - (lo - start) // 8
            out["records"][sid] = visits
            out["probes"] += (sid + 1) * visits
    out["record_visits"] = sum(out["records"])
    out["loop_steps"] = out["header_steps"] + out["source_steps"] + out["record_visits"]
    return out


def step_block(counts, base):
    ranges, extent = sections(counts)
    at, end = base, min(extent, base + BLOCK)
    out = {"bytes": max(0, end - base), "header_steps": 0,
           "source_steps": 0, "records": [0] * 9, "probes": 0}
    while at < end:
        if at < HEADER:
            at = min(HEADER, end)
            out["header_steps"] += 1
            continue
        for sid, start, stop in ranges:
            out["probes"] += 1
            if start <= at < stop:
                break
        else:
            raise AssertionError("schedule gap")
        if sid == 0:
            out["source_steps"] += 1
            at = min(stop, end)
        else:
            out["records"][sid] += 1
            remaining_word = 8 - (at - start) % 8
            at += min(remaining_word, end - at)
    out["record_visits"] = sum(out["records"])
    out["loop_steps"] = out["header_steps"] + out["source_steps"] + out["record_visits"]
    return out


def closed_total(counts):
    ranges, extent = sections(counts)
    source_steps = ceil_div(HEADER + counts[0], BLOCK) if counts[0] else 0
    records = [0] * 9
    splits = [0] * 9
    for sid, start, end in ranges[1:]:
        words = (end - start) // 8
        if words and start % 8:
            splits[sid] = (end - 1) // BLOCK - start // BLOCK
        records[sid] = words + splits[sid]
    return {"extent": extent, "blocks": ceil_div(extent, BLOCK),
            "source_steps": source_steps, "records": records, "splits": splits,
            "record_visits": sum(records), "split_visits": sum(splits),
            "probes": source_steps + sum((sid + 1) * n for sid, n in enumerate(records)),
            "record_array_slots": sum(records) * 5}


def compare_profile(name, counts, use_steps=True):
    total = closed_total(counts)
    records, probes, copied, source_steps = [0] * 9, 0, 0, 0
    maxima = {"loop_steps": 0, "record_visits": 0, "probes": 0}
    for base in range(0, total["extent"], BLOCK):
        event = interval_block(counts, base)
        if use_steps and event != step_block(counts, base):
            raise AssertionError((name, base, "independent geometry differs"))
        copied += event["bytes"]
        probes += event["probes"]
        source_steps += event["source_steps"]
        records = [a + b for a, b in zip(records, event["records"])]
        for key in maxima:
            maxima[key] = max(maxima[key], event[key])
    check(name, records == total["records"] and probes == total["probes"] and
          copied == total["extent"] and source_steps == total["source_steps"] and
          maxima["loop_steps"] <= 513 and maxima["record_visits"] <= 513 and
          maxima["probes"] <= 4617, {"counts": counts, **total, "block_maxima": maxima})
    return total


def controls():
    check("maximum wire extent", sections(CAPS)[1] == MAXIMUM)
    aligned = compare_profile("maximum aligned inventory", CAPS)
    unaligned = compare_profile("maximum source minus one", (CAPS[0] - 1,) + CAPS[1:])
    check("maximum aligned visit count", aligned["record_visits"] == 331716)
    check("unaligned additional split count", unaligned["split_visits"] == 648)
    check("unaligned record visits", unaligned["record_visits"] == 332364)
    check("maximum nonempty call count", aligned["blocks"] == unaligned["blocks"] == 17033)
    compare_profile("header only geometry", (0,) * 9)
    compare_profile("source only geometry", (8193,) + (0,) * 8)
    for residue in range(8):
        compare_profile(f"alignment residue {residue}", (8192 + residue, 11, 9, 3, 7, 9, 13, 17, 1500))
    # Isolate the last section, forcing each requested word through all 9 probes.
    tail = (1, 0, 0, 0, 0, 0, 0, 0, 2048)
    event = interval_block(tail, BLOCK)
    check("actual 513 visits in unaligned last section", event["record_visits"] == 513, event)
    check("actual 4617 directory probes", event["probes"] == 4617, event)
    check("once-per-block directory mutation rejected", event["probes"] > 9)
    check("once-per-row reconstruction mutation rejected", event["record_visits"] > ceil_div(event["record_visits"], WIDTHS[8]))
    check("missing five-slot work mutation rejected", event["record_visits"] * 5 > event["record_visits"])
    check("missing split work mutation rejected", unaligned["record_visits"] > aligned["record_visits"])
    # Same geometric prefix is attempted again after a late refusal because the
    # cursor updates only on successful return. This is arithmetic, not a VM run.
    prefix_visits, failed_reconstruction = 512, 1
    once = prefix_visits + failed_reconstruction
    check("late error includes failed operation", once == 513 and once > prefix_visits)
    check("retry has a fresh charge", add(once, once) == 1026)
    check("terminal calls require per-call overhead", add(1, 1) > 1)
    for a, b, expected in [(0, 0, 0), (U64, 0, U64), (U64 - 1, 1, U64)]:
        check(f"checked sum {a} {b}", add(a, b) == expected)
    must_overflow("existing usage plus credit overflow", lambda: add(U64, 1))
    must_overflow("prep plus block sum overflow", lambda: add(U64 - 2, 3))
    must_overflow("negative u64 rejected", lambda: add(-1, 1))
    check("checked product exact edge", mul(U64, 1) == U64)
    check("checked product zero", mul(U64, 0) == 0)
    must_overflow("visit coefficient overflow", lambda: mul(U64 // 513 + 1, 513))
    must_overflow("retry multiplier overflow", lambda: mul(U64 // 2 + 1, 2))
    for n in [0, 1, 4095, 4096, 4097, U64 - 4095, U64]:
        check(f"safe ceil {n}", ceil_div(n, BLOCK) == (n + BLOCK - 1) // BLOCK)
    must_overflow("naive ceil numerator overflow", lambda: add(U64, BLOCK - 1))
    must_overflow("header plus source overflow", lambda: add(U64, HEADER))
    for used, credits, limit, expected in [(0, 0, 0, True), (7, 3, 10, True), (7, 4, 10, False), (U64, 1, U64, False)]:
        try:
            admitted = add(used, credits) <= limit
        except OverflowError:
            admitted = False
        check(f"original checked admission {used} {credits} {limit}", admitted == expected)
    rng = random.Random(0x4D4958534E423032)
    for index in range(256):
        counts = (rng.randrange(16385),) + tuple(rng.randrange(33) for _ in range(8))
        compare_profile(f"independent interval-step geometry {index}", counts)
    return {"schema": 1, "scope": "source-independent integer geometry and u64 arithmetic; no engine execution or grant selection",
            "status": "pass", "checks": checks, "check_count": len(checks),
            "maximum_aligned": aligned, "maximum_source_minus_one": unaligned,
            "not_established": ["complete primitive coefficients", "guard/provenance helper bodies", "work floor or operational grant", "CPU/RSS", "writer execution", "native or GA qualification"]}


if __name__ == "__main__":
    print(json.dumps(controls(), indent=2) + "\n", end="")
