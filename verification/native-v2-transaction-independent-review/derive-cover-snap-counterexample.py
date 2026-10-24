#!/usr/bin/env python3
"""Independent Fraction model of the pre-correction row/cover geometry; no UIKit."""
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import platform
import sys

BASE = Path(__file__).resolve().parent
OUT = BASE / 'cover-snap-counterexample-1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def edge(value):
    # UIAppearanceGeometryV2.pixelEdge at density1024: nearest, ties up.
    assert value >= 0
    return F((2 * value.numerator + value.denominator) // (2 * value.denominator))


def main():
    manifest = json.loads((OUT / 'source-manifest.json').read_text())
    for name, expected in manifest.items():
        assert sha(OUT / 'inputs' / name) == expected
    top, floor, inset = F(3053, 64), F(3347, 64), F(16)
    field_semantic, hit, padding = F(1773, 64), F(44), F(12)
    first_height, toggle_height, field_height = floor, floor, field_semantic + inset * 2
    toggle_origin = top + first_height
    field_origin = toggle_origin + toggle_height
    cover_min = toggle_origin + (toggle_height - hit) / 2 - padding
    cover_max = toggle_origin + (toggle_height + hit) / 2 + padding
    field_hit_min = field_origin + (field_height - hit) / 2
    field_content_min = field_origin + inset
    assert toggle_origin == 100
    assert cover_max == field_hit_min
    assert cover_max < field_content_min
    # Corners can be interior to a zero-radius opaque group, and x insets16
    # leave the12pt expansion interior. Empty label/preceding row add no ink.
    assert cover_min > top
    assert cover_max < top + first_height + toggle_height + field_height
    assert inset > padding
    actual_cover_max = edge(toggle_origin) + (toggle_height + hit) / 2 + padding
    actual_field_hit_min = edge(field_origin) + (field_height - hit) / 2
    overlap = actual_cover_max - actual_field_hit_min
    assert overlap == F(19, 64) > 0
    result = {
        'status': 'derived-pre-correction-final-placement-overlap-reproduced',
        'command': [sys.executable, str(Path(__file__).resolve())],
        'pythonVersion': platform.python_version(),
        'scriptSHA256': sha(Path(__file__)),
        'sourceSHA256': manifest,
        'fixtureMetrics64': {'density1024': 1024, 'topPadding64': 3053,
                             'rowFloor64': 3347, 'contentInsets64': 1024,
                             'fieldMinimumContentHeight64': 1773, 'fieldInsets64': 0,
                             'minimumHitHeight64': 2816},
        'rows': ['empty transparent container', 'empty-label toggle', 'empty-label/value field'],
        'rowHeightsPoints': list(map(float, [first_height, toggle_height, field_height])),
        'logicalCoverEnd': float(cover_max), 'logicalNeighborHitStart': float(field_hit_min),
        'logicalNeighborContentStart': float(field_content_min),
        'snappedNeighborRowOrigin': float(edge(field_origin)),
        'actualCoverEnd': float(actual_cover_max), 'actualNeighborHitStart': float(actual_field_hit_min),
        'overlapPoints': float(overlap), 'overlapExact': str(overlap),
        'scope': 'Independent host arithmetic derivation of captured source coordinate mismatch only. No packet/native fixture executed; no UIKit geometry, native hit, paint, glass extent, GUI, runtime, simulator or device qualification.',
    }
    path = OUT / 'derivation.json'
    assert not path.exists()
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': result['status'], 'overlapPoints': float(overlap), 'receipt': str(path)}))


if __name__ == '__main__':
    main()
