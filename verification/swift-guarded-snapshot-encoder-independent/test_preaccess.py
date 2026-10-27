"""Pre-access oracle sanity and adversarial controls; synthetic, not validation."""
import copy
import hashlib
import json
import unittest
from wire_oracle import (HEADER, MAX_IMAGE, CAPS, WORDS, RUN_CEILINGS, WASI_IDS,
                         NATIVE, Refused, expected_image, inspect_image,
                         compare_actual, put, words)


def synthetic(source_bytes=8193, wasi=None):
    """Distinctive bounded values; deliberately not a genuine Wasm/proof."""
    source = bytes((n * 73 + 19) % 256 for n in range(source_bytes))
    sections = [
        [(0, 4, 4), (4, 0, 0)],
        [(1,), (2,), (3,), (4,)],
        [(n, 2, n + 2, 3, n % 2) for n in range(34)],
        [(13, 5, 0), (21, 6, 1), (35, 7, 0)],
        [(n, n % 2, 46 + n, 1) for n in range(1, 5)],
        [(50 + n, 2, n, 10 + n) for n in range(4)],
        [(60, 3, 7, 3), (63, 2, 19, 2)],
        [(65, 2, 11, 2), (67, 3, 23, 3)],
    ]
    capacities = [4, 8, 64, 8, 8, 8, 4, 4]
    metadata = 664 + sum(cap * size for cap, size in zip(capacities, NATIVE[1:]))
    limits = (67_108_864, 16_777_216, 1_048_576, 512_000_000, 120_000)
    return {
        'source': source, 'sections': sections, 'capacities': capacities,
        'instructions': 11, 'validation_limits': limits,
        'usage': (source_bytes, source_bytes, metadata, 0, metadata + 48,
                  100, metadata + 148, 1234, 987, 120_000),
        'observations': (2, 4, 34, 3, 3, 11, 4, 4, 2, 2, 17, 13, 7,
                         2, 0, 0, 768, 4, 1, 16),
        'metadata': (1, 2, 768, 1, 4, 16, 0, 0, 1, 16, 7, 9, 11),
        'provenance_extent': source_bytes, 'provenance_limits': limits,
        'retained_values': [bytes((n + 31 * k) % 256 for n in range(32)) for k in range(6)],
        'identities': [(100 + k, 201 + k, source_bytes if k == 0 else 700 + k,
                        0o100600 + k, -1 - k, -11 - k, -101 - k, -1001 - k)
                       for k in range(4)],
        'runtime': {'owner': 17, 'limits': RUN_CEILINGS, 'wasi': wasi,
                    'scalars': (source_bytes, 2, 3, 64, 1, 121264, 16777216, 8388608)},
        # A deliberate non-ALL ordering must remain representable by the data
        # oracle. It does not assert this synthetic array passed the validator.
        'resolved': tuple(range(34, 0, -1)),
    }


