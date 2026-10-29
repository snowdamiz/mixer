import * as fs from 'node:fs/promises';
import { createHash } from 'node:crypto';

export const PIN = Object.freeze({
  sourceManifest: '601b9722df4f42c6649f0e0b6943fe5e3ad96bc6ebeeeecc186da475875e5782',
  sourceReview: '7dce2a7630a22f095b0953444b214e5ee0b219213e168b0867c7d626f19ea3fa',
  projection: '257ed4dfa93d43b15d4bfe2d51372d261e4fec5fd9e80c3f1ca62b1967a3a793',
  appleVerifier: '74a3e0261a8dcd9faa075333a09d33f635e5a96351560c4a4d94d1a90b11c442',
  packageRelative: 'verification/android-axis-refusal-host-preparation/package',
  admissionRelative: 'verification/android-axis-refusal-host-admission-result-correction',
  developer: '/Applications/Xcode_26.3.app/Contents/Developer',
  toolchain: 'com.apple.dt.toolchain.XcodeDefault',
  swift: '/Applications/Xcode_26.3.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift',
  capturedStreamCap: 8388608,
  regularFileCap: 67108864,
});
export function sha(bytes) { return createHash('sha256').update(bytes).digest('hex'); }
export function requireThat(value, message) { if (!value) throw new Error(message); }
export function equal(a, b, message) { requireThat(JSON.stringify(a) === JSON.stringify(b), message); }
export async function boundedRead(path, cap = 1048576) {
  const stat = await fs.lstat(path);
  requireThat(stat.isFile() && !stat.isSymbolicLink() && stat.size <= cap, 'Not a bounded regular file: ' + path);
  const bytes = await fs.readFile(path);
  requireThat(bytes.length === stat.size && bytes.length <= cap, 'File changed during bounded read: ' + path);
  return bytes;
}
async function readJSON(path, cap) { return JSON.parse((await boundedRead(path, cap)).toString('utf8')); }
async function walk(base, relative = '', depth = 0) {
  requireThat(depth < 10, 'Package directory depth exceeded');
  const entries = await fs.readdir(base + (relative ? '/' + relative : ''), { withFileTypes: true });
  requireThat(entries.length <= 32, 'Package directory entry cap exceeded');
  let files = [];
  for (const entry of entries) {
    const path = relative ? relative + '/' + entry.name : entry.name;
    requireThat(!entry.isSymbolicLink(), 'Package symlink: ' + path);
    if (entry.isDirectory()) files.push(...await walk(base, path, depth + 1));
    else { requireThat(entry.isFile(), 'Package special member: ' + path); files.push(path); }
    requireThat(files.length <= 27, 'Extra package source member');
  }
  return files.sort();
}
export async function sourceSnapshot(root) {
  const prep = root + '/verification/android-axis-refusal-host-preparation';
  for(const directory of [prep,prep+'/package']) { const stat=await fs.lstat(directory); requireThat(stat.isDirectory()&&!stat.isSymbolicLink(),'Package root directory symlink'); }
  const raw = await boundedRead(prep + '/source-manifest.json');
  equal(sha(raw), PIN.sourceManifest, 'Frozen source manifest drift');
  equal(sha(await boundedRead(root + '/verification/android-axis-refusal-host-review/receipt.json')), PIN.sourceReview, 'Independent review drift');
  equal(sha(await boundedRead(root + '/scripts/ci/verify-apple-toolchain.py')), PIN.appleVerifier, 'Apple verifier drift');
  const manifest = JSON.parse(raw.toString('utf8'));
  requireThat(manifest.source_rows.length === 27, 'Source row count');
  const expected = manifest.source_rows.map(row => row.path).sort();
  equal(await walk(prep + '/package'), expected, 'Exact 27-member package inventory drift');
  const rows = [];
  for (const row of manifest.source_rows) {
    requireThat(/^(?:Package\.swift|(?:Sources|Tests)\/[A-Za-z0-9_/]+\.swift)$/.test(row.path) && !row.path.includes('..'), 'Unsafe source row');
    const bytes = await boundedRead(prep + '/package/' + row.path);
    requireThat(bytes.length === row.bytes && sha(bytes) === row.sha256, 'Source row drift: ' + row.path);
    rows.push({ path: row.path, bytes: bytes.length, sha256: sha(bytes) });
  }
  rows.sort((a,b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  const projection = sha(rows.map(row => row.path + '\0' + row.sha256 + '\n').join(''));
  equal(projection, PIN.projection, 'Package projection drift');
  equal(rows.reduce((sum,row) => sum + row.bytes, 0), 284605, 'Source byte total');
  const roster = await readJSON(root + '/' + PIN.admissionRelative + '/required-tests.json');
  equal(roster.suites, manifest.test_membership.map(({suite,framework,names})=>({suite,framework,names})), 'Exact 19-method roster drift');
  return { schema: 1, status: 'exact-27-source-members', sourceManifestSHA256: PIN.sourceManifest, sourceReviewSHA256: PIN.sourceReview, projection, rows, bytes: 284605 };
}
export function verifyBinding(selection, context, workflowSHA256) {
  requireThat(selection.selected === true && selection.dispatch_authorized === true, 'Root selection and dispatch remain false/unbound');
  equal(selection.mechanism, 'ordinary-github-actions-direct-swiftpm', 'Unselected command mechanism');
  equal(selection.repository, 'snowdamiz/mixer', 'Repository binding');
  equal(selection.workflow_path, '.github/workflows/android-axis-refusal-host.yml', 'Workflow path');
  equal(selection.workflow_sha256, workflowSHA256, 'Installed workflow byte binding');
  equal(selection.profile, 'axis-refusal-host-v1', 'Selected profile');
  requireThat(/^[0-9a-f]{40}$/.test(selection.source_revision ?? ''), 'Root source revision is unbound');
  equal(context.repository, selection.repository, 'Actual repository');
  equal(context.sha, selection.source_revision, 'Actual source revision');
  equal(context.event, 'workflow_dispatch', 'Manual event required');
  equal(context.profile, selection.profile, 'Actual profile');
  requireThat(/^[1-9][0-9]*$/.test(String(context.run_id)), 'Actual run ID');
  equal(String(context.run_attempt), '1', 'Only attempt 1 is selected');
  if (selection.run_id !== null) equal(String(context.run_id), String(selection.run_id), 'Bound run ID');
  equal(selection.max_manual_dispatches, 1, 'One root-dispatched manual run');
  equal(selection.max_run_attempt, 1, 'One attempt');
  equal(selection.host, { runner: 'macos-15', developer_dir: PIN.developer, toolchain: PIN.toolchain, xcode_version: '26.3', xcode_build: '17C529' }, 'Host/tool selection');
  equal(selection.budget, { job_minutes: 30, tool_step_minutes: 3, test_step_minutes: 12, data_step_minutes: 2, artifact_step_minutes: 3, jobs: 2, bash_file_limit_blocks: 65536, bash_file_limit_unit_bytes: 1024, inherited_regular_file_cap_bytes: PIN.regularFileCap, accepted_output_cap_bytes_per_stream: PIN.capturedStreamCap }, 'Finite selected bounds');
  equal(selection.scope, 'isolated-27-file-host-behavior-only', 'Scope');
  for (const field of ['source_pair_selected','canonical_promotion','native_runtime','OTA_or_GA_acceptance']) equal(selection[field], false, 'Forbidden promotion field: ' + field);
  return { event: context.event, repository: context.repository, sha: context.sha, run_id: String(context.run_id), run_attempt: '1', profile: context.profile, workflowSHA256, rootSelectionSHA256: sha(JSON.stringify(selection)) };
}
export function parseTestOutput(stdout, stderr, roster) {
  requireThat(Buffer.isBuffer(stdout) && Buffer.isBuffer(stderr), 'Raw separate streams required');
  requireThat(stdout.length <= PIN.capturedStreamCap && stderr.length <= PIN.capturedStreamCap, 'Captured output cap exceeded');
  const text = stdout.toString('utf8') + '\n' + stderr.toString('utf8');
  requireThat(!text.includes('\u001b') && !text.includes('\ufffd'), 'Ambiguous terminal control or invalid UTF-8');
  requireThat(/Build complete!/.test(text), 'Missing compiler/build completion');
  requireThat(!/(?:error:|fatal error:|Test Case .* (?:failed|skipped)|[✘✗] |\bTest .* (?:failed|skipped)|\bTest run .*failed)/i.test(text), 'Failure/skip/compiler diagnostic');
  const xctest = roster.suites.find(s=>s.framework==='XCTest');
  requireThat(xctest?.names.length === 8, 'XCTest roster size');
  const actualXCTest = [...text.matchAll(/^Test Case '-\[(?:[A-Za-z0-9_]+\.)?AndroidTextFieldAxisRefusalTests ([A-Za-z0-9_]+)\]' passed \([^\n]+\)\.?\r?$/gm)].map(match=>match[1]);
  equal(actualXCTest.slice().sort(), xctest.names.slice().sort(), 'Every exact XCTest result once');
  requireThat((text.match(/^Test Case .* passed /gm)||[]).length === 8, 'Unexpected/duplicate XCTest result');
  const summaries = [...text.matchAll(/Executed (\d+) tests?, with (\d+) failures?(?: \((\d+) unexpected\))?(?: and (\d+) skips?)? in [^\n]+/g)];
  requireThat(summaries.length > 0 && summaries.every(m=>+m[1]===8 && +m[2]===0 && +(m[3]||0)===0 && +(m[4]||0)===0), 'Separate eight-test zero-failure XCTest summary');
  requireThat(/Test Suite 'AndroidTextFieldAxisRefusalTests' passed/.test(text) && /Test Suite 'All tests' passed/.test(text), 'Missing XCTest terminal suite summaries');
  const expectedSwift = roster.suites.filter(s=>s.framework==='Swift Testing').flatMap(s=>s.names);
  requireThat(expectedSwift.length === 11, 'Swift Testing roster size');
  const actualSwift = [...text.matchAll(/^[✔✓] Test ([A-Za-z0-9_]+)\(\) passed after [^\n]+\r?$/gm)].map(match=>match[1]);
  equal(actualSwift.slice().sort(), expectedSwift.slice().sort(), 'Every exact Swift Testing result once');
  const swiftSummary = [...text.matchAll(/^[✔✓] Test run with (\d+) tests?(?: in (\d+) suites?)? passed after [^\n]+\r?$/gm)];
  requireThat(swiftSummary.length === 1 && +swiftSummary[0][1]===11, 'Separate eleven-test Swift Testing summary');
  // Count every successful Swift Testing result line, including display names,
  // quoted names, arguments, qualified/Unicode names and indented variants.
  // Only the one independently validated framework summary is excluded.
  const successfulSwiftLines = [...text.matchAll(/^[ \t]*[✔✓][\uFE0E\uFE0F]?[ \t]+Test\b[^\r\n]*\bpassed\b[^\r\n]*\r?$/gm)].map(match=>match[0]);
  const successfulSwiftResults = successfulSwiftLines.filter(line=>line!==swiftSummary[0][0]);
  requireThat(successfulSwiftResults.length === 11, 'Unexpected/duplicate Swift Testing success result');
  const warningLines = text.split(/\r?\n/).filter(line=>/\bwarning:/i.test(line));
  const warnings = warningLines.map(line=>({ category: /\.swift:\d+:\d+: warning:/.test(line) ? 'source-compiler' : 'tool-or-SwiftPM', sha256: sha(line), line }));
  return { XCTest: { count: 8, names: actualXCTest, summaryOccurrences: summaries.length }, Swift_Testing: { count: 11, successResultLines: successfulSwiftResults.length, names: actualSwift, summary: swiftSummary[0][0] }, total: 19, warnings, stdout: { bytes: stdout.length, sha256: sha(stdout) }, stderr: { bytes: stderr.length, sha256: sha(stderr) } };
}
export function verifyExecution(record, tool, before, after, output, selection, context) {
  equal(before, after, '27 source identities changed after execution');
  equal(before.projection, PIN.projection, 'Actual source projection');
  equal(tool.status, 'verified-installed-toolchain', 'Apple verifier success');
  equal(tool.xcode, 'Xcode 26.3\nBuild version 17C529', 'Exact Apple version/build');
  equal(tool.developerDirectory, PIN.developer, 'Exact developer directory');
  equal(tool.toolchains, PIN.toolchain, 'Exact toolchain');
  equal(tool.swiftPath, PIN.swift, 'Actual Swift path');
  requireThat(Array.isArray(tool.swiftVersion) && tool.swiftVersion[0]===6 && tool.swiftVersion[1]>=2, 'Official Swift minimum');
  for(const key of ['swiftSHA256','swiftFrontendSHA256','probeSHA256']) requireThat(/^[0-9a-f]{64}$/.test(tool[key]??''),'Missing exact tool hash: '+key);
  equal(tool.probeSHA256, PIN.appleVerifier, 'Actual Apple probe source');
  equal(tool.sourceRevision, context.sha, 'Tool receipt source revision');
  equal(record.argv, [PIN.swift,'test','--package-path',record.workspace+'/'+PIN.packageRelative,'--scratch-path',record.scratch,'--jobs','2'], 'Exact unfiltered Swift test argv');
  equal(record.developer_dir, PIN.developer, 'Command developer directory');
  equal(record.toolchain, PIN.toolchain, 'Command toolchain');
  equal(record.run_id, String(context.run_id), 'Command run ID');
  equal(record.run_attempt, '1', 'Command attempt');
  equal(record.exit_code, 0, 'Direct SwiftPM exit');
  equal(record.shell_completion, 'returned-to-actions-shell', 'Hosted shell completion');
  equal(record.file_limit_blocks, 65536, 'Bash -f limit');
  equal(record.file_limit_unit_bytes, 1024, 'Bash -f source-established unit');
  requireThat(record.bash_version?.length>0, 'Bash version missing');
  equal(record.file_limit_readback.soft_bytes, PIN.regularFileCap, 'RLIMIT_FSIZE soft byte readback');
  equal(record.file_limit_readback.hard_bytes, PIN.regularFileCap, 'RLIMIT_FSIZE hard byte readback');
  equal(record.file_limit_readback.bash_blocks, 65536, 'Readback Bash block count');
  equal(record.file_limit_readback.bash_version, record.bash_version, 'Readback Bash version');
  requireThat(record.scratch === record.runner_temp+'/android-axis-refusal-'+context.run_id+'-1-scratch', 'Exact owned scratch path');
  requireThat(record.workspace?.startsWith('/') && record.runner_temp?.startsWith('/'), 'Absolute owned paths');
  equal(selection.scope, 'isolated-27-file-host-behavior-only', 'Selected scope');
  return { schema: 1, status: 'isolated-host-test-evidence-complete', sourceProjection: PIN.projection, sourceFiles: 27, sourceBytes: 284605, context, tool, command: record, tests: output, custody: { hosted_step_completion: true, direct_child_reap: null, owned_group_absence: null, separate_pipe_EOF: null, arbitrary_descendants: null, runner_disposal: null, scratch_cleanup: 'not-performed-or-established' }, pending: ['canonical SDK/engine package topology and C ABI integration','Java decoder/combined source pair','native/UI/capture and physical phones','immutable published external FieldLog','source-pair promotion, OTA and GA'] };
}
export async function preflight({root, outputDirectory, context, selection}) {
  const directory = root+'/'+PIN.admissionRelative;
  const workflow = await boundedRead(root+'/.github/workflows/android-axis-refusal-host.yml');
  const binding = verifyBinding(selection, context, sha(workflow));
  const source = await sourceSnapshot(root);
  await fs.mkdir(outputDirectory, {recursive: false});
  await fs.writeFile(outputDirectory+'/root-selection.json',JSON.stringify(selection,null,2)+'\n');
  await fs.writeFile(outputDirectory+'/context.json',JSON.stringify(context,null,2)+'\n');
  await fs.writeFile(outputDirectory+'/binding.json',JSON.stringify(binding,null,2)+'\n');
  await fs.writeFile(outputDirectory+'/source-before.json',JSON.stringify(source,null,2)+'\n');
  return {binding,source};
}
export async function postflight({root, outputDirectory}) {
  const source = await sourceSnapshot(root);
  await fs.writeFile(outputDirectory+'/source-after.json',JSON.stringify(source,null,2)+'\n');
  equal(await readJSON(outputDirectory+'/source-before.json'),source,'Source pre/post mismatch');
  return source;
}
export async function assess({root,outputDirectory}) {
  const directory = root+'/'+PIN.admissionRelative;
  const selection=await readJSON(outputDirectory+'/root-selection.json');
  const context=await readJSON(outputDirectory+'/context.json');
  const binding=verifyBinding(selection,context,sha(await boundedRead(root+'/.github/workflows/android-axis-refusal-host.yml')));
  equal(await readJSON(outputDirectory+'/binding.json'),binding,'Preflight root binding changed');
  const before=await readJSON(outputDirectory+'/source-before.json');
  const after=await readJSON(outputDirectory+'/source-after.json');
  equal(after,await sourceSnapshot(root),'Source changed after postflight');
  const roster=await readJSON(directory+'/required-tests.json');
  const output=parseTestOutput(await boundedRead(outputDirectory+'/swift.stdout',PIN.capturedStreamCap),await boundedRead(outputDirectory+'/swift.stderr',PIN.capturedStreamCap),roster);
  const result=verifyExecution(await readJSON(outputDirectory+'/command.json'),await readJSON(outputDirectory+'/apple-toolchain.json'),before,after,output,selection,context);
  result.binding=binding;
  result.apple_file_limit=await readJSON(outputDirectory+'/apple-file-limit.json');
  equal(result.apple_file_limit.soft_bytes,PIN.regularFileCap,'Apple probe inherited soft byte limit');
  equal(result.apple_file_limit.hard_bytes,PIN.regularFileCap,'Apple probe inherited hard byte limit');
  equal(result.apple_file_limit.bash_blocks,65536,'Apple probe Bash file-size blocks');
  result.tool_probe_streams={};
  for(const name of ['apple-toolchain.stdout','apple-toolchain.stderr','apple-file-limit.stdout','apple-file-limit.stderr','file-limit.stdout','file-limit.stderr']) { const bytes=await boundedRead(outputDirectory+'/'+name,PIN.capturedStreamCap); result.tool_probe_streams[name]={bytes:bytes.length,sha256:sha(bytes)}; }
  await fs.writeFile(outputDirectory+'/result.json',JSON.stringify(result,null,2)+'\n');
  return result;
}

export async function recordCommand({workspace,runnerTemp,outputDirectory,context,bashVersion,exitCode=null}) {
  const limit=await readJSON(outputDirectory+'/file-limit.json');
  const record={schema:1,workspace,runner_temp:runnerTemp,scratch:runnerTemp+'/android-axis-refusal-'+context.run_id+'-1-scratch',developer_dir:PIN.developer,toolchain:PIN.toolchain,run_id:String(context.run_id),run_attempt:'1',bash_version:bashVersion,file_limit_blocks:65536,file_limit_unit_bytes:1024,file_limit_readback:limit,exit_code:exitCode,shell_completion:exitCode===null?'not-observed':'returned-to-actions-shell'};
  equal(limit.soft_bytes,PIN.regularFileCap,'Unexpected inherited soft file-size limit');
  equal(limit.hard_bytes,PIN.regularFileCap,'Unexpected inherited hard file-size limit');
  equal(limit.bash_blocks,65536,'Unexpected Bash file-size blocks');
  equal(limit.bash_version,bashVersion,'Bash version binding');
  record.argv=[PIN.swift,'test','--package-path',workspace+'/'+PIN.packageRelative,'--scratch-path',record.scratch,'--jobs','2'];
  await fs.writeFile(outputDirectory+'/command.json',JSON.stringify(record,null,2)+'\n');
  return record;
}
