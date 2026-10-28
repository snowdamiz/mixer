"""Strict JSON custody: duplicate object keys and non-finite constants reject."""
import json


class DuplicateKey(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKey('duplicate JSON object key: ' + repr(key))
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non-finite JSON constant: ' + value)


def loads(raw):
    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
