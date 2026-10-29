#!/usr/bin/env node
// Bounded source/data inspection only. Imports only fs/path/crypto; never loads
// subject modules, invokes commands, probes processes or performs network I/O.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = '/Users/andreyyurlov/Documents/dev/mixer';
const HERE = 'verification/swift-pin-bitmap-canonical-integration-preparation';
const SELECTED = 'verification/swift-pin-bitmap-match-binding-correction';
const PINS = {
  seal: '0210ab9c252c6f7a5a3eff077e36c2811c79351d916d78b75b2cda88e2bdf85c',
  manifest: '44cb4d23942522dbe28c519bbfe51f01abf6b7b6d7683099da98a007dabff11f',
  baseline: 'af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b',
  candidate: 'e9282e05cea70d4aceaf6a145fb9f971acb023dd41a7d4651216753666305ba1',
  workflow: 'a90bab7dea218e5a098e45eb370e9b666afdf0bda9100cb35ec14dfc779de024',
};
const MODE = process.argv[2] ?? 'preflight';
if (!['preflight', 'installed'].includes(MODE)) throw Error('Only preflight or installed inspection is supported');
const checks = [];
let readBytes = 0;
function check(name, condition) {
  checks.push({ name, passed: Boolean(condition) });
  if (!condition) throw Error(name);
}
function safeRelative(name) {
  if (typeof name !== 'string' || name === '' || name.includes('\\') || name.includes('\0')
      || path.posix.isAbsolute(name) || path.posix.normalize(name) !== name
      || name.split('/').some(p => ['', '.', '..', '.git'].includes(p))) throw Error('Unsafe relative path');
  return name;
}
function regular(name) {
  safeRelative(name);
  let current = ROOT;
  for (const part of name.split('/')) {
    current = path.join(current, part);
    if (fs.lstatSync(current).isSymbolicLink()) throw Error('Symlink refused');
  }
  const stat = fs.statSync(current);
  if (!stat.isFile() || stat.size > 16 * 1024 * 1024) throw Error('Regular bounded input required');
  return current;
}
function read(name) {
  const actual = regular(name), before = fs.statSync(actual);
  readBytes += before.size;
  if (readBytes > 160 * 1024 * 1024) throw Error('Aggregate read cap');
  const raw = fs.readFileSync(actual), after = fs.statSync(actual);
  if (before.dev !== after.dev || before.ino !== after.ino || before.size !== after.size
      || before.mtimeMs !== after.mtimeMs || raw.length !== before.size) throw Error('Input changed during read');
  return raw;
}
const sha = raw => crypto.createHash('sha256').update(raw).digest('hex');
const metadata = raw => ({ bytes: raw.length, sha256: sha(raw) });
const same = (a, b) => a.bytes === b.bytes && a.sha256 === b.sha256;
const closure = rows => sha(Object.keys(rows).sort().map(n => `${n}\0${rows[n].sha256}\n`).join(''));
function write(name, text) {
  safeRelative(name);
  if (!name.startsWith(`${HERE}/`) || path.posix.dirname(name) !== HERE) throw Error('Write outside owned packet');
  const parent = path.join(ROOT, HERE);
  if (fs.lstatSync(parent).isSymbolicLink()) throw Error('Owned directory symlink');
  const target = path.join(ROOT, name);
  if (fs.existsSync(target) && fs.lstatSync(target).isSymbolicLink()) throw Error('Output symlink');
  if (Buffer.byteLength(text) > 2 * 1024 * 1024) throw Error('Output cap');
  fs.writeFileSync(target, text, { flag: 'w' });
}
function rejected(fn) { try { fn(); return false; } catch { return true; } }

