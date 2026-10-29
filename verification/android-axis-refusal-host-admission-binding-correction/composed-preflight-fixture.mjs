import {createHash} from 'node:crypto';

// Inert in-memory filesystem adapter for root-reviewed DATA-ONLY execution.
// No filesystem/process/network/native API is imported or delegated here.
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const check = (value, message) => { if (!value) throw new Error(message); };
const sourceManifestHash = '601b9722df4f42c6649f0e0b6943fe5e3ad96bc6ebeeeecc186da475875e5782';
const sourceReviewHash = '7dce2a7630a22f095b0953444b214e5ee0b219213e168b0867c7d626f19ea3fa';
const appleVerifierHash = '74a3e0261a8dcd9faa075333a09d33f635e5a96351560c4a4d94d1a90b11c442';
const sourceProjection = '257ed4dfa93d43b15d4bfe2d51372d261e4fec5fd9e80c3f1ca62b1967a3a793';
const candidateWorkflowHash = '01bbe4cb7271367c60dc711cc5bfb731bef3d8f60f5353b13765a0aba3476cce';
const candidateVerifierHash = '3e06379857607464d5b0eb124aaa079c7b02bfffd6c29b8d7900f1f03a724319';
const rosterHash = 'ab504f3105379b3e225f8ef1b1b65c7650ef57e3a4e21f3ef2d9cbe150a493cf';
const admission = 'verification/android-axis-refusal-host-admission-binding-correction';
const prep = 'verification/android-axis-refusal-host-preparation';
const sortKeys = value => Array.isArray(value) ? value.map(sortKeys) : value !== null && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, sortKeys(value[key])])) : value;

export function verifierSourceForAdapter(candidateVerifierBytes, adapterModuleURL) {
  check(Buffer.isBuffer(candidateVerifierBytes) && hash(candidateVerifierBytes) === candidateVerifierHash, 'Exact reviewed candidate verifier required');
  check(typeof adapterModuleURL === 'string' && adapterModuleURL.startsWith('data:text/javascript;base64,'), 'Root-owned inert adapter data module required');
  const source = candidateVerifierBytes.toString('utf8');
  const marker = "import * as fs from 'node:fs/promises';";
  check(source.split(marker).length === 2, 'One exact fs import');
  return source.replace(marker, () => 'import * as fs from ' + JSON.stringify(adapterModuleURL) + ';');
}

