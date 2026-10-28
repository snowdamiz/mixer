#!/usr/bin/env python3
"""Finite source-qualified layout association; never a price or peak model."""
import re

OWNER = 'experimental_swift_reactor::retained_profile_loader_v1::prepaid_input_owner_v1::'
LOADER = 'experimental_swift_reactor::retained_profile_loader_v1::'
ENTRY = 'experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::'
CHILD = ENTRY + 'host_account_v1::'
OWNER_NAMES = ['AdmittedLoaderCorrespondenceV1', 'PrepaidCorrelationAttemptV1', 'RootBoundV1',
    'LoaderCarrierCoreV1', 'OriginalCorrelationRefusalV1', 'RawSelectedBundleV1', 'CorrelatedSelectedProfileV1',
    'RootBoundSelectedProfileV1', 'RawCorrelationOutcomeV1', 'OwnedCorrelationOutcomeV1', 'FixtureLeafArgumentsV1',
    'RawFixturePrimaryV1', 'RawFixtureResultV1', 'RootBoundFixtureOutcomeV1', 'RootBoundPrimaryBorrowV1',
    'BootstrapFailureV1', 'BootstrapLedgerV1']
QUALIFIED = {OWNER + name: name for name in OWNER_NAMES}
QUALIFIED.update({LOADER + name: name for name in ['ReturnedLoaderFilesV1', 'LoaderUsageV1']})
QUALIFIED.update({ENTRY + name: name for name in ['AdmittedFixtureOutcomeV1', 'AdmittedFixturePayloadV1']})
QUALIFIED.update({CHILD + name: name for name in ['PrepaidOwnedV1', 'RefusalV1']})
QUALIFIED.update({'std::result::Result': 'Result', 'std::option::Option': 'Option', 'std::fs::File': 'File'})
TOKEN = re.compile(r'[A-Za-z_][A-Za-z_0-9]*(?:::[A-Za-z_][A-Za-z_0-9]*)*')


class Refusal(ValueError):
    pass


def normalize(spelling):
    if not isinstance(spelling, str) or not spelling:
        raise Refusal('missing-type-spelling')
    if '{closure@' in spelling:
        return spelling
    # Explicit reference lifetime versus elision has no extra representation;
    # generic lifetime positions retain arity. This never equates ownership,
    # funding, borrow permissions, generic payload substitutions or newtypes.
    text = re.sub(r"&\s*'(?:static|_)(?![A-Za-z_0-9])\s*", '&', spelling)
    text = re.sub(r"'(?:static|_)(?![A-Za-z_0-9])", "'L", text)
    text = TOKEN.sub(lambda match: QUALIFIED.get(match[0], match[0]), text)
    return ''.join(text.split())


def observed_map(layouts):
    result = {}
    for row in layouts:
        key = normalize(row['type'])
        if key in result:
            raise Refusal('duplicate-or-colliding-observed-shape')
        if type(row['size']) is not int or type(row['align']) is not int or not 0 < row['size'] < 2**64:
            raise Refusal('invalid-observed-size')
        align = row['align']
        if not 0 < align < 2**64 or align & (align - 1) or row['size'] % align:
            raise Refusal('invalid-observed-alignment')
        result[key] = row
    return result


def require_link(spelling, shapes, *, target, source_tree, expected_target, expected_tree):
    if target != expected_target or source_tree != expected_tree:
        raise Refusal('cross-target-or-source-layout-reuse')
    key = normalize(spelling)
    if key not in shapes:
        raise Refusal('unobserved-exact-shape')
    return shapes[key]


def checked_difference(source, destination):
    for value in (source, destination):
        if type(value) is not int or not 0 <= value < 2**64:
            raise Refusal('target-usize-arithmetic-input')
    if destination < source:
        raise Refusal('negative-wrapper-uplift')
    return destination - source


def require_closure(spelling, role_identity, *, exact_spelling, allowed_roles):
    if spelling != exact_spelling or role_identity not in allowed_roles:
        raise Refusal('wrong-or-ambiguous-actual-closure-role')
    return {'size': 48, 'align': 8}


def prohibit_total(roles, *, claim):
    if claim in {'work-price', 'storage-charge', 'simultaneous-peak', 'backing-capacity', 'funding', 'full-ownership'}:
        raise Refusal('layout-role-links-do-not-authorize-' + claim)
    raise Refusal('no-additive-total-over-overlapping-role-inventory')
