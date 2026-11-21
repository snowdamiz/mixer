import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {until} from "./workerd-custody.mjs";

const encode = text => new TextEncoder().encode(text).buffer;
const sha256 = text => createHash("sha256").update(text).digest("hex");

export async function exerciseProjectionPublisher({
  bucket, worker, target, assignments, artifact, manifestHash, installation, current, publishProjection,
}) {
  const retained = {manifest_sha256: manifestHash, envelope_sha256: sha256(artifact)};
  const rootDeadline = BigInt(Math.floor(Date.now() / 1000) + 30);
  function projection(label, validUntilUnix = rootDeadline) {
    const bytes = assignments[label];
    const {sequence, rollout_basis_points} = JSON.parse(bytes).assignment;
    return {
      target, validUntilUnix, assignmentBytes: encode(bytes), artifacts: [retained],
      head: {
        sequence: String(sequence), assignment_sha256: sha256(bytes), artifact_sha256: manifestHash,
        rollout_basis_points, enabled: rollout_basis_points > 0,
      },
    };
  }

  let live = projection("publish-first");
  let afterArtifact;
  let artifactBytes = encode(artifact);
  let authorityChecks = 0;
  let permitChecks = Number.POSITIVE_INFINITY;
  const source = {
    async read() { return live; },
    async readArtifact() {
      afterArtifact?.();
      return artifactBytes;
    },
    async withCurrent(authority, publish) {
      authorityChecks++;
      if (live === null) return "unavailable";
      if (live.head.assignment_sha256 !== authority.head.assignment_sha256 ||
          live.validUntilUnix !== authority.validUntilUnix) return "stale";
      return publish(() => permitChecks-- > 0);
    },
  };
  const issue = () => publishProjection({bucket, target, source, leaseMs: 60_000});
  const origin = "http://published-fixture.invalid";
  const offer = "/v3/updates?" + new URLSearchParams({...target, installation});
  const download = "/v3/artifacts/" + manifestHash + "?" +
    new URLSearchParams({organization: target.organization, project: target.project});
  const get = path => worker.fetch(origin + path, {signal: AbortSignal.timeout(4500)});

  artifactBytes = encode(artifact + " ");
  await assert.rejects(issue(), /publication_artifact/);
  assert.equal(authorityChecks, 0);
  assert.equal(await current(bucket, target), null);
  artifactBytes = encode(artifact);

  afterArtifact = () => { live = projection("promote"); };
  assert.equal(await issue(), "stale");
  assert.equal(await current(bucket, target), null);
  assert.equal((await get(download)).status, 404);
  afterArtifact = undefined;

  live = projection("publish-first");
  permitChecks = 1;
  assert.equal(await issue(), "expired");
  assert.equal(await current(bucket, target), null);
  permitChecks = Number.POSITIVE_INFINITY;
  assert.equal(await issue(), "applied");
  const first = await current(bucket, target);
  assert.equal(first.snapshot.revision, "1");
  assert.equal(first.snapshot.expires_at_ms, Number(rootDeadline * 1000n));
  const response = await get(offer);
  assert.equal(response.status, 200);
  assert((await response.text()).startsWith('{"signed_assignment":' + assignments["publish-first"] + ","));

  live = null;
  assert.equal(await issue(), "unavailable");
  assert.equal((await current(bucket, target)).hash, first.hash);

  live = projection("halt");
  assert.equal(await issue(), "applied");
  const halted = await current(bucket, target);
  assert.equal(halted.snapshot.revision, "2");
  assert.equal((await get(offer)).status, 204);
  const historical = await get(download);
  assert.equal(historical.status, 200);
  assert.equal(await historical.text(), artifact);

  live = projection("publish-first");
  assert.equal(await issue(), "stale");
  assert.equal((await current(bucket, target)).hash, halted.hash);

  const expiry = BigInt(Math.floor(Date.now() / 1000) + 5);
  live = projection("resume", expiry);
  assert.equal(await issue(), "applied");
  const resumed = await current(bucket, target);
  assert.equal(resumed.snapshot.revision, "3");
  assert.equal(resumed.snapshot.expires_at_ms, Number(expiry * 1000n));
  assert.equal((await get(offer)).status, 200);
  await until(async () => (await get(offer)).status === 204, 6000);
  assert.equal((await get(download)).status, 404);
  assert.equal(await issue(), "expired");
  assert.equal((await current(bucket, target)).hash, resumed.hash);

  return {
    wireDigestBeforePublication: true, stageRaceRefused: true, authorityUnavailableNoRenewal: true,
    rootDeadlineExact: true, historicalArtifactDuringHalt: true, staleReplayRefused: true,
    expiredLeaseClosed: true, callbackDeadlineAtCAS: true, fixtureAuthority: true,
  };
}
