#!/usr/bin/env python3
"""Finite arithmetic/order model only. This file grants no host/product authority."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX = (1 << 64) - 1
PRODUCT_WORK = 1_000_000_000
PRODUCT_STORAGE = 268_435_456
INGRESS = 33_613
PROVISIONAL_DISPATCH = 1_272
PROVISIONAL_FIXED = 451_814_442


def checked_sum(*items):
    total = 0
    for value in items:
        if type(value) is not int or not 0 <= value <= MAX:
            raise ValueError('unsigned integer required')
        if value > MAX-total:
            raise OverflowError('closed host quote overflows u64')
        total += value
    return total


def reserve_arithmetic(storage_limit, work_limit, storage_used, work_used,
                       storage_quote, work_quote):
    """Model an already-authorized external host account, never its authority."""
    storage = checked_sum(storage_used, storage_quote)
    work = checked_sum(work_used, work_quote)
    checked_sum(storage_limit)
    checked_sum(work_limit)
    if storage > storage_limit or work > work_limit:
        return None  # atomic refusal; neither dimension changed
    return storage, work


# Loader and caller preparation precede consuming ingress. The exact before-
# store interval includes each of the following even on admission failure.
BEFORE_COMMIT = ('files_setup', 'loader', 'loaded_carrier', 'arguments',
                 'carrier_conversion', 'control_initialization',
                 'budget_check', 'deadline_initialization', 'stop_check',
                 'selected_comparison')
AFTER_COMMIT = ('fixed_commit', 'owner_and_admissions', 'construct', 'outer', 'finish')
TAIL = ('diagnostic_destroyed', 'file_source_places_destroyed',
        'all_owned_host_backing_destroyed', 'host_storage_release')
SUCCESS = ('external_host_pregrant',)+BEFORE_COMMIT+AFTER_COMMIT+TAIL


def valid_trace(events):
    """Accept exactly one paid closed run or its terminal paid failure prefix."""
    if events == SUCCESS:
        return True
    # All named failure alternatives are paid upfront and remain terminal.
    # pregrant refusal is outside the child run and creates no child/File owner.
    if events == ('external_pregrant_refused_no_dispatch',):
        return True
    for index in range(len(BEFORE_COMMIT)+len(AFTER_COMMIT)):
        prefix = ('external_host_pregrant',)+(BEFORE_COMMIT+AFTER_COMMIT)[:index+1]
        if events == prefix+('host_failure_finalize',)+TAIL:
            return True
    return False


def main():
    checks = 0
    def require(value):
        nonlocal checks
        assert value
        checks += 1

    require(checked_sum(INGRESS,PROVISIONAL_DISPATCH) == 34_885)
    actual = json.loads((HERE/'driver-inventory.json').read_text())
    require(actual['logical_source_object_union_bytes'] == 95_850)
    require(checked_sum(152_437_784,actual['logical_source_object_union_bytes']) == 152_533_634)
    require(checked_sum(451_703_621,33_613,68_781,7_155,1_272) == PROVISIONAL_FIXED)
    # No WASI is run by the selected leaf. Both optional terms remain retained
    # in the provisional source counter; this model selects no discount.
    require(PROVISIONAL_FIXED < PRODUCT_WORK)
    require(PRODUCT_STORAGE == 256*1024*1024)
    for left in [0,1,MAX//2,MAX-1,MAX]:
        for right in [0,1,MAX//2,MAX-1,MAX]:
            try:
                value = checked_sum(left,right)
                require(value == left+right and value <= MAX)
            except OverflowError:
                require(left+right > MAX)
    for invalid in [-1,MAX+1,False,True,None,1.0,'1']:
        try:
            checked_sum(invalid)
            raise AssertionError('invalid operand accepted')
        except ValueError:
            require(True)
    # Synthetic bounded account values are model inputs, not product quotes.
    # Acceptance at equality, both one-unit shortages, already used account,
    # overflow, refusal atomicity and monotone nonrefundable work are exercised.
    require(reserve_arithmetic(101,37,0,0,101,37) == (101,37))
    require(reserve_arithmetic(100,37,0,0,101,37) is None)
    require(reserve_arithmetic(101,36,0,0,101,37) is None)
    require(reserve_arithmetic(101,37,1,1,100,36) == (101,37))
    old = (3,5)
    require(reserve_arithmetic(101,37,*old,99,1) is None and old == (3,5))
    for args in [(MAX,MAX,MAX,0,1,0),(MAX,MAX,0,MAX,0,1)]:
        try:
            reserve_arithmetic(*args)
            raise AssertionError('overflow accepted')
        except OverflowError:
            require(True)
    require(valid_trace(SUCCESS))
    require(valid_trace(('external_pregrant_refused_no_dispatch',)))
    for index in range(len(BEFORE_COMMIT)+len(AFTER_COMMIT)):
        prefix = ('external_host_pregrant',)+(BEFORE_COMMIT+AFTER_COMMIT)[:index+1]
        failed = prefix+('host_failure_finalize',)+TAIL
        require(valid_trace(failed))
        require(not valid_trace(failed+('loader',)))
        require(not valid_trace(failed+('host_work_refund',)))
    for index in range(len(SUCCESS)):
        require(not valid_trace(SUCCESS[:index]+SUCCESS[index+1:]))
        require(not valid_trace(SUCCESS[:index]+(SUCCESS[index],)+SUCCESS[index:]))
    for index in range(len(SUCCESS)-1):
        events = list(SUCCESS)
        events[index],events[index+1] = events[index+1],events[index]
        require(not valid_trace(tuple(events)))
    require(not valid_trace(('files_setup','external_host_pregrant')+SUCCESS[1:]))
    require(not valid_trace(SUCCESS[:-1]+('host_work_refund',SUCCESS[-1])))
    # A zero product counter at work refusal never releases host reservations.
    fixed_refusal = ('external_host_pregrant',)+BEFORE_COMMIT+('host_failure_finalize',)+TAIL
    require(valid_trace(fixed_refusal))
    require('fixed_commit' not in fixed_refusal)
    require(fixed_refusal.index('host_storage_release') > fixed_refusal.index('diagnostic_destroyed'))
    # No relabeling the product counter store as the earlier host pregrant.
    require(not valid_trace(('fixed_commit',)+SUCCESS[1:]))
    result = dict(schema=1, controls_passed=checks,
                  scope='finite Python arithmetic and exact protocol traces only',
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  before_commit=list(BEFORE_COMMIT), after_commit=list(AFTER_COMMIT), tail=list(TAIL),
                  ingress_plus_provisional_dispatch_upper_envelope=34_885,
                  ingress_upper_envelope_is_complete_loader_or_host_price=False,
                  loader_and_leaf_partial_logical_union=152_533_634,
                  partial_logical_union_is_complete_host_storage_quote=False,
                  numeric_limits_are_authority=False,
                  product_limits=dict(work=PRODUCT_WORK, combined_storage=PRODUCT_STORAGE),
                  host_authority_created=False, product_or_loader_executed=False,
                  final_composition_qualified=False)
    (HERE/'ordering-results.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps(dict(controls_passed=checks, scope=result['scope'])))


if __name__ == '__main__':
    main()
