// Interoperability probe only; no controller or authority implementation.
const assert = require('node:assert/strict');
const largest = '9223372036854775807';
const parsed = JSON.parse('{"counter":9223372036854775807}');
assert.notEqual(BigInt(parsed.counter), BigInt(largest));
const safe = JSON.parse('{"counter":"9223372036854775807"}');
assert.equal(BigInt(safe.counter), 9223372036854775807n);
assert.equal(BigInt('9007199254740993') > BigInt('9007199254740992'), true);
console.log(JSON.stringify({
  scope: 'javascript-integer-interoperability-only', node: process.version,
  number_loses_int64_precision: true, decimal_string_preserves_int64: true,
  bigint_comparison_is_exact: true,
  cleanup: 'no network, process children, files or provider effects'
}));