export function createComposedPreflightFixture({files, selectionWire, context}) {
  check(files instanceof Map && files.size === 32, 'Exactly32 independently acquired source/input files required');
  check(Buffer.isBuffer(selectionWire) && selectionWire.length <= 65536, 'Bounded producer selection bytes required');
  const wire = selectionWire.toString('utf8');
  const selection = JSON.parse(wire);
  check(wire === JSON.stringify(sortKeys(selection)), 'Use actual intended recursively sorted compact producer serialization');
  const fileBytes = new Map();
  for (const [relative, bytes] of files) {
    check(typeof relative === 'string' && /^(?:[A-Za-z0-9._-]+\/)*[A-Za-z0-9._-]+$/.test(relative) && !relative.split('/').includes('..'), 'Exact safe relative file path');
    check(Buffer.isBuffer(bytes) && bytes.length <= 1048576, 'Bounded immutable input Buffer');
    fileBytes.set(relative, Buffer.from(bytes));
  }
  const get = relative => { check(fileBytes.has(relative), 'Missing exact fixture member: ' + relative); return fileBytes.get(relative); };
  check(hash(get('.github/workflows/android-axis-refusal-host.yml')) === candidateWorkflowHash, 'Candidate workflow bytes');
  check(hash(get(prep + '/source-manifest.json')) === sourceManifestHash, 'Frozen source manifest');
  check(hash(get('verification/android-axis-refusal-host-review/receipt.json')) === sourceReviewHash, 'Frozen independent review');
  check(hash(get('scripts/ci/verify-apple-toolchain.py')) === appleVerifierHash, 'Frozen Apple verifier source');
  check(hash(get(admission + '/required-tests.json')) === rosterHash, 'Exact candidate roster');
  const manifest = JSON.parse(get(prep + '/source-manifest.json').toString('utf8'));
  check(manifest.source_rows.length === 27, 'Exact27 package members');
  const expected = ['.github/workflows/android-axis-refusal-host.yml', prep + '/source-manifest.json', 'verification/android-axis-refusal-host-review/receipt.json', 'scripts/ci/verify-apple-toolchain.py', admission + '/required-tests.json'];
  const rows = [];
  for (const row of manifest.source_rows) {
    const relative = prep + '/package/' + row.path;
    const bytes = get(relative);
    check(bytes.length === row.bytes && hash(bytes) === row.sha256, 'Exact frozen package member');
    expected.push(relative);
    rows.push({path: row.path, bytes: bytes.length, sha256: hash(bytes)});
  }
  check(JSON.stringify([...fileBytes.keys()].sort()) === JSON.stringify(expected.sort()), 'Exact32-member fixture inventory');
  rows.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  check(rows.reduce((sum, row) => sum + row.bytes, 0) === 284605, 'Frozen source byte total');
  check(hash(rows.map(row => row.path + '\0' + row.sha256 + '\n').join('')) === sourceProjection, 'Frozen source projection');
  const expectedSource = {schema: 1, status: 'exact-27-source-members', sourceManifestSHA256: sourceManifestHash, sourceReviewSHA256: sourceReviewHash, projection: sourceProjection, rows, bytes: 284605};
  const root = '/axis-binding-data-fixture/workspace';
  const outputDirectory = '/axis-binding-data-fixture/output';
  const absoluteFiles = new Map([...fileBytes].map(([relative, bytes]) => [root + '/' + relative, bytes]));
  const directories = new Set([root]);
  for (const filename of absoluteFiles.keys()) { let parent = filename.slice(0, filename.lastIndexOf('/')); while (parent.startsWith(root)) { directories.add(parent); parent = parent.slice(0, parent.lastIndexOf('/')); } }
  const receipts = new Map();
  const allowedReceipts = new Set(['root-selection.json', 'context.json', 'binding.json', 'source-before.json'].map(name => outputDirectory + '/' + name));
  const calls = {lstat: 0, readFile: 0, readdir: 0, mkdir: 0, writeFile: 0};
  const regularStat = bytes => ({size: bytes.length, isFile: () => true, isDirectory: () => false, isSymbolicLink: () => false});
  const directoryStat = () => ({size: 0, isFile: () => false, isDirectory: () => true, isSymbolicLink: () => false});
  const adapter = Object.freeze({
    async lstat(filename) { calls.lstat++; if (absoluteFiles.has(filename)) return regularStat(absoluteFiles.get(filename)); if (directories.has(filename)) return directoryStat(); throw new Error('Denied virtual lstat: ' + filename); },
    async readFile(filename) { calls.readFile++; check(absoluteFiles.has(filename), 'Denied virtual read: ' + filename); return Buffer.from(absoluteFiles.get(filename)); },
    async readdir(directory, options) {
      calls.readdir++; check(directories.has(directory) && options?.withFileTypes === true, 'Denied virtual readdir');
      const children = new Map();
      for (const filename of absoluteFiles.keys()) if (filename.startsWith(directory + '/')) { const rest = filename.slice(directory.length + 1); const slash = rest.indexOf('/'); const name = slash < 0 ? rest : rest.slice(0, slash); children.set(name, slash >= 0); }
      return [...children].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([name, directory]) => ({name, isDirectory: () => directory, isFile: () => !directory, isSymbolicLink: () => false}));
    },
    async mkdir(directory, options) { calls.mkdir++; check(directory === outputDirectory && options?.recursive === false && !directories.has(directory), 'Only one new owned virtual output directory'); directories.add(directory); },
    async writeFile(filename, data) { calls.writeFile++; check(directories.has(outputDirectory) && allowedReceipts.has(filename) && !receipts.has(filename), 'Only four single-write owned virtual receipts'); const bytes = Buffer.from(data); check(bytes.length <= 1048576, 'Bounded virtual receipt'); receipts.set(filename, bytes); },
  });
  return Object.freeze({
    root, outputDirectory, adapter, selection: JSON.parse(wire), context: structuredClone(context),
    verifyReceipts(result, {equal, verifyBinding}) {
      check(calls.mkdir === 1 && calls.writeFile === 4 && receipts.size === 4, 'Exactly one composed preflight and four receipts');
      check(calls.readFile === 32, 'All32 exact fixture input files read by composed preflight');
      const parsed = {};
      for (const filename of allowedReceipts) parsed[filename.slice(outputDirectory.length + 1)] = JSON.parse(receipts.get(filename).toString('utf8'));
      equal(parsed['root-selection.json'], selection, 'Reparsed producer selection receipt');
      equal(parsed['context.json'], context, 'Reparsed context receipt');
      equal(parsed['source-before.json'], expectedSource, 'Reparsed actual frozen27 source snapshot and roster traversal');
      equal(result.source, expectedSource, 'Composed source snapshot result');
      const rebound = verifyBinding(parsed['root-selection.json'], parsed['context.json'], candidateWorkflowHash);
      equal(parsed['binding.json'], rebound, 'Reparsed receipt binding');
      equal(result.binding, rebound, 'Composed preflight binding result');
      equal(rebound.rootSelectionSHA256, hash(selectionWire), 'Exact producer serialized selection identity');
      const receiptRows = [...receipts].map(([filename, bytes]) => ({path: filename.slice(outputDirectory.length + 1), bytes: bytes.length, sha256: hash(bytes)})).sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
      return {schema: 1, status: 'passed-data-only-composed-preflight-fixture', calls: {...calls}, sourceFiles: 27, fixtureInputFiles: 32, candidateWorkflowSHA256: candidateWorkflowHash, candidateVerifierSHA256: candidateVerifierHash, rootSelectionSHA256: rebound.rootSelectionSHA256, receipts: receiptRows, in_memory_owned_receipts_only: true, live_installed_workflow_touched: false, compiler_or_host_runtime_evidence: false, dispatch_authorized_by_fixture: false};
    },
  });
}
