#!/usr/bin/env python3
"""Write independent contract vectors without reading or executing implementation."""
import json
import pathlib

BASE = pathlib.Path(__file__).resolve().parent


def main():
    vectors = []
    def add(identifier, family, setup, expect, layer, **extra):
        vectors.append({'id': identifier, 'family': family, 'setup': setup,
                        'expected': expect, 'verification_layer': layer,
                        'execution_status': 'pending-frozen-handoff', **extra})
    add('G01', 'generation', 'Fresh actual CLI-created Android project from frozen SDK and adapter.',
        'Exact real CLI-linked canonical default is written before adapter digest; fourteen Java sources remain exact.', 'fresh-cli-and-codec')
    add('G02', 'generation', 'Create-only copied SDK source has required default API absent; Package.swift and source snapshot still exist.',
        'CLI-owned default asset is unchanged; create does not secretly compile copied SDK. Copied SDK compatibility stays unqualified.', 'fresh-cli-create-only')
    add('G03', 'generation', 'Existing destination contains an owned sentinel.',
        'Refuse overwrite, preserve sentinel and retire only owned creation scratch.', 'fresh-cli-create-only')
    add('G04', 'generation', 'Inspect frozen exact source change set and fresh CLI behavior.',
        'One existing CLI-linked canonical API producer; no copied table/fixture/theme or new emitter/watchdog/dependency; V1/native/schema scope intact.', 'source-and-fresh-cli')
    add('G05', 'generation', 'Fresh actual CLI iOS-only creation.',
        'Existing iOS-only behavior remains; no Android asset/helper compatibility policy is introduced.', 'fresh-cli-create-only')
    invalid_assets = [
        ('A01', 'Remove app/assets entirely.'),
        ('A02', 'Leave an empty app/assets directory.'),
        ('A03', 'Remove descriptor.json only.'),
        ('A04', 'Rename descriptor.json to descriptor-renamed.json.'),
        ('A05', 'Use zero bytes for descriptor.json.'),
        ('A06', 'Use 65,537 bytes for descriptor.json.'),
        ('A07', 'Use a very large sparse descriptor regular file; inspect size without reading its content.'),
        ('A08', 'Replace descriptor.json with a directory.'),
        ('A09', 'Replace descriptor.json with a symlink to an owned outside sentinel.'),
        ('A10', 'Replace descriptor.json with a dangling symlink.'),
        ('A11', 'Redirect app/assets through an owned directory symlink.'),
        ('A12', 'Redirect app/assets/MixerAppearanceV2 through an owned directory symlink.'),
        ('A13', 'Redirect the adapter app path component through an owned directory symlink.'),
        ('A14', 'Replace descriptor.json with an owned FIFO; no writer exists.'),
        ('A15', 'Add a second ordinary asset file.'),
        ('A16', 'Add hidden asset .hidden.'),
        ('A17', 'Add source-digest-skipped .DS_Store asset.'),
        ('A18', 'Add source-digest-skipped .env and .env.local assets.'),
        ('A19', 'Add source-digest-skipped credential-extension asset such as extra.pem.'),
        ('A20', 'Add a .build directory containing a masked extra file.'),
        ('A21', 'Add an unexpected empty directory.'),
        ('A22', 'Add an unknown FIFO beneath the asset tree.'),
        ('A23', 'Add an owned Unix-domain socket path beneath the asset tree; no network listener.'),
    ]
    for identifier, setup in invalid_assets:
        add(identifier, 'asset-preflight', setup,
            'Reject within deadline before asset hashing can open special/oversized input, before any tool sentinel and before output mutation.',
            'independent-driver-or-pure-preflight', original_lock=True,
            recomputed_lock='Repeat layout/type/size cases when safely hashable; never open FIFO/socket to form a lock.')
    add('A24', 'asset-preflight', 'One-byte ordinary descriptor with exact supported path inventory.',
        'Layout/type/size admission accepts boundary; no claim of canonical/default semantics or successful build.', 'pure-preflight-only')
    add('A25', 'asset-preflight', '65,536-byte ordinary descriptor with exact supported path inventory.',
        'Layout/type/size admission accepts boundary; no claim of canonical/default semantics or successful build.', 'pure-preflight-only')
    add('A26', 'asset-preflight', 'Layout-valid malformed/noncanonical descriptor and intentionally recomputed unauthenticated local lock.',
        'Record that Python path/type/size admission does not establish codec semantics; do not claim semantic acceptance.', 'pure-preflight-only')
    for identifier, setup in [
        ('L01', 'Edit original descriptor without updating local lock.'),
        ('L02', 'Edit AuthoredToggleInputV2.java while asset layout stays valid.'),
        ('L03', 'Remove or rename AuthoredToggleInputV2.java while asset layout stays valid.'),
        ('L04', 'Edit copied SDK source while asset layout stays valid.'),
    ]:
        add(identifier, 'source-lock', setup,
            'Existing SDK/adapter lock admission rejects before output/tool work; valid new asset does not mask old drift checks.',
            'independent-driver-and-cli-lock')
    add('R01', 'app-resources', 'Add ordinary app-owned Resources/extra.txt.',
        'CLI and direct driver retain explicit unsupported-resource refusal before build tools.', 'cli-and-direct-driver')
    add('R02', 'app-resources', 'Add hidden app Resources/.hidden and excluded-extension Resources/extra.pem.',
        'No app resource is silently omitted; direct driver rejects. Record actual CLI path scope rather than claiming its general digest sees excluded names.', 'direct-driver-and-cli-observation')
    zip_cases = [
        ('Z01', 'Final aligned APK has exactly one expected descriptor asset with exact admitted bytes and no other assets.', 'Accept the narrow inventory/byte-identity predicate.'),
        ('Z02', 'Final APK omits descriptor asset.', 'Reject missing asset.'),
        ('Z03', 'Final APK renames descriptor asset.', 'Reject wrong asset path.'),
        ('Z04', 'Final APK contains duplicate expected descriptor names with equal bytes.', 'Reject duplicate ZIP name before dictionary conversion.'),
        ('Z05', 'Final APK contains duplicate expected descriptor names with unequal bytes.', 'Reject ambiguous ZIP entries, regardless of which archive.read result wins.'),
        ('Z06', 'Final APK contains one descriptor plus assets/extra.bin.', 'Reject complete asset inventory mismatch.'),
        ('Z07', 'Final APK contains one descriptor plus an assets/extra/ directory member.', 'Reject additional asset entry.'),
        ('Z08', 'Final APK descriptor has different bytes but equal length.', 'Reject exact byte identity mismatch.'),
        ('Z09', 'Final APK descriptor is truncated or extended.', 'Reject length and byte mismatch.'),
        ('Z10', 'Final APK has duplicate nonasset member names.', 'Reject duplicate ZIP names before content hashing.'),
    ]
    for identifier, setup, expect in zip_cases:
        add(identifier, 'final-zip', setup, expect, 'independent-zip-or-pure-final-inspector')
    add('S01', 'staging-containment', 'Minimal valid-asset fixture replaces old empty adapter fixture; all accepted staging assertions remain.',
        'Preserve outside sentinels and staging parent/output/deep/file symlink, hardlink, dangling link, FIFO and nondirectory refusals; allowed internal SwiftPM links stay allowed.', 'exact-source-existing-staging-suite')
    add('B01', 'complete-consumer', 'Fresh frozen CLI, selected real SDK/adapter, actual create and complete unsigned cross-build.',
        'Actual Swift/JNI/Java/D8/AAPT2/zipalign APK with locks, symbols, native libraries, complete asset inventory and exact descriptor identity; no signing/runtime qualification.', 'fresh-complete-unsigned-cross-build')
    add('B02', 'codec-verification', 'Extract asset from actual independently built APK; fresh review-owned host probe uses exact frozen real MixerUI codec and production pure Java codec.',
        'Both real codecs validate default/shared/empty catalog/system sans; canonical encode equals exact extracted bytes. Noncanonical negative rejects.', 'fresh-host-codecs-not-installed-capture')
    value = {
        'schema_version': 1,
        'frozen_before_implementation_access': True,
        'accepted_revision': '99d6384306ea17643b70c472f93b57418c674f86',
        'selection_sha256': '30171f00f98ed7e27c8f9654f0c997a7c9672e282697a7a4c8fa7bfca1d98582',
        'descriptor_source_relative': 'app/assets/MixerAppearanceV2/descriptor.json',
        'descriptor_apk_entry': 'assets/MixerAppearanceV2/descriptor.json',
        'descriptor_bytes_bounds_inclusive': [1, 65536],
        'retained_reference_only': {'bytes': 9587, 'sha256': '1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3',
                                    'authority': 'Prior reviewed observed API output; never product input or arbitrary SDK compatibility proof.'},
        'negative_command_controls': {'deadline_seconds': 5, 'owned_output_sentinels': True,
                                      'owned_fake_tool_attempt_sentinel': True,
                                      'private_owned_process_group': True,
                                      'no_process_inventory_or_native_tools': True},
        'no_claims': ['Unauthenticated rewritten local lock semantics', 'Hostile-code sandbox',
                      'Arbitrary copied-SDK default/API/ABI equivalence', 'Public V2',
                      'Native installed capture/runtime/UI', 'Physical matrix', 'Signed/release/GA authority'],
        'vectors': vectors,
    }
    assert len({row['id'] for row in vectors}) == len(vectors)
    (BASE / 'vectors.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'independent_vectors': len(vectors), 'product_execution': False}, sort_keys=True))


if __name__ == '__main__':
    main()