// Myers line edit script with finite work/trace bounds and an independent replay.
function edits(a, b) {
  let v = new Map([[1, 0]]), trace = [], work = 0;
  for (let d = 0; d <= a.length + b.length && d <= 2048; ++d) {
    trace.push(new Map(v));
    if (trace.reduce((n, t) => n + t.size, 0) > 2200000) throw Error('Diff trace cap');
    for (let k = -d; k <= d; k += 2) {
      let x = k === -d || (k !== d && (v.get(k - 1) ?? -1) < (v.get(k + 1) ?? -1))
        ? (v.get(k + 1) ?? 0) : (v.get(k - 1) ?? 0) + 1;
      let y = x - k;
      while (x < a.length && y < b.length && a[x] === b[y]) { ++x; ++y; if (++work > 25000000) throw Error('Diff work cap'); }
      v.set(k, x);
      if (x < a.length || y < b.length) continue;
      const result = [];
      for (let back = d; back >= 0; --back) {
        const prev = trace[back], diagonal = x - y;
        const pk = diagonal === -back || (diagonal !== back && (prev.get(diagonal - 1) ?? -1) < (prev.get(diagonal + 1) ?? -1))
          ? diagonal + 1 : diagonal - 1;
        const px = prev.get(pk) ?? 0, py = px - pk;
        while (x > px && y > py) { result.push([' ', a[x - 1]]); --x; --y; }
        if (back === 0) break;
        if (x === px) { result.push(['+', b[y - 1]]); --y; }
        else { result.push(['-', a[x - 1]]); --x; }
      }
      return result.reverse();
    }
  }
  throw Error('Diff edit bound exceeded');
}
function unified(name, before, after) {
  if (!before.endsWith('\n') || !after.endsWith('\n')) throw Error('Source final LF required');
  const a = before.slice(0, -1).split('\n'), b = after.slice(0, -1).split('\n'), ops = edits(a, b);
  check(`diff source replay ${name}`, ops.filter(o => o[0] !== '+').map(o => o[1]).join('\n') + '\n' === before);
  check(`diff candidate replay ${name}`, ops.filter(o => o[0] !== '-').map(o => o[1]).join('\n') + '\n' === after);
  const oldAt = [0], newAt = [0];
  for (const [kind] of ops) { oldAt.push(oldAt.at(-1) + (kind !== '+' ? 1 : 0)); newAt.push(newAt.at(-1) + (kind !== '-' ? 1 : 0)); }
  const changed = ops.flatMap((o, i) => o[0] === ' ' ? [] : [i]);
  let ranges = [];
  for (const i of changed) {
    const start = Math.max(0, i - 3), end = Math.min(ops.length, i + 4);
    if (ranges.length && start <= ranges.at(-1)[1]) ranges.at(-1)[1] = end;
    else ranges.push([start, end]);
  }
  let output = `--- a/vm/${name}\n+++ b/vm/${name}\n`;
  for (const [start, end] of ranges) {
    const oldCount = oldAt[end] - oldAt[start], newCount = newAt[end] - newAt[start];
    output += `@@ -${oldAt[start] + (oldCount ? 1 : 0)},${oldCount} +${newAt[start] + (newCount ? 1 : 0)},${newCount} @@\n`;
    output += ops.slice(start, end).map(([kind, line]) => kind + line + '\n').join('');
  }
  check(`serialized unified patch replay ${name}`, applyUnified(name, before, output) === after);
  return { text: output, added: ops.filter(o => o[0] === '+').length, removed: ops.filter(o => o[0] === '-').length, hunks: ranges.length };
}
function applyUnified(name, before, patch) {
  const source = before.slice(0, -1).split('\n'), lines = patch.slice(0, -1).split('\n'), output = [];
  if (lines[0] !== `--- a/vm/${name}` || lines[1] !== `+++ b/vm/${name}`) throw Error('Patch headers differ');
  let cursor = 0, row = 2;
  while (row < lines.length) {
    const match = /^@@ -(\d+),(\d+) \+(\d+),(\d+) @@$/.exec(lines[row++]);
    if (!match) throw Error('Malformed unified hunk');
    const [, oldFirst, oldCount, newFirst, newCount] = match.map(Number);
    const start = oldFirst - (oldCount ? 1 : 0), newStart = newFirst - (newCount ? 1 : 0);
    if (start < cursor || start > source.length) throw Error('Patch source order');
    output.push(...source.slice(cursor, start)); cursor = start;
    if (output.length !== newStart) throw Error('Patch destination order');
    let consumed = 0, produced = 0;
    while (row < lines.length && !lines[row].startsWith('@@ ')) {
      const line = lines[row++], kind = line[0], text = line.slice(1);
      if (![' ', '+', '-'].includes(kind)) throw Error('Patch line kind');
      if (kind !== '+') { if (source[cursor++] !== text) throw Error('Patch source context differs'); ++consumed; }
      if (kind !== '-') { output.push(text); ++produced; }
    }
    if (consumed !== oldCount || produced !== newCount) throw Error('Patch hunk counts differ');
  }
  output.push(...source.slice(cursor));
  return output.join('\n') + '\n';
}

