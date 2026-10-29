import {equal, requireThat, sha} from './verify.mjs';
import {priorEqualSource, correctedEqualSource} from './binding-controls.mjs';

// Pure source/data controls. This is a bounded check of this exact workflow,
// not a general YAML/schema validator or evidence of any GitHub/Swift execution.
export const priorDirectory = 'verification/android-axis-refusal-host-admission-result-correction';
export const correctedDirectory = 'verification/android-axis-refusal-host-admission-binding-correction';
export const rejectedJobEnv = '      MIXER_AXIS_OUT: ${{ runner.temp }}/android-axis-refusal-${{ github.run_id }}-${{ github.run_attempt }}\n';
export const firstMarker = '          ulimit -f 65536\n          node --input-type=module';
export const initialization = [
  '          ulimit -f 65536',
  '          export MIXER_AXIS_OUT="$RUNNER_TEMP/android-axis-refusal-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"',
  '          case "$MIXER_AXIS_OUT" in',
  '            *$\'\\n\'*|*$\'\\r\'*) printf \'Invalid output path line break\\n\' >&2; exit 1 ;;',
  '          esac',
  '          printf \'MIXER_AXIS_OUT=%s\\n\' "$MIXER_AXIS_OUT" >> "$GITHUB_ENV"',
  '          node --input-type=module',
].join('\n');

export function expectedWorkflow(prior) {
  equal(sha(prior), 'ff3f4f99a8e99794b881fe34b8a4b4b3ac5491b98144b2df0cfc7763916bbf64', 'Frozen prior workflow binding');
  equal(prior.split(rejectedJobEnv).length, 2, 'Exactly one invalid job env assignment');
  const rebound = prior.replace(rejectedJobEnv, '').replaceAll(priorDirectory, correctedDirectory);
  requireThat(rebound.includes(firstMarker), 'Existing first data step marker');
  // A function replacement preserves the shell's literal $'...' syntax;
  // JavaScript replacement strings interpret $' as the matched suffix.
  return rebound.replace(firstMarker, () => initialization);
}

export function reviewExpressionLocations(workflow) {
  const reviewed = new Map([
    ['      MIXER_AXIS_ROOT_SELECTION: ${{ inputs.root_selection }}', ['jobs.axis-refusal.env.MIXER_AXIS_ROOT_SELECTION', ['inputs']]],
    ['      MIXER_AXIS_PROFILE: ${{ inputs.profile }}', ['jobs.axis-refusal.env.MIXER_AXIS_PROFILE', ['inputs']]],
    ['          name: android-axis-refusal-host-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}', ['jobs.axis-refusal.steps.upload-artifact.with.name', ['github', 'github', 'github']]],
    ['          path: ${{ runner.temp }}/android-axis-refusal-${{ github.run_id }}-${{ github.run_attempt }}/', ['jobs.axis-refusal.steps.upload-artifact.with.path', ['runner', 'github', 'github']]],
  ]);
  const locations = [];
  for (const [index, line] of workflow.split('\n').entries()) {
    if (!line.includes('${{')) continue;
    const allowed = reviewed.get(line);
    requireThat(allowed, 'Expression outside exact reviewed context: line ' + (index + 1));
    const contexts = [...line.matchAll(/\$\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\./g)].map(match => match[1]);
    equal(contexts, allowed[1], 'Expression context roster: line ' + (index + 1));
    locations.push({line: index + 1, path: allowed[0], contexts});
  }
  equal(locations.map(row => row.path), [...reviewed.values()].map(row => row[0]), 'Exactly four reviewed expression lines');
  equal(locations.flatMap(row => row.contexts).length, 8, 'Exactly eight reviewed expressions');
  equal(locations.filter(row => row.contexts.includes('runner')).map(row => row.path), ['jobs.axis-refusal.steps.upload-artifact.with.path'], 'runner context occurs only in valid step with scope');
  return locations;
}

