"""Adapt only accepted owned-server infrastructure; no producer tests execute."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = (root / 'verification/hosted-browser-relation-catalog/run.py').read_text()
source = source.replace("'verification/hosted-browser-relation-catalog/effects.exs',", "")
source = source.replace('verification/hosted-browser-relation-catalog/run.py', 'verification/hosted-browser-relation-catalog-review/run.py')
source = source.replace('verification/hosted-browser-relation-catalog/live.exs', 'verification/hosted-browser-relation-catalog-review/live.exs')
source = source.replace('mixer-relation-catalog-pg', 'mixer-relation-catalog-review-pg')
source = source.replace('Standalone RelationCatalog actual runtime prerequisite only;', 'Independent RelationCatalog selected controls;')
source = source.replace("  run('roles',admin,", "  run('actual-server-version',admin,data=\"SELECT version(),current_setting('server_version_num'),current_setting('server_encoding');\")\n  run('roles',admin,")
(Path(__file__).resolve().parent / 'run.py').write_text(source)
