#!/usr/bin/env python3
"""Read exact archived/retained baselines; no historical producer execution."""
import datetime
import difflib
import io
import json
from pathlib import Path
import sys
import tarfile

import run_review as r


def source_payload(path, expected):
    r.require(r.row(path)['sha256'] == expected, 'Source archive differs')
    payload, seen = {}, set()
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive.getmembers():
            name = Path(member.name)
            r.require(not name.is_absolute() and '..' not in name.parts and member.name not in seen,
                      'Unsafe or duplicate source archive member')
            seen.add(member.name)
            if member.isdir():
                continue
            r.require(member.isfile() and member.name.startswith('accepted/'), 'Nonregular source member')
            payload[member.name] = archive.extractfile(member).read()
    return payload


def main():
    original_archive = r.ROOT / 'verification/apple-focus-reference-diagnostic-v1/accepted-sources.tar.gz'
    template_build = r.ROOT / 'verification/apple-toggle-keyboard-focus-diagnostic-v1-build'
    fresh = r.BUILD / 'attempt-1'
    v5_run = r.PRIOR / 'native-run-v5-e7108fc8-281b-4c59-831a-f3697609017d'
    original_sources = source_payload(original_archive, 'c1e59b3e950acfe4afa46ae69e8eed29e6c8e1816e1d845e1c40548833201294')
    template_sources = source_payload(template_build / 'accepted-sources.tar.gz',
                                      '5b7f6b663e71b0ce56bb016bb0c42e5e30b622d20469e0a47b89cab352625e32')
    fresh_sources = source_payload(fresh / 'accepted-sources.tar.gz',
                                   '82b88c3ee0d55b3cf10930904f0f2eaed6d44b368659c9b2665f58cd28e764a9')
    changed = sorted(n for n in fresh_sources if fresh_sources[n] != original_sources.get(n))
    r.require(changed == ['accepted/harness/MixerToggleUITests.xcodeproj/project.pbxproj',
                         'accepted/harness/UITests/SettingsFailureDiagnostic.swift',
                         'accepted/harness/UITests/ToggleUITests.swift'], 'Original-to-fresh source delta differs')
    original_app = {n: data for n, data in original_sources.items() if '/harness/' not in n}
    r.require(original_app and all(fresh_sources[n] == data for n, data in original_app.items()),
              'Original application/library source changed')
    products = json.loads((fresh / 'product-manifest.json').read_bytes())
    template = json.loads((r.PRIOR / 'selection-template.json').read_bytes())
    app_rows = {n: v for n, v in products['products'].items() if n.startswith('MixerToggleDiagnostics.app/')}
    r.require(len(app_rows) == 13, 'Expected 13 application product files')
    actual = {n: r.row(v5_run / 'runtime/restored-app/diagnostic' / n) for n in app_rows}
    r.require(actual == app_rows, 'Actual retained V5 application differs from fresh V6')
    old_manifest = r.ROOT / 'verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/product-manifest.json'
    old_archive = old_manifest.with_name('products.tar.gz')
    r.require(r.row(old_manifest)['sha256'] == '2791292716192ebfa074854007a1867f3477c45fcfb86365c0f5ea1ab91ddb9a',
              'Original product manifest differs')
    original_manifest = json.loads(old_manifest.read_bytes())
    r.archive(old_archive, original_manifest['products'],
              '0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8')
    r.require(all(original_manifest['products'][n] == v for n, v in app_rows.items()),
              'Original V1 application differs from fresh V6')
    root = json.loads((v5_run / 'root-selection.json').read_bytes())
    r.require(root['productArchiveSHA256'] == r.row(old_archive)['sha256'], 'V5 root product selection differs')
    old_prepare = r.PRIOR / 'prepare.py'
    packet = json.loads((r.PRIOR / 'packet.json').read_bytes())
    r.require(r.row(old_prepare) == packet['files']['prepare.py'], 'Accepted V5 dispatcher source differs')
    text = old_prepare.read_text()
    required = ["PRODUCT = '0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8'",
                "h=helpers(); product_manifest=json.loads((V1/'compile-attempt-1/product-manifest.json').read_bytes())",
                "product_payload=h.archive_payload(V1/'compile-attempt-1/products.tar.gz',product_manifest['products'],PRODUCT)",
                "productArchive=str(V1/'compile-attempt-1/products.tar.gz'),productManifest=product_manifest"]
    r.require(all(value in text for value in required), 'V5 dispatch override does not match evidence')
    differences = {n: {'staleTemplate': template['productManifest']['products'][n], 'actualV5AndFreshV6': v}
                   for n, v in app_rows.items() if template['productManifest']['products'][n] != v}
    template_delta = sorted(n for n in fresh_sources if fresh_sources[n] != template_sources.get(n))
    app_source_delta = {n: {'templateSHA256': r.sha(template_sources[n]), 'actualOriginalAndFreshSHA256': r.sha(data),
                          'diff': ''.join(difflib.unified_diff(template_sources[n].decode().splitlines(True),
                                      data.decode().splitlines(True), fromfile='stale-template/' + n,
                                      tofile='actual-original-and-fresh/' + n))}
                        for n, data in original_app.items() if template_sources.get(n) != data}
    paths = [original_archive, template_build / 'accepted-sources.tar.gz', fresh / 'accepted-sources.tar.gz',
             old_archive, old_manifest, old_prepare, v5_run / 'root-selection.json',
             r.PRIOR / 'selection-template.json', fresh / 'product-manifest.json']
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'argv': [sys.executable, '-B', str(Path(__file__).resolve())], 'python': sys.version,
               'script': r.row(Path(__file__).resolve()), 'supportScript': r.row(r.BASE / 'run_review.py'),
               'inputBindings': {str(p.relative_to(r.ROOT)): r.row(p) for p in paths},
               'actualV5RunID': root['runID'], 'actualV5ProductArchiveSHA256': root['productArchiveSHA256'],
               'actualV5RetainedApplication': {str((v5_run / 'runtime/restored-app/diagnostic' / n).relative_to(r.ROOT)): v
                                              for n, v in actual.items()},
               'actualV5AndFreshV6All13ApplicationRowsMatch': True,
               'originalV1AndFreshV6All13ApplicationRowsMatch': True,
               'applicationAndLibrarySourceFilesUnchangedFromOriginalV1': len(original_app),
               'originalV1ToFreshV6ChangedSources': changed,
               'staleTemplateToFreshV6ChangedSources': template_delta,
               'staleTemplateApplicationSourceDifferences': app_source_delta,
               'staleTemplateProductArchiveSHA256': template['productManifest']['archive']['sha256'],
               'staleTemplateNineApplicationProductDifferences': differences,
               'conclusion': 'Fresh V6 preserves the actual dispatched V5 application byte-for-byte. The toggle/referenceButton difference belongs to the stale template build; V5 dispatch overrides it with original V1 products. No app-baseline change between actual V5 and fresh V6.',
               'nativeCommandsExecuted': 0, 'nativeInstancesQueried': 0, 'hostScratchCreated': False,
               'historicalProducerImportedOrExecuted': False, 'excludedFrozenLanesRead': False,
               'gaAccepted': False}
    (r.BASE / 'baseline-reconciliation.json').write_bytes(r.stable(receipt))
    print(json.dumps({'all13ActualV5ApplicationRowsMatchFreshV6': True,
                      'unchangedApplicationAndLibrarySourceFiles': len(original_app),
                      'staleTemplateProductDifferences': len(differences), 'nativeExecuted': False}))


if __name__ == '__main__':
    main()
