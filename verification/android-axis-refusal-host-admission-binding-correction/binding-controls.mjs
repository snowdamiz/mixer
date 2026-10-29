import {equal, requireThat, sha, verifyBinding} from './verify.mjs';

// Inert pure source/data controls; no filesystem, process, compiler, network or UI APIs.
export const priorDirectory = "verification/android-axis-refusal-host-admission-expression-correction";
export const correctedDirectory = "verification/android-axis-refusal-host-admission-binding-correction";
export const priorEqualSource = "export function equal(a, b, message) { requireThat(JSON.stringify(a) === JSON.stringify(b), message); }";
export const correctedEqualSource = "// Compare JSON values, not the insertion order of their serialized object keys.\n// Validate both complete operands first: even identical non-JSON inputs fail closed.\nfunction requireJSONValue(value, ancestors, message) {\n  if (value === null || typeof value === 'string' || typeof value === 'boolean') return;\n  if (typeof value === 'number') { requireThat(Number.isFinite(value), message); return; }\n  requireThat(typeof value === 'object', message);\n  const array = Array.isArray(value);\n  const prototype = Object.getPrototypeOf(value);\n  requireThat(array ? prototype === Array.prototype : prototype === Object.prototype || prototype === null, message);\n  requireThat(!ancestors.has(value), message);\n  const descriptors = Object.getOwnPropertyDescriptors(value);\n  const keys = Reflect.ownKeys(descriptors);\n  if (array) {\n    requireThat(keys.length === value.length + 1 && keys.includes('length'), message);\n    for (let index = 0; index < value.length; index++) requireThat(Object.hasOwn(descriptors, String(index)), message);\n  }\n  ancestors.add(value);\n  try {\n    for (const key of keys) {\n      requireThat(typeof key === 'string', message);\n      if (array && key === 'length') continue;\n      const descriptor = descriptors[key];\n      requireThat(descriptor.enumerable === true && Object.hasOwn(descriptor, 'value'), message);\n      requireJSONValue(descriptor.value, ancestors, message);\n    }\n  } finally { ancestors.delete(value); }\n}\nfunction sameJSONValue(a, b) {\n  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return Object.is(a, b);\n  if (Array.isArray(a) !== Array.isArray(b)) return false;\n  if (Array.isArray(a)) return a.length === b.length && a.every((value, index) => sameJSONValue(value, b[index]));\n  const keys = Object.keys(a);\n  return keys.length === Object.keys(b).length && keys.every(key => Object.hasOwn(b, key) && sameJSONValue(a[key], b[key]));\n}\nexport function equal(a, b, message) {\n  requireJSONValue(a, new Set(), message);\n  requireJSONValue(b, new Set(), message);\n  requireThat(sameJSONValue(a, b), message);\n}";
export const authorityNote = "This source-only sibling grants no workflow installation, selection, dispatch or additional allowance. The previous expression-correction manual attempt is consumed without replay. The per-attempt mechanism ceilings are retained as data, not renewed authority. Root must independently select any later delivery and allowance, bind its delivered source revision after push, and reconcile actual run identity. A null run_id is unbound; it does not authorize submission.";

export function verifyPreparedCorrection({priorVerifier, verifier, priorWorkflow, workflow, priorTemplateBytes, template}) {
  equal(sha(priorVerifier), 'cb62acbbe45fc98d205e3b7b8dfa0d6cc83975c5e9ca3a0e5227e05d57a1dbad', 'Frozen expression verifier');
  equal(sha(priorWorkflow), '8483fbf0b110ab9f1806004f51b857d47eebb46acb9521ee1ee91bbfb5a86dc5', 'Frozen expression workflow');
  equal(sha(priorTemplateBytes), 'd95cb2e7734451d61d0c9f80b03bb4fb6573c7e84fe965ea1605edf8f7cf9527', 'Frozen expression template');
  equal(priorVerifier.split(priorEqualSource).length, 2, 'One prior comparator');
  equal(verifier, priorVerifier.replace(priorDirectory, correctedDirectory).replace(priorEqualSource, () => correctedEqualSource), 'Only admission path and strict JSON equality source delta');
  equal(workflow, priorWorkflow.replaceAll(priorDirectory, correctedDirectory), 'Only workflow admission paths changed');
  const expectedTemplate = JSON.parse(priorTemplateBytes.toString('utf8'));
  expectedTemplate.workflow_sha256 = sha(workflow);
  expectedTemplate.authority_note = authorityNote;
  equal(template, expectedTemplate, 'Only final workflow hash and no-new-authority prose changed in false template');
  equal([template.selected, template.dispatch_authorized, template.source_revision, template.run_id], [false, false, null, null], 'False unbound template');
  requireThat(verifier.includes('rootSelectionSHA256: sha(JSON.stringify(selection))'), 'Serialized selection hash retained separately');
  requireThat(verifier.includes("equal(String(context.run_attempt), '1'") && verifier.includes('equal(String(context.run_id), String(selection.run_id)'), 'Existing explicit ID normalization retained');
}