class PreaccessControls(unittest.TestCase):
    checks = []

    def refused_mutation(self, label, offset, value):
        image = bytearray(expected_image(synthetic()))
        put(image, offset, (value,))
        with self.assertRaises(Refused, msg=label):
            inspect_image(image)
        self.checks.append(label)

    def test_complete_fields_and_provenance_identity(self):
        semantic = synthetic()
        image = expected_image(semantic)
        result = compare_actual(image, semantic)
        self.assertEqual(result['counts'], [8193, 2, 4, 34, 3, 4, 4, 2, 2])
        self.assertEqual(image[584:776], b''.join(semantic['retained_values']))
        for k in range(4):
            for j in range(4, 8):
                self.assertEqual(words(image, 776 + k * 64 + j * 8), semantic['identities'][k][j] % 2**64)
        self.assertEqual(result['resolved'], tuple(range(34, 0, -1)))
        self.assertEqual(len(WASI_IDS), 34)
        for offset in range(584, 776):
            changed = bytearray(image)
            changed[offset] ^= 1
            # Grammar acceptance is not provenance authority: every one of the
            # 192 retained bytes must still differ from independent expectation.
            inspect_image(changed)
            with self.assertRaises(Refused):
                compare_actual(changed, semantic)
            self.checks.append('retained-byte-' + str(offset))

    def test_wasi_absence_and_some_zero_distinct(self):
        none = expected_image(synthetic(wasi=None))
        zero = expected_image(synthetic(wasi=(0,) * 12))
        nonzero = expected_image(synthetic(wasi=(1, 2, 3, 4, 5, 6, 7, 1, 0, 1, 0, 1)))
        for image in (none, zero, nonzero):
            inspect_image(image)
        self.assertNotEqual(none, zero)
        self.assertEqual(none[:1112] + none[1120:], zero[:1112] + zero[1120:])
        self.checks.extend(['WASI-none', 'WASI-some-zero', 'WASI-some-nonzero'])

    def test_block_boundaries_and_all_nine_sections(self):
        for extent in (4095, 4096, 4097, 8191, 8192, 8193, 12287, 12288, 12289):
            semantic = synthetic()
            if extent < 8191:
                semantic['sections'] = [[(0, 0, 0)], [],
                    [(n, 2, n + 2, 3, 0) for n in range(34)],
                    [(13, 5, 0)], [], [], [], []]
                semantic['capacities'] = [2, 0, 64, 2, 0, 0, 0, 0]
                semantic['observations'] = (1, 0, 34, 1, 1, 11, 0, 0, 0, 0,
                                            17, 13, 7, 2, 0, 0, 768, 4, 1, 16)
                scalars = semantic['runtime']['scalars']
                semantic['runtime']['scalars'] = (8193, 1, 1) + scalars[3:]
                usage = semantic['usage']
                reserved = 664 + sum(cap * size for cap, size in zip(semantic['capacities'], NATIVE[1:]))
                semantic['usage'] = usage[:2] + (reserved,) + usage[3:]
            overhead = len(expected_image(semantic)) - 8193
            source_bytes = extent - overhead
            source = synthetic(source_bytes)['source']
            semantic['source'] = source
            semantic['provenance_extent'] = source_bytes
            semantic['usage'] = (source_bytes, source_bytes) + semantic['usage'][2:]
            identity = semantic['identities'][0]
            semantic['identities'][0] = identity[:2] + (source_bytes,) + identity[3:]
            semantic['runtime']['scalars'] = (source_bytes,) + semantic['runtime']['scalars'][1:]
            image = expected_image(semantic)
            result = inspect_image(image)
            self.assertEqual(len(image), extent)
            blocks = [image[n:n + 4096] for n in range(0, len(image), 4096)]
            self.assertEqual(b''.join(blocks), image)
            self.assertEqual(result['blocks'], len(blocks))
            self.assertTrue(all(len(block) == 4096 for block in blocks[:-1]))
            self.checks.append('complete-extent-' + str(extent))

    def test_duplicate_equations_and_scalar_restrictions(self):
        # Single-word changes exercise every E01-E29 family, including all
        # duplicate copies rather than just a representative source word.
        offsets = (64, 144, 152, 536, 792, 1360, 1616, 1632, 1656,
                   96, 104, 112, 120, 128, 544, 552, 560, 568, 576, 216,
                   72, 264, 480, 224, 232, 240, 248, 272, 280, 288, 296,
                   56, 256, 328, 392, 352, 400, 336, 344, 432, 440,
                   360, 416, 368, 376, 448, 456, 384, 408, 424,
                   1368, 1376, 1384, 1392, 1408, 1416, 160, 88)
        valid = expected_image(synthetic())
        for offset in offsets:
            self.refused_mutation('equation-at-' + str(offset), offset, words(valid, offset) + 1)
        self.refused_mutation('E29-base-over-capacity', 1400, 16_777_217)
        self.refused_mutation('E28-charge-overflow', 1680, 2**64 - 1)

    def test_reserved_enums_widths_limits_and_directory(self):
        for offset in (136, 488, 1032, 1424, 2448):
            self.refused_mutation('reserved-' + str(offset), offset, 1)
        for k in range(34):
            for bad in (0, 35):
                self.refused_mutation('resolved-' + str(k) + '-' + str(bad), 2176 + k * 8, bad)
        for section in range(9):
            start = 1600 + section * 64
            for relative, value in ((0, 99), (24, 99), (40, 3), (48, 2561), (56, 1)):
                self.refused_mutation('directory-' + str(section) + '-' + str(relative), start + relative, value)
        for offset, value in ((1112, 2), (1120, 0), (1128, 67_108_865),
                              (1208, 2**32), (1264, 1), (464, 2**32), (472, 2**32)):
            self.refused_mutation('runtime-width-presence-' + str(offset), offset, value)
        valid = bytearray(expected_image(synthetic(wasi=(0,) * 12)))
        for offset, value in ((1288, 2**32), (1296, 2**32), (1304, 2**32), (1320, 2)):
            image = bytearray(valid)
            put(image, offset, (value,))
            with self.assertRaises(Refused):
                inspect_image(image)
            self.checks.append('WASI-width-boolean-' + str(offset))
        for image in (bytes(valid[:-1]), bytes(valid) + b'\x00'):
            with self.assertRaises(Refused):
                inspect_image(image)
            self.checks.append('truncation-or-trailer-' + str(len(image)))

    def test_each_record_field_is_byte_compared(self):
        semantic = synthetic()
        original = expected_image(semantic)
        for section_index, records in enumerate(semantic['sections']):
            for row_index, row in enumerate(records):
                for field_index in range(len(row)):
                    changed = copy.deepcopy(semantic)
                    row2 = list(row)
                    row2[field_index] ^= 1
                    changed['sections'][section_index][row_index] = tuple(row2)
                    with self.assertRaises(Refused):
                        compare_actual(original, changed)
                    self.checks.append('record-field-%d-%d-%d' % (section_index + 1, row_index, field_index))

    def test_caps_and_non_equations(self):
        self.assertEqual(HEADER + CAPS[0] + sum(c * w * 8 for c, w in zip(CAPS[1:], WORDS[1:])), MAX_IMAGE)
        # Capacity deliberately exceeds count in every metadata section.
        semantic = synthetic()
        run = list(semantic['runtime']['limits'])
        run[10] = 64
        semantic['runtime']['limits'] = tuple(run)
        image = expected_image(semantic)
        inspect_image(image)
        self.assertNotEqual(words(image, 128), words(image, 1256))
        self.assertNotEqual(words(image, 400), words(image, 1208))
        self.assertNotEqual(words(image, 1376), words(image, 1160))
        self.assertNotEqual(words(image, 1400), words(image, 1408))
        self.checks.extend(['envelope-cap-equation', 'capacity-exceeds-count', 'non-equations'])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PreaccessControls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'scope': 'independently authored synthetic pre-access oracle only',
                      'methods': result.testsRun, 'controls': len(PreaccessControls.checks),
                      'control_ids_sha256': hashlib.sha256('\n'.join(PreaccessControls.checks).encode()).hexdigest(),
                      'successful': result.wasSuccessful(),
                      'candidate_accessed': False, 'compiler_run': False}, sort_keys=True))
    raise SystemExit(not result.wasSuccessful())
