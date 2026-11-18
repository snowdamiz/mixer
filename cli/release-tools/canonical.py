def cbor(value):
    def head(kind, number):
        if number < 24:
            return bytes([kind * 32 + number])
        for width, tag in ((1, 24), (2, 25), (4, 26), (8, 27)):
            if number < 1 << (8 * width):
                return bytes([kind * 32 + tag]) + number.to_bytes(width, "big")
        raise ValueError("integer outside uint64")

    if isinstance(value, bool):
        return bytes([0xF5 if value else 0xF4])
    if isinstance(value, int):
        return head(0, value)
    if isinstance(value, str):
        encoded = value.encode()
        return head(3, len(encoded)) + encoded
    if isinstance(value, list):
        return head(4, len(value)) + b"".join(map(cbor, value))
    if isinstance(value, dict):
        pairs = sorted((cbor(key), cbor(item)) for key, item in value.items())
        return head(5, len(value)) + b"".join(key + item for key, item in pairs)
    raise TypeError(type(value))
