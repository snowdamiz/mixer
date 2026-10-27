"""Corrected pure arithmetic utility; no product imports or dispatch authority."""
MAX64 = (1 << 64) - 1


def checked_sum(*values: int) -> int:
    out = 0
    for value in values:
        if not isinstance(value, int) or value < 0 or value > MAX64:
            raise OverflowError('invalid u64 input')
        out += value
        if out > MAX64:
            raise OverflowError('u64 addition')
    return out


def checked_mul(a: int, b: int) -> int:
    for value in (a, b):
        if not isinstance(value, int) or value < 0 or value > MAX64:
            raise OverflowError('invalid u64 input')
    out = a * b
    if out > MAX64:
        raise OverflowError('u64 multiplication')
    return out


def emission(extent: int, blocks: int) -> int:
    return checked_sum(19537, checked_mul(299377, blocks), checked_mul(32, extent))


def quote(ingress: int, setup: int, wasi_finish: int, attached: bool,
          extent: int, blocks: int, dispatch_delta: int) -> int:
    # Incoming prices are explicit interfaces to the other source ledger,
    # not an authorized product API accepting caller-defined scalar permits.
    return checked_sum(451703621, ingress,
                       checked_sum(setup, wasi_finish) if attached else 0,
                       dispatch_delta, 16384, emission(extent, blocks))