// For these ASCII JSON fixtures, this composes the actual Python producer's
// sort_keys=True, separators=(',', ':') transformation without running Python.
export function producerSerialization(value) {
  const sorted = item => Array.isArray(item) ? item.map(sorted) : item !== null && typeof item === 'object' ? Object.fromEntries(Object.keys(item).sort().map(key => [key, sorted(item[key])])) : item;
  return JSON.stringify(sorted(value));
}
export function reverseObjectKeys(value) {
  return Array.isArray(value) ? value.map(reverseObjectKeys) : value !== null && typeof value === 'object' ? Object.fromEntries(Object.keys(value).reverse().map(key => [key, reverseObjectKeys(value[key])])) : value;
}

export function runBindingControls(input) {
  const {template, roster, manifest, snapshot, actualProducerWire, actualPrettySelection} = input;
  const results = [];
  const test = (name, body) => { body(); results.push({name, status: 'pass'}); };
  const rejects = body => { let refused = false; try { body(); } catch { refused = true; } requireThat(refused, 'Expected refusal'); };
  const refuse = (name, body) => test(name, () => rejects(body));
  const invalid = (name, create) => test(name, () => { const value = create(); rejects(() => equal(value, value, name)); rejects(() => equal(value, null, name)); rejects(() => equal(null, value, name)); });
  test('exact-prepared-source-workflow-template-delta', () => verifyPreparedCorrection(input));
  refuse('changed-comparator-source-refused', () => verifyPreparedCorrection({...input, verifier: input.verifier.replace('Object.is(a, b)', 'a == b')}));
  refuse('changed-workflow-bound-refused', () => verifyPreparedCorrection({...input, workflow: input.workflow.replace('ulimit -f 65536', 'ulimit -f 65537')}));
  refuse('changed-false-template-bound-refused', () => verifyPreparedCorrection({...input, template: {...template, max_manual_dispatches: 2}}));
  const context = {repository: 'snowdamiz/mixer', sha: 'a'.repeat(40), event: 'workflow_dispatch', profile: 'axis-refusal-host-v1', run_id: '123456', run_attempt: '1'};
  const selected = {...structuredClone(template), selected: true, dispatch_authorized: true, source_revision: context.sha};
  const bind = value => verifyBinding(value, context, selected.workflow_sha256);
  test('producer-sorted-compact-parse-current-binding', () => bind(JSON.parse(producerSerialization(selected))));
  test('producer-sorted-pretty-parse-current-binding', () => bind(JSON.parse(JSON.stringify(JSON.parse(producerSerialization(selected)), null, 2))));
  test('recursive-reverse-key-permutation-current-binding', () => bind(reverseObjectKeys(selected)));
  test('wire-selection-hash-remains-serialized-input-specific', () => { const left = bind(selected); const changed = reverseObjectKeys(selected); const right = bind(changed); equal(left.rootSelectionSHA256, sha(JSON.stringify(selected)), 'Original serialized identity'); equal(right.rootSelectionSHA256, sha(JSON.stringify(changed)), 'Permuted serialized identity'); requireThat(left.rootSelectionSHA256 !== right.rootSelectionSHA256, 'Key order remains observable in separate byte identity'); });
  test('actual-wire-identity', () => { requireThat(Buffer.isBuffer(actualProducerWire), 'Exact retained wire bytes required'); equal(actualProducerWire.length, 1624, 'Actual wire length'); equal(sha(actualProducerWire), '3af103fcba99e9fd728f40c7642acbd5c9418f73e156ad62a7ce968c18d98874', 'Actual wire SHA256'); });
  test('actual-pretty-identity', () => { requireThat(Buffer.isBuffer(actualPrettySelection), 'Exact retained pretty bytes required'); equal(actualPrettySelection.length, 1802, 'Actual pretty length'); equal(sha(actualPrettySelection), '42c593d7fdecbaf7c471acfee1fac16b32c348ecfeffd20ebb1ac673d1cfa620', 'Actual pretty SHA256'); });
  const actual = JSON.parse(actualProducerWire.toString('utf8'));
  const actualPretty = JSON.parse(actualPrettySelection.toString('utf8'));
  const actualContext = {repository: 'snowdamiz/mixer', sha: '2cea1013151ccc38bb635fb4755793cd25a0bd1b', event: 'workflow_dispatch', profile: 'axis-refusal-host-v1', run_id: '40909865814', run_attempt: '1'};
  test('actual-producer-sorted-serialization-composes-with-JSON-parse', () => { equal(producerSerialization(actualPretty), actualProducerWire.toString('utf8'), 'Actual producer transform'); equal(actual, actualPretty, 'Actual wire and pretty JSON values'); });
  test('actual-failed-wire-now-passes-binding-as-data-only', () => { const binding = verifyBinding(actual, actualContext, '8483fbf0b110ab9f1806004f51b857d47eebb46acb9521ee1ee91bbfb5a86dc5'); equal(binding.rootSelectionSHA256, sha(actualProducerWire), 'Actual compact serialized identity'); });
  test('actual-host-and-budget-order-were-serialized-mismatches', () => { equal(actual.host, template.host, 'Exact host values'); equal(actual.budget, template.budget, 'Exact budget values'); requireThat(JSON.stringify(actual.host) !== JSON.stringify(template.host), 'Actual host insertion order differs'); requireThat(JSON.stringify(actual.budget) !== JSON.stringify(template.budget), 'Actual budget insertion order differs'); });
  for (const field of ['host', 'budget']) {
    for (const key of Object.keys(selected[field])) {
      const changed = structuredClone(selected); changed[field][key] = typeof changed[field][key] === 'number' ? changed[field][key] + 1 : changed[field][key] + '-changed';
      refuse(field + '-changed-value-' + key, () => bind(changed));
      const typed = structuredClone(selected); typed[field][key] = typeof typed[field][key] === 'number' ? String(typed[field][key]) : 1;
      refuse(field + '-changed-type-' + key, () => bind(typed));
      const missing = structuredClone(selected); delete missing[field][key];
      refuse(field + '-missing-key-' + key, () => bind(missing));
    }
    const extra = structuredClone(selected); extra[field].unexpected = false;
    refuse(field + '-extra-key', () => bind(extra));
    test(field + '-reverse-keys-accepted', () => bind({...selected, [field]: reverseObjectKeys(selected[field])}));
  }
  refuse('false-unbound-template-still-refused', () => bind(template));
  test('explicit-String-run-ID-normalization-preserved', () => verifyBinding({...selected, run_id: 123456}, {...context, run_id: 123456, run_attempt: 1}, selected.workflow_sha256));
  // Top-level selection remains field-validated. Unknown-key rejection below
  // applies to complete objects compared by equal(), including host and budget.
  test('roster-object-key-permutations-accepted', () => equal(reverseObjectKeys(roster.suites), manifest.test_membership.map(({suite, framework, names}) => ({suite, framework, names})), 'Exact roster with permuted object keys'));
  refuse('roster-suite-array-order-refused', () => equal([...roster.suites].reverse(), roster.suites, 'Suite order'));
  const changedRoster = structuredClone(roster.suites); changedRoster[0].names.reverse();
  refuse('roster-method-array-order-refused', () => equal(changedRoster, roster.suites, 'Method order'));
  test('snapshot-object-key-permutations-accepted', () => equal(reverseObjectKeys(snapshot), snapshot, 'Snapshot JSON values'));
  refuse('snapshot-source-row-order-refused', () => equal({...snapshot, rows: [...snapshot.rows].reverse()}, snapshot, 'Source row order'));
  test('nested-object-key-permutations-accepted', () => equal({b: [{z: null, a: [true, 7, 's']}], a: {y: 2, x: 1}}, {a: {x: 1, y: 2}, b: [{a: [true, 7, 's'], z: null}]}, 'Recursive keys'));
  test('null-prototype-JSON-object-accepted', () => equal(Object.assign(Object.create(null), {b: 2, a: 1}), {a: 1, b: 2}, 'JSON object prototype is not a value'));
  test('noncyclic-shared-references-accepted-as-JSON-values', () => { const shared = {a: 1}; equal({a: shared, b: shared}, {a: {a: 1}, b: {a: 1}}, 'Repeated noncyclic JSON values'); });
  test('own-proto-key-compared-as-data', () => equal(JSON.parse('{"__proto__":{"a":1},"x":2}'), JSON.parse('{"x":2,"__proto__":{"a":1}}'), 'Own __proto__ JSON data'));
  for (const value of [null, true, false, '', 'string', 0, -0, 1, -1, 0.5]) test('exact-JSON-scalar-' + typeof value + '-' + String(value) + '-' + (Object.is(value, -0) ? 'negative-zero' : 'ordinary'), () => equal(value, value, 'Exact JSON scalar'));
  for (const [name, left, right] of [['number-string', 1, '1'], ['boolean-number', false, 0], ['null-false', null, false], ['string-case', 'x', 'X'], ['positive-negative-zero', 0, -0], ['array-object', [], {}], ['array-position', [1, 2], [2, 1]], ['array-length', [1], [1, 2]], ['nested-changed', {a: {b: 1}}, {a: {b: 2}}], ['nested-missing', {a: {b: 1}}, {a: {}}], ['nested-extra', {a: {b: 1}}, {a: {b: 1, c: false}}]]) refuse(name, () => equal(left, right, name));
  invalid('undefined-refused-even-self', () => undefined);
  invalid('function-refused-even-self', () => function forbidden() {});
  invalid('symbol-refused-even-self', () => Symbol('forbidden'));
  invalid('bigint-refused-even-self', () => 1n);
  invalid('NaN-refused-even-self', () => NaN);
  invalid('positive-Infinity-refused-even-self', () => Infinity);
  invalid('negative-Infinity-refused-even-self', () => -Infinity);
  invalid('nested-undefined-refused-even-self', () => ({x: undefined}));
  invalid('nested-function-refused-even-self', () => ({x() {}}));
  invalid('nested-NaN-refused-even-self', () => ({x: [NaN]}));
  invalid('sparse-array-refused-even-self', () => new Array(1));
  invalid('array-undefined-refused-even-self', () => [undefined]);
  invalid('array-extra-string-key-refused-even-self', () => Object.assign([1], {extra: 2}));
  invalid('array-symbol-key-refused-even-self', () => Object.assign([1], {[Symbol('extra')]: 2}));
  invalid('object-symbol-key-refused-even-self', () => ({[Symbol('extra')]: 2}));
  invalid('nonenumerable-object-key-refused-even-self', () => Object.defineProperty({}, 'hidden', {value: 1}));
  invalid('nonenumerable-array-index-refused-even-self', () => Object.defineProperty([1], '0', {value: 1, enumerable: false}));
  for (const [name, create] of [['object', get => Object.defineProperty({}, 'getter', {enumerable: true, get})], ['array', get => Object.defineProperty([1], '0', {enumerable: true, get})]]) test('accessor-' + name + '-refused-without-getter-call', () => { let calls = 0; const value = create(() => { calls++; return 1; }); rejects(() => equal(value, value, 'Accessor')); rejects(() => equal(value, null, 'Accessor')); rejects(() => equal(null, value, 'Accessor')); requireThat(calls === 0, 'Accessor must never be invoked'); });
  invalid('Date-refused-even-self', () => new Date(0));
  invalid('Map-refused-even-self', () => new Map([['a', 1]]));
  invalid('Set-refused-even-self', () => new Set([1]));
  invalid('boxed-number-refused-even-self', () => Object(1));
  invalid('typed-array-refused-even-self', () => new Uint8Array([1]));
  invalid('custom-prototype-refused-even-self', () => Object.create({inherited: 1}));
  invalid('array-subclass-refused-even-self', () => new (class extends Array {})(1, 2));
  invalid('custom-toJSON-refused-even-self', () => ({toJSON() { return {}; }}));
  invalid('self-cycle-refused-even-self', () => { const value = {}; value.self = value; return value; });
  invalid('array-cycle-refused-even-self', () => { const value = []; value.push(value); return value; });
  invalid('mutual-cycle-refused-even-self', () => { const left = {}, right = {left}; left.right = right; return left; });
  return {schema: 1, status: 'passed-data-only-binding-controls', count: results.length, results, actual_input_is_retained_failure_data_only: true, synthetic_binding_acceptance_does_not_authorize_dispatch_or_establish_host_evidence: true};
}