try {
  for (const value of ['../vm/x', '/tmp/x', 'vm/../x', '.git/index', 'vm\\src', 'vm//src', 'vm/./src', 'vm/\0x'])
    check(`path refusal ${JSON.stringify(value)}`, rejected(() => safeRelative(value)));
  check('foreign write refused before filesystem effects', rejected(() => write('vm/never-created', '')));
  check('tampered metadata refused', !same({bytes: 1, sha256: 'a'}, {bytes: 1, sha256: 'b'}));
  for (const [a, b] of [['a\nb\n', 'a\nx\nb\n'], ['a\nb\n', 'b\n'], ['a\n', 'x\n'], ['a\n', 'a\n']])
    unified('internal-diff-control', a, b);
  const sealRaw = read(`${SELECTED}/seal.json`), manifestRaw = read(`${SELECTED}/manifest.json`);
  check('selected seal exact', sha(sealRaw) === PINS.seal);
  check('selected manifest exact', sha(manifestRaw) === PINS.manifest);
  const seal = JSON.parse(sealRaw), manifest = JSON.parse(manifestRaw);
  check('selected seal 24 members', Object.keys(seal.files).length === 24);
  for (const [name, row] of Object.entries(seal.files)) check(`selected sealed member ${name}`, same(metadata(read(`${SELECTED}/${safeRelative(name)}`)), row));
  check('selected seal member closure', closure(seal.files) === seal.treeSHA256);
  const names = Object.keys(manifest.baselineFiles).sort();
  check('complete baseline/candidate/materialization rosters', names.length === 136 && JSON.stringify(names) === JSON.stringify(Object.keys(manifest.candidateFiles).sort()) && JSON.stringify(names) === JSON.stringify(Object.keys(manifest.materializationPaths).sort()));
  check('selected baseline closure', closure(manifest.baselineFiles) === PINS.baseline && manifest.baselineTreeSHA256 === PINS.baseline);
  check('selected candidate closure', closure(manifest.candidateFiles) === PINS.candidate && manifest.candidateTreeSHA256 === PINS.candidate);
  const overlays = [...manifest.overlayPaths].sort();
  const changed = names.filter(n => !same(manifest.baselineFiles[n], manifest.candidateFiles[n]));
  check('exactly 15 changed overlays', overlays.length === 15 && new Set(overlays).size === 15 && JSON.stringify(overlays) === JSON.stringify(changed));
  const canonical = {}, candidate = {}, contents = new Map(), paths = [];
  let diff = '';
  for (const name of names) {
    safeRelative(name);
    const expectedPath = overlays.includes(name) ? `${SELECTED}/candidate/vm/${name}` : `vm/${name}`;
    check(`materialization binding ${name}`, manifest.materializationPaths[name] === expectedPath);
    const base = read(`vm/${name}`), selected = read(expectedPath);
    canonical[name] = metadata(base); candidate[name] = metadata(selected);
    check(`canonical ${MODE} preimage ${name}`, same(canonical[name], (MODE === 'preflight' ? manifest.baselineFiles : manifest.candidateFiles)[name]));
    check(`selected candidate member ${name}`, same(candidate[name], manifest.candidateFiles[name]));
    if (overlays.includes(name)) {
      if (MODE === 'preflight') {
        const delta = unified(name, base.toString('utf8'), selected.toString('utf8'));
        diff += delta.text;
        const oldTests = [...base.toString('utf8').matchAll(/#\[test\][\s\S]*?\bfn\s+(\w+)\s*\(/g)].map(m => m[1]);
        const newTests = [...selected.toString('utf8').matchAll(/#\[test\][\s\S]*?\bfn\s+(\w+)\s*\(/g)].map(m => m[1]);
        check(`existing named tests retained ${name}`, oldTests.every(n => newTests.includes(n)));
        paths.push({path: `vm/${name}`, before: canonical[name], after: candidate[name], addedLines: delta.added, removedLines: delta.removed, hunks: delta.hunks, previousNamedTests: oldTests.length, selectedNamedTests: newTests.length});
      }
    }
    if (['src/experimental_swift_reactor/control.rs', 'Cargo.toml'].includes(name)) contents.set(name, selected.toString('utf8'));
  }
  check('actual full canonical closure', closure(canonical) === PINS[MODE === 'preflight' ? 'baseline' : 'candidate']);
  check('actual full selected closure', closure(candidate) === PINS.candidate);
  const budget = contents.get('src/experimental_swift_reactor/control.rs');
  check('original 17 budget fields and defaults unchanged by hash', same(manifest.baselineFiles['src/experimental_swift_reactor/control.rs'], manifest.candidateFiles['src/experimental_swift_reactor/control.rs']));
  check('64 residents pins frames and 86 tickets retained', ['cache_entries: 64,', 'active_pins: 64,', 'frames: 64,', 'MAX_RESERVATION_TICKETS: usize = 86;'].every(s => budget.includes(s)));
  check('dependency manifest unchanged', same(manifest.baselineFiles['Cargo.toml'], manifest.candidateFiles['Cargo.toml']) && same(manifest.baselineFiles['Cargo.lock'], manifest.candidateFiles['Cargo.lock']));
  for (const name of ['include/mixer_vm.h', 'include/mixer_vm_capability.h', 'include/mixer_vm_guest_ui.h']) check(`public header unchanged ${name}`, same(manifest.baselineFiles[name], manifest.candidateFiles[name]));
  const consumerNames = [
    '.github/workflows/verify.yml', 'runtime/build-vm.py', 'runtime/build-tests/test_build_vm.py',
    'experimental-capability-runtime/build-vm.py', 'experimental-capability-runtime/build-tests/test_builder.py',
    'capabilities/tools/generate.py', 'capabilities/tools/export-native-preimage.py', 'capabilities/schema/hashes.json',
    'scripts/check-policy.py', 'scripts/ci/check-sdk-package.py', 'scripts/ci/check-analyzer-framing.py',
    'verification/envelope-partition-default-ci-adoption/adopt_envelope.py',
    'verification/envelope-partition-default-ci-adoption/dependencies.json',
    'verification/shared-fixture-clock-controls-correction/adopt_fixture.py',
    'verification/shared-fixture-clock-controls-correction/dependencies.json',
    'vm/tools/generate-capability-terminals.py', 'vm/profiles/numeric-v2.json', 'vm/profiles/table-memory-v3.json',
    'runtime/Sources/CMixerVM/include/mixer_vm.h',
  ];
  const consumers = {};
  for (const name of consumerNames) consumers[name] = metadata(read(name));
  check('ordinary workflow exact supplied SHA256', consumers['.github/workflows/verify.yml'].sha256 === PINS.workflow);
  for (const name of ['verification/envelope-partition-default-ci-adoption/dependencies.json', 'verification/shared-fixture-clock-controls-correction/dependencies.json']) {
    const dependencies = JSON.parse(read(name));
    check(`ordinary frozen fixture independent of live vm ${name}`, dependencies.members.every(r => !r.path.startsWith('vm/')));
  }
  check('Swift C header mirror retained', consumers['runtime/Sources/CMixerVM/include/mixer_vm.h'].sha256 === candidate['include/mixer_vm.h'].sha256);
  for (const name of names) check(`canonical no mutation postflight ${name}`, same(metadata(read(`vm/${name}`)), canonical[name]));
  for (const name of consumerNames) check(`consumer no mutation postflight ${name}`, same(metadata(read(name)), consumers[name]));
  const result = {
    schema: 1, scope: 'Bounded source/data integration preparation only; no execution acceptance or canonical apply',
    mode: MODE, command: `node ${HERE}/check.mjs ${MODE}`, nodeVersion: process.version,
    agentConfigurationParentSupplied: {model: 'gpt-6.1-sol', reasoningEffort: 'xhigh', freshContext: true},
    checker: metadata(read(`${HERE}/check.mjs`)),
    proposal: metadata(read(`${HERE}/PROPOSAL.md`)),
    deliveredRevisionParentSupplied: '1eec8e0fc270c0409c8920ee22fd2374f3bd249f',
    deliveredGitTreeParentSupplied: 'f20be7de5a047f1983931961cc3d774e56de80a3',
    pins: PINS, sourceMembers: names.length, overlays: overlays.length,
    observedCanonicalClosure: closure(canonical), observedCandidateClosure: closure(candidate),
    changedPaths: paths, consumerInputs: consumers,
    checks: checks.length, failures: checks.filter(c => !c.passed), readBytes,
    pendingHostRunParentSupplied: {runID: 40824584975, attempt: 1, status: 'Root reports FAILURE after about 7m15s in the six-child step; exact cause and independent artifact review not yet relayed; no poll performed'},
    canonicalInstallationSelection: 'Unselected after root-reported host failure',
    preparationFailures: [{command: `node ${HERE}/check.mjs preflight`, nodeVersion: 'v22.23.3', exitCode: 1, originalCheckerSHA256: 'a7f18b88da342de1754154c77344d4824076ca0e8095c0767b748cc1039284ce', phase: 'Module parse before any checker execution', stderr: "check.mjs:139 SyntaxError: Unexpected token ')'", correction: 'Removed one extra closing parenthesis from the names.filter expression; no subject source or input changed'}],
    canonicalApplyPerformed: false, newSubjectRuntimeOrCompilerCommands: 0,
    processInventoryOrHeldProbes: 0, networkCalls: 0, nativeUICapturePhoneRuns: 0,
    cleanup: 'No owned subject child, session, socket, native or capture instance created; no scratch required',
    requiredBeforeApply: ['Root resolves the failed exact-source host run and explicitly selects an accepted candidate', 'Root relay of independent actual acceptance for the exact promoted candidate closure', 'Fresh preflight remains exact immediately before coordinated root-only promotion'],
    limitations: ['Static inspection supplements executable acceptance and never authorizes OTA release', 'Ordinary CI after delivery remains required', 'No native, physical-device, published-package FieldLog, store/customer or GA qualification'],
  };
  if (MODE === 'preflight') {
    write(`${HERE}/canonical-to-candidate.diff`, diff);
    result.diff = metadata(Buffer.from(diff));
    write(`${HERE}/receipt.json`, JSON.stringify(result, null, 2) + '\n');
  }
  console.log(JSON.stringify({mode: MODE, checks: checks.length, failures: result.failures.length, canonicalClosure: result.observedCanonicalClosure, candidateClosure: result.observedCandidateClosure, paths: paths.length, diffBytes: Buffer.byteLength(diff), readBytes, canonicalApplyPerformed: false}));
} catch (error) {
  const failure = {schema: 1, mode: MODE, scope: 'Source/data setup or check failure retained; no acceptance', nodeVersion: process.version, checks, error: String(error), readBytes, canonicalApplyPerformed: false};
  write(`${HERE}/setup-or-check-failure.json`, JSON.stringify(failure, null, 2) + '\n');
  throw error;
}