export function verifyCorrection({priorWorkflow, workflow, priorVerifier, verifier, template}) {
  equal(workflow, expectedWorkflow(priorWorkflow), 'Only the exact expression placement and sibling-path delta');
  const locations = reviewExpressionLocations(workflow);
  equal(sha(priorVerifier), 'a7a6cfa655a7bcd784eb4048247edbfb4e74f0502ac1a9979a0b318fd0bbdbf3', 'Frozen corrected-result verifier binding');
  equal(verifier, priorVerifier.replace("admissionRelative: '" + priorDirectory + "'", "admissionRelative: '" + correctedDirectory + "'").replace(priorEqualSource, () => correctedEqualSource), 'Verifier differs only by sibling admission path and reviewed strict JSON comparator');
  equal(template.workflow_sha256, sha(workflow), 'False template binds final corrected workflow bytes');
  equal([template.selected, template.dispatch_authorized, template.source_revision, template.run_id], [false, false, null, null], 'Root selection and runtime authority remain false/unbound');
  equal([template.max_manual_dispatches, template.max_run_attempt], [1, 1], 'One manual dispatch and attempt');
  return locations;
}

export function runExpressionControls(input) {
  const results = [];
  const test = (name, body) => { body(); results.push({name, status: 'pass'}); };
  const refuse = (name, body) => test(name, () => { let refused = false; try { body(); } catch { refused = true; } requireThat(refused, 'Expected refusal: ' + name); });
  const check = delta => verifyCorrection({...input, ...delta});
  test('exact-correction-and-all-expression-locations', () => check({}));
  refuse('actual-prior-runner-in-job-env-defect', () => reviewExpressionLocations(input.priorWorkflow));
  refuse('reintroduced-runner-in-job-env', () => check({workflow: input.workflow.replace('    steps:\n', rejectedJobEnv + '    steps:\n')}));
  refuse('missing-output-export', () => check({workflow: input.workflow.replace('          export MIXER_AXIS_OUT=', '          MIXER_AXIS_OUT=')}));
  refuse('missing-next-step-output-persistence', () => check({workflow: input.workflow.replace(' >> "$GITHUB_ENV"', '')}));
  refuse('missing-line-break-refusal', () => check({workflow: input.workflow.replace("            *$'\\n'*|*$'\\r'*) printf 'Invalid output path line break\\n' >&2; exit 1 ;;\n", '')}));
  refuse('output-path-drift', () => check({workflow: input.workflow.replace('$RUNNER_TEMP/android-axis-refusal-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT', '$RUNNER_TEMP/other-output-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT')}));
  refuse('initialization-after-preflight', () => check({workflow: input.workflow.replace(initialization, firstMarker) + '\n' + initialization + '\n'}));
  refuse('new-unreviewed-runner-expression', () => reviewExpressionLocations(input.workflow + '      EXTRA: ${{ runner.temp }}\n'));
  refuse('runner-upload-step-expression-drift', () => reviewExpressionLocations(input.workflow.replace('path: ${{ runner.temp }}', 'path: ${{ runner.workspace }}')));
  refuse('test-command-filter-drift', () => check({workflow: input.workflow.replace('--scratch-path "$MIXER_AXIS_SCRATCH" --jobs 2', '--scratch-path "$MIXER_AXIS_SCRATCH" --jobs 2 --filter test')}));
  refuse('file-limit-drift', () => check({workflow: input.workflow.replace('ulimit -f 65536', 'ulimit -f 65537')}));
  refuse('manual-event-guard-drift', () => check({workflow: input.workflow.replace("github.event_name == 'workflow_dispatch'", "github.event_name == 'push'")}));
  refuse('attempt-guard-drift', () => check({workflow: input.workflow.replace('github.run_attempt == 1', 'github.run_attempt <= 2')}));
  refuse('stale-template-workflow-hash', () => check({template: {...input.template, workflow_sha256: sha(input.priorWorkflow)}}));
  refuse('selected-template', () => check({template: {...input.template, selected: true}}));
  refuse('additional-dispatch-allowance', () => check({template: {...input.template, max_manual_dispatches: 2}}));
  refuse('result-parser-drift', () => check({verifier: input.verifier + '\n// changed parser\n'}));
  return {schema: 1, status: 'passed-data-only-expression-controls', count: results.length, results, synthetic_source_controls_are_not_GitHub_or_host_evidence: true};
}
