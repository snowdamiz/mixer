"""Pin selection/preflight tests; successful full runs hash the actual artifacts."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run


class InputTests(unittest.TestCase):
    def test_default_preserves_original_command_artifact_and_map(self):
        selected = run.select_input()
        self.assertEqual(selected['artifact'], run.ARTIFACT.resolve())
        self.assertEqual(selected['sha256'], run.ARTIFACT_HASH)
        self.assertEqual(selected['bytes'], 52_008_982)
        self.assertEqual(selected['link_map'], run.LINK_MAP.resolve())
        self.assertEqual(selected['link_map_sha256'], run.LINK_MAP_HASH)

    def test_reactor_pin_is_explicit_and_bad_sha_or_unknown_input_reject(self):
        selected = run.select_input('reactor')
        self.assertEqual(selected['bytes'], 53_777_114)
        self.assertEqual(selected['functions'], 79_832)
        self.assertEqual(run.select_input('reactor', supplied_sha256=selected['sha256']), selected)
        for kind, value in [('reactor', run.ARTIFACT_HASH), ('command', '0' * 64), ('command', 'invalid')]:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                run.select_input(kind, supplied_sha256=value)
        with self.assertRaises(ValueError):
            run.select_input('arbitrary')

    def test_missing_directory_wrong_length_and_wrong_content_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            selected = run.select_input('reactor', parent / 'missing')
            for path in [parent / 'missing', parent]:
                selected['artifact'] = path
                with self.subTest(path=path), self.assertRaises(ValueError):
                    run.validate_input(selected)
            artifact, link_map = parent / 'artifact', parent / 'map'
            artifact.write_bytes(b'x')
            link_map.write_bytes(b'map')
            selected.update(artifact=artifact, link_map=link_map)
            with self.assertRaises(ValueError):
                run.validate_input(selected)
            with artifact.open('wb') as file:
                file.truncate(selected['bytes'])
            with patch.object(run.helper, 'digest', return_value='0' * 64), self.assertRaises(ValueError):
                run.validate_input(selected)

    def test_relocated_selected_bytes_preserve_pin_and_map_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact, link_map = (Path(directory) / 'artifact').resolve(), (Path(directory) / 'map').resolve()
            artifact.touch(); link_map.write_bytes(b'map')
            selected = run.select_input('command', artifact)
            selected['link_map'] = link_map
            with artifact.open('wb') as file:
                file.truncate(selected['bytes'])
            def exact(path):
                return selected['sha256'] if path == artifact else selected['link_map_sha256']
            with patch.object(run.helper, 'digest', side_effect=exact):
                run.validate_input(selected)
            with patch.object(run.helper, 'digest', return_value=selected['sha256']), self.assertRaises(ValueError):
                run.validate_input(selected)

    def test_complete_reactor_coverage_requires_every_pinned_total(self):
        selected = run.select_input('reactor')
        observed = {'source_bytes': selected['bytes'], 'functions': selected['functions']}
        stats = {'function_count': selected['functions'], 'raw_instruction_count': selected['instructions'], 'wire_body_bytes': selected['body_bytes']}
        run.validate_complete_inventory(selected, observed, stats)
        for target, key in [(observed, 'source_bytes'), (observed, 'functions'), (stats, 'function_count'), (stats, 'raw_instruction_count'), (stats, 'wire_body_bytes')]:
            previous = target[key]
            target[key] -= 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                run.validate_complete_inventory(selected, observed, stats)
            target[key] = previous


if __name__ == '__main__':
    unittest.main()
