import unittest
from analyze import Reader, wasm, link_map, object_data, initialized_contribution


def leb(value):
    output = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        output.append(byte | (128 if value else 0))
        if not value:
            return output


def section(identifier, data):
    return bytes([identifier]) + leb(len(data)) + data


class MeasurementTests(unittest.TestCase):
    def test_original_table_memory_data_body_measurement(self):
        data = b'\0asm\x01\0\0\0' + section(3, b'\x01\x00')
        data += section(4, b'\x01\x70\x01\x02\x02') + section(5, b'\x01\x01\x01\x01')
        data += section(9, b'\x01\x00\x41\x01\x0b\x01\x00')
        data += section(10, b'\x01\x02\x00\x0b')
        data += section(11, b'\x01\x00\x41\x00\x0b\x03abc')
        value = wasm(data)
        self.assertEqual(value['active_data_bytes'], 3)
        self.assertEqual(value['function_body_bytes'], 2)
        self.assertEqual(value['initial_linear_memory_bytes'], 65536)
        self.assertEqual(data[value['data'][0]['file_offset']:][:3], b'abc')
        self.assertEqual(value['elements'][0]['entries'], 1)
        self.assertFalse(value['authorization'])
        for end in range(len(data)):
            try:
                wasm(data[:end])  # A prefix ending on a section boundary can itself be valid.
            except (ValueError, UnicodeDecodeError):
                pass

    def test_bounded_leb_and_lengths(self):
        for value in [b'', b'\x80', b'\xff\xff\xff\xff\x10', b'\x80' * 6]:
            with self.assertRaises(ValueError):
                Reader(value).uint()
        with self.assertRaises(ValueError):
            Reader(leb(1_000_001)).count()
        with self.assertRaises(ValueError):
            wasm(b'\0asm\x01\0\0\0\x0a\x7f')

    def test_unknown_sections_modes_and_names_are_not_guessed(self):
        for data in [section(12, b'\x00'), section(9, b'\x01\x01'),
                     section(4, b'\x01\x6f\x00\x01'), section(0, b'\x01\xff')]:
            with self.assertRaises((ValueError, UnicodeDecodeError)):
                wasm(b'\0asm\x01\0\0\0' + data)

    def test_duplicate_or_out_of_order_sections_reject(self):
        for data in [section(3, b'\0') + section(3, b'\0'), section(3, b'\0') + section(1, b'\0')]:
            with self.assertRaises(ValueError):
                wasm(b'\0asm\x01\0\0\0' + data)

    def test_link_map_counts_input_once_and_separates_zero_fill(self):
        value = link_map('''       -        8       40 CODE
       -        b       20         /sdk/libOwned.a(a.o):(work)
       -        b       20                 work
       -       48       20 DATA
    1000       4b       10 .rodata
    1000       4b       10         /sdk/libOwned.a(b.o):(.rodata.bytes)
    1010        0       10 .bss
    1010        0       10         /sdk/libOwned.a(c.o):(.bss.zero)
''')
        self.assertEqual(value['input_rows'], 3)
        self.assertEqual(value['archives_and_objects'][0]['code'], 32)
        self.assertEqual(value['archives_and_objects'][0]['initialized_data'], 16)
        self.assertEqual(value['archives_and_objects'][0]['zero_fill'], 16)
        with self.assertRaises(ValueError):
            link_map('unrecognized format')

    def test_relocatable_object_data_count_and_payload(self):
        prefix = b'\0asm\x01\0\0\0'
        data = prefix + section(12, b'\x01') + section(11, b'\x01\x00\x41\x00\x0b\x03abc')
        measured = object_data(data)
        self.assertEqual(measured[0]['bytes'], 3)
        self.assertEqual(data[measured[0]['file_offset']:][:3], b'abc')
        for value in [prefix, prefix + section(12, b'\0') + data[len(prefix) + 3:],
                      prefix + section(12, b'\x01') + section(12, b'\x01'), data[:-1]]:
            with self.assertRaises(ValueError):
                object_data(value)

    def test_attribution_uses_actual_segment_address_not_map_file_offset(self):
        data = b'\0asm\x01\0\0\0' + section(11, b'\x01\x00\x41\x05\x0b\x03abc')
        measured = wasm(data)
        payload, offset = initialized_contribution(data, measured,
            {'address': 5, 'bytes': 3, 'link_map_file_offset': 0})
        self.assertEqual(payload, b'abc')
        self.assertEqual(data[offset:], b'abc')
        with self.assertRaises(ValueError):
            initialized_contribution(data, measured, {'address': 5, 'bytes': 4})


if __name__ == '__main__':
    unittest.main()
